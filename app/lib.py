"""Application utility library containing pure data-loading, mode switching, and helper functions."""

from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
from typing import Any
import zipfile

import numpy as np
import pandas as pd
import streamlit as st

from gate.decisions import decide
from gate.thresholds import compute_thresholds


@dataclass
class AppPaths:
    """Holds all configured filesystem paths based on active application mode."""
    mode: str
    is_mock: bool
    scores_path: Path
    meta_path: Path
    candidate_list_path: Path
    policy_path: Path
    registry_path: Path
    out_dir: Path
    review_decisions_path: Path


def get_mode() -> str:
    """Read current operation mode from SHIFTGATE_MODE environment variable."""
    return os.environ.get("SHIFTGATE_MODE", "mock").strip().lower()


def get_app_paths(mode: str | None = None) -> AppPaths:
    """Resolve file paths for mock or real operational mode."""
    current_mode = (mode or get_mode()).strip().lower()
    is_mock = current_mode != "real"

    if is_mock:
        return AppPaths(
            mode="mock",
            is_mock=True,
            scores_path=Path("gate/FAKE_scores.csv"),
            meta_path=Path("gate/FAKE_run_meta.json"),
            candidate_list_path=Path("gate/FAKE_candidate_list.csv"),
            policy_path=Path("gate/policy.yaml"),
            registry_path=Path("gate/registry_mock.json"),
            out_dir=Path("app/.mock_out"),
            review_decisions_path=Path("app/.mock_out/review_decisions.json"),
        )
    return AppPaths(
        mode="real",
        is_mock=False,
        scores_path=Path("results/scores.csv"),
        meta_path=Path("results/run_meta.json"),
        candidate_list_path=Path("results/candidate_list.csv"),
        policy_path=Path("gate/policy.yaml"),
        registry_path=Path("gate/registry.json"),
        out_dir=Path("results/exports"),
        review_decisions_path=Path("results/review_decisions.json"),
    )


def check_missing_files(paths: AppPaths) -> list[str]:
    """Check existence of required data files and return descriptive system-attributed messages."""
    missing: list[str] = []
    if not paths.scores_path.exists():
        src = "gate synthetic generator (Stage A2)" if paths.is_mock else "System 1 (pipeline scoring run)"
        missing.append(f"Scores file '{paths.scores_path}' not found. Produced by: {src}.")
    if not paths.meta_path.exists():
        src = "gate synthetic generator (Stage A2)" if paths.is_mock else "System 1 (pipeline run metadata)"
        missing.append(f"Metadata file '{paths.meta_path}' not found. Produced by: {src}.")
    if not paths.policy_path.exists():
        missing.append(f"Policy file '{paths.policy_path}' not found. Maintained by: System 2.")
    return missing


