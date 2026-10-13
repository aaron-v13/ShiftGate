"""End-to-end execution of the ShiftGate PatchCore pipeline."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd
import torch
import yaml

from pipeline.dataset import list_images
from pipeline.device import get_device_info
from pipeline.features import FeatureExtractor
from pipeline.score import score_images
from pipeline.shifts import assign_conditions
from pipeline.splits import make_splits
from pipeline.versions import build_banks


def validate_contract_outputs(
    scores_path: Path,
    meta_path: Path,
    splits_path: Path,
    cand_path: Path,
) -> None:
    """Validate all generated output files against the contract specifications."""
    if not scores_path.exists():
        raise FileNotFoundError(f"Missing {scores_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing {meta_path}")
    if not splits_path.exists():
        raise FileNotFoundError(f"Missing {splits_path}")
    if not cand_path.exists():
        raise FileNotFoundError(f"Missing {cand_path}")

    # Validate scores.csv
    scores_df = pd.read_csv(scores_path)
    expected_scores_cols = [
        "run_id", "image_id", "path", "category", "condition", "split",
        "true_label", "model_version", "anomaly_score", "map_path", "device"
    ]
    if list(scores_df.columns) != expected_scores_cols:
        raise ValueError(f"scores.csv columns mismatch: got {list(scores_df.columns)}, expected {expected_scores_cols}")

    valid_labels = {"good", "defect"}
    if not set(scores_df["true_label"].unique()).issubset(valid_labels):
        raise ValueError(f"Invalid true_label in scores.csv: {scores_df['true_label'].unique()}")

    valid_splits = {"calibration", "validation", "test"}
    if not set(scores_df["split"].unique()).issubset(valid_splits):
        raise ValueError(f"Invalid split in scores.csv: {scores_df['split'].unique()}")

    valid_versions = {"v1_current", "v2_candidate_loose", "v3_candidate_reviewed"}
    if not set(scores_df["model_version"].unique()).issubset(valid_versions):
        raise ValueError(f"Invalid model_version in scores.csv: {scores_df['model_version'].unique()}")

    # Validate run_meta.json
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    expected_meta_keys = [
        "run_id", "device", "gpu_name", "torch_version", "hip_version",
        "seed", "n_images", "batch_size", "image_size", "timings_sec",
        "dataset", "notes"
    ]
    for k in expected_meta_keys:
        if k not in meta:
            raise ValueError(f"Missing key in run_meta.json: {k}")

    for tk in ["features", "bank", "scoring"]:
        if tk not in meta["timings_sec"]:
            raise ValueError(f"Missing timing key in timings_sec: {tk}")

    for dk in ["name", "category", "licence", "shift_type"]:
        if dk not in meta["dataset"]:
            raise ValueError(f"Missing dataset key: {dk}")

    # Validate splits.csv
    splits_df = pd.read_csv(splits_path)
    expected_splits_cols = ["image_id", "path", "category", "condition", "split", "true_label", "defect_type"]
    if list(splits_df.columns) != expected_splits_cols:
        raise ValueError(f"splits.csv columns mismatch: got {list(splits_df.columns)}")

    # Validate candidate_list.csv
    cand_df = pd.read_csv(cand_path)
    expected_cand_cols = ["image_id", "path", "condition", "is_contaminant", "in_v3_bank"]
    if list(cand_df.columns) != expected_cand_cols:
        raise ValueError(f"candidate_list.csv columns mismatch: got {list(cand_df.columns)}")


def run_pipeline(config_path: str, req_device: str = "auto") -> Dict[str, Any]:
    """Execute complete detection pipeline and write contract compliant outputs."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    device_info = get_device_info(req_device)
    device_obj = torch.device(device_info["torch_device"])
    device_label = device_info["label"]

    mode = cfg.get("mode", "sample")
    timestamp_str = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_id = f"{mode}-{device_label}-{timestamp_str}"

    results_dir = Path(cfg.get("results_dir", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover dataset images and condition assignment
    df_raw = list_images(cfg)
    df_cond = assign_conditions(df_raw, cfg)

    # 2. Splits generation or loading
    splits_path = results_dir / "splits.csv"
    df_splits = make_splits(df_cond, cfg)

    # Initialize timings tracker
    timers: Dict[str, float] = {"features": 0.0, "bank": 0.0, "scoring": 0.0}

    # 3. Backbone Feature Extractor
    extractor = FeatureExtractor(device=device_obj, weights="DEFAULT")

    # 4. Memory Bank Construction
    banks, cand_df = build_banks(df_splits, extractor, cfg, timers)

    # 5. Scoring
    scores_df = score_images(df_splits, banks, extractor, cfg, timers, run_id, device_label)
    scores_path = results_dir / "scores.csv"
    scores_df.to_csv(scores_path, index=False)

    # Determine shift_type recorded
    shift_cfg_type = cfg.get("shift", {}).get("type", "auto")
    shift_type = "synthetic" if shift_cfg_type in ["auto", "synthetic"] else "native"

    # 6. Write run_meta.json
    run_meta = {
        "run_id": run_id,
        "device": device_label,
        "gpu_name": device_info["gpu_name"],
        "torch_version": device_info["torch_version"],
        "hip_version": device_info["hip_version"],
        "seed": int(cfg.get("seed", 42)),
        "n_images": int(len(df_splits)),
        "batch_size": int(cfg.get("batch_size", 8)),
        "image_size": int(cfg.get("image_size", 256)),
        "timings_sec": {
            "features": round(timers.get("features", 0.0), 3),
            "bank": round(timers.get("bank", 0.0), 3),
            "scoring": round(timers.get("scoring", 0.0), 3),
        },
        "dataset": {
            "name": "AmazonScience/RobustAD",
            "category": str(cfg.get("category", "PCB")),
            "licence": "CC BY 4.0",
            "shift_type": shift_type,
        },
        "notes": f"Pipeline run in mode={mode} on device={device_label}.",
    }

    meta_path = results_dir / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    # 7. Validate contract outputs
    cand_path = results_dir / "candidate_list.csv"
    validate_contract_outputs(scores_path, meta_path, splits_path, cand_path)

    # Real summary reporting
    print("=== ShiftGate Pipeline Run Summary ===")
    print(f"Run ID: {run_id}")
    print(f"Device: {device_label} ({device_info['gpu_name'] or device_label})")
    print(f"Total dataset images: {len(df_splits)}")
    print("Images per split:")
    split_counts = df_splits["split"].value_counts().to_dict()
    for sp, cnt in split_counts.items():
        print(f"  {sp}: {cnt}")
    print(f"Timings (sec): features={run_meta['timings_sec']['features']}, bank={run_meta['timings_sec']['bank']}, scoring={run_meta['timings_sec']['scoring']}")

    calib_normals = scores_df[(scores_df["split"] == "calibration") & (scores_df["true_label"] == "good")]
    print("Calibration normals mean anomaly score:")
    for v in ["v1_current", "v2_candidate_loose", "v3_candidate_reviewed"]:
        v_scores = calib_normals[calib_normals["model_version"] == v]["anomaly_score"]
        mean_s = float(v_scores.mean()) if len(v_scores) > 0 else 0.0
        print(f"  {v}: {mean_s:.4f}")

    return run_meta


def main() -> None:
    """CLI entrypoint for executing pipeline from command line arguments."""
    parser = argparse.ArgumentParser(description="ShiftGate Anomaly Detection Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--device", default="auto", help="Compute device specification")
    args = parser.parse_args()

    run_pipeline(args.config, args.device)


if __name__ == "__main__":
    main()