def load_run_metadata(meta_path: Path | str) -> dict[str, Any]:
    """Load JSON metadata safely from disk."""
    p = Path(meta_path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scores_df(scores_path: Path | str) -> pd.DataFrame:
    """Load scores CSV into DataFrame."""
    p = Path(scores_path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def get_run_info_device_text(device: str | None, is_mock: bool) -> str:
    """Format truth-in-advertising device description string without misrepresenting hardware."""
    if is_mock:
        return "SAMPLE DATA: not a real run."
    dev = str(device or "").lower()
    if dev == "rocm":
        return "AMD GPU (ROCm / HIP accelerated)"
    if dev == "cpu":
        return "Not an AMD GPU run."
    if dev == "other_gpu":
        return "Not an AMD GPU."
    return "Unknown execution environment."


def format_run_info(meta: dict[str, Any], is_mock: bool) -> dict[str, Any]:
    """Format all run information fields for presentation in the UI footer."""
    device = meta.get("device")
    device_text = get_run_info_device_text(device, is_mock)

    run_id = str(meta.get("run_id", "N/A"))
    if is_mock:
        badge_text = "SAMPLE DATA"
        badge_color = "red"
    elif run_id.startswith("sample-"):
        badge_text = "SAMPLE RUN"
        badge_color = "orange"
    else:
        badge_text = "PRODUCTION RUN"
        badge_color = "green"

    timings = meta.get("timings_sec", {})
    t_feat = timings.get("features", 0.0)
    t_bank = timings.get("bank", 0.0)
    t_score = timings.get("scoring", 0.0)
    total_time = t_feat + t_bank + t_score

    dataset_info = meta.get("dataset", {})

    return {
        "run_id": run_id,
        "device": device or "N/A",
        "device_text": device_text,
        "badge_text": badge_text,
        "badge_color": badge_color,
        "gpu_name": meta.get("gpu_name") or "None",
        "hip_version": meta.get("hip_version") or "None",
        "torch_version": meta.get("torch_version") or "N/A",
        "seed": meta.get("seed", "N/A"),
        "features_sec": t_feat,
        "bank_sec": t_bank,
        "scoring_sec": t_score,
        "total_sec": total_time,
        "dataset_name": dataset_info.get("name", "N/A"),
        "category": dataset_info.get("category", "pcb"),
        "shift_type": dataset_info.get("shift_type", "N/A"),
    }


def get_current_false_holds(
    df_scores: pd.DataFrame,
    active_version: str,
    condition: str = "shift_a",
    percentile: float = 99.0,
) -> int:
    """Compute current count of false holds for active version on specified validation condition."""
    if df_scores.empty:
        return 0
    v_scores = df_scores[df_scores["model_version"] == active_version]
    if v_scores.empty:
        return 0

    th_map = compute_thresholds(df_scores, percentile=percentile, versions=[active_version])
    th = th_map.get(active_version, 0.0)

    val_good_cond = v_scores[
        (v_scores["split"] == "validation")
        & (v_scores["true_label"] == "good")
        & (v_scores["condition"] == condition)
    ]
    if val_good_cond.empty:
        return 0

    holds = decide(val_good_cond["anomaly_score"], th)
    return int((holds == "HOLD").sum())


def save_review_decisions(decisions: dict[str, str], path: Path | str) -> None:
    """Save user candidate image approval choices to JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)


def load_review_decisions(path: Path | str) -> dict[str, str]:
    """Load previously saved candidate review choices from JSON file."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_review_decisions_to_bank(
    decisions: dict[str, str],
    candidate_list_df: pd.DataFrame,
) -> list[str]:
    """Compare operator review decisions against reference bank ground-truth inclusion."""
    notes: list[str] = []
    if candidate_list_df.empty or not decisions:
        return notes

    cand_map = candidate_list_df.set_index("image_id").to_dict(orient="index")
    for img_id, decision in decisions.items():
        if img_id not in cand_map:
            continue
        row = cand_map[img_id]
        in_v3 = bool(row.get("in_v3_bank", False))
        is_contaminant = bool(row.get("is_contaminant", False))

        if decision == "approve" and not in_v3:
            msg = f"Image '{img_id}' was approved, but v3 bank excluded it"
            if is_contaminant:
                msg += " (it is a contaminant defect!)."
            else:
                msg += "."
            notes.append(msg)
        elif decision == "reject" and in_v3:
            notes.append(f"Image '{img_id}' was rejected, but was included in v3 bank.")

    return notes


def build_zip_archive(bundle_dir: str | Path) -> bytes:
    """Compress contents of bundle directory into in-memory zip bytes."""
    src = Path(bundle_dir)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in src.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(src))
    buffer.seek(0)
    return buffer.getvalue()


def render_header(title: str, is_mock: bool, subtitle: str = "") -> None:
    """Render standardized page header with prominent sample data banner if in mock mode."""
    if is_mock:
        st.markdown(
            """
            <div style="background-color: #B91C1C; color: white; padding: 12px 18px; border-radius: 6px;
                        font-weight: bold; font-size: 1.1rem; margin-bottom: 20px; text-align: center; letter-spacing: 1px;">
                ⚠️ SAMPLE DATA &mdash; NOT A PRODUCTION OR AMD RUN
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_run_info(meta: dict[str, Any], is_mock: bool) -> None:
    """Render honest, transparent hardware and execution footer on every Streamlit page."""
    info = format_run_info(meta, is_mock)

    st.markdown("---")
    cols = st.columns([2, 2, 2, 2])
    with cols[0]:
        st.markdown("**Hardware & Platform**")
        st.write(info["device_text"])
        st.caption(f"Device: `{info['device']}` | GPU: `{info['gpu_name']}`")

    with cols[1]:
        st.markdown("**Software Versions**")
        st.caption(f"PyTorch: `{info['torch_version']}`")
        st.caption(f"ROCm/HIP: `{info['hip_version']}`")
        st.caption(f"Seed: `{info['seed']}`")

    with cols[2]:
        st.markdown("**Execution Timings**")
        st.caption(f"Feature Extr: {info['features_sec']:.2f}s")
        st.caption(f"Bank Build: {info['bank_sec']:.2f}s | Scoring: {info['scoring_sec']:.2f}s")
        st.caption(f"Total: {info['total_sec']:.2f}s")

    with cols[3]:
        st.markdown("**Run Identification**")
        st.caption(f"Run ID: `{info['run_id']}`")
        st.caption(f"Dataset: `{info['dataset_name']}` ({info['category']})")
        st.caption(f"Shift Type: `{info['shift_type']}`")
