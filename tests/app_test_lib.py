"""Unit tests for pure helper functions in app/lib.py."""

import json
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from app.lib import (
    check_missing_files,
    compare_review_decisions_to_bank,
    format_run_info,
    get_app_paths,
    get_current_false_holds,
    get_mode,
    get_run_info_device_text,
    load_run_metadata,
    load_scores_df,
    load_review_decisions,
    save_review_decisions,
)


def test_mode_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert get_mode and get_app_paths toggle correctly based on SHIFTGATE_MODE env var."""
    monkeypatch.delenv("SHIFTGATE_MODE", raising=False)
    assert get_mode() == "mock"
    paths_default = get_app_paths()
    assert paths_default.is_mock is True
    assert paths_default.scores_path == Path("gate/FAKE_scores.csv")

    monkeypatch.setenv("SHIFTGATE_MODE", "real")
    assert get_mode() == "real"
    paths_real = get_app_paths()
    assert paths_real.is_mock is False
    assert paths_real.scores_path == Path("results/scores.csv")


def test_run_info_device_text() -> None:
    """Assert device text truthfulness for mock, rocm, cpu, and other_gpu."""
    # In mock mode, always shows SAMPLE DATA
    assert "SAMPLE DATA" in get_run_info_device_text("rocm", is_mock=True)
    assert "SAMPLE DATA" in get_run_info_device_text("cpu", is_mock=True)

    # In real mode:
    assert "AMD GPU" in get_run_info_device_text("rocm", is_mock=False)
    assert "Not an AMD GPU run." == get_run_info_device_text("cpu", is_mock=False)
    assert "Not an AMD GPU." == get_run_info_device_text("other_gpu", is_mock=False)


def test_format_run_info() -> None:
    """Assert format_run_info returns all required fields and timings."""
    meta = {
        "run_id": "sample-cpu-20261013T120000",
        "device": "cpu",
        "gpu_name": None,
        "torch_version": "2.2.0",
        "hip_version": None,
        "seed": 42,
        "timings_sec": {"features": 1.0, "bank": 0.5, "scoring": 2.0},
        "dataset": {"name": "PCB", "category": "pcb", "shift_type": "synthetic"},
    }
    info = format_run_info(meta, is_mock=False)
    assert info["badge_text"] == "SAMPLE RUN"
    assert info["total_sec"] == 3.5
    assert info["device_text"] == "Not an AMD GPU run."


def test_check_missing_files_messages() -> None:
    """Assert missing file messages clearly indicate file name and producing system."""
    paths = get_app_paths(mode="real")
    paths.scores_path = Path("results/nonexistent_scores.csv")
    missing = check_missing_files(paths)
    assert len(missing) >= 1
    assert any("System 1" in m for m in missing)


def test_compare_review_decisions_to_bank() -> None:
    """Assert comparing operator review decisions flags contaminant approval."""
    df_cand = pd.DataFrame([
        {"image_id": "cand_1", "in_v3_bank": True, "is_contaminant": False},
        {"image_id": "cand_2", "in_v3_bank": False, "is_contaminant": True},
    ])
    decisions = {
        "cand_1": "approve",
        "cand_2": "approve",  # Operator approved contaminant!
    }
    notes = compare_review_decisions_to_bank(decisions, df_cand)
    assert len(notes) == 1
    assert "contaminant defect" in notes[0]


def test_save_and_load_review_decisions() -> None:
    """Assert saving and loading review decisions to temporary JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "reviews.json"
        data = {"cand_001": "approve", "cand_002": "reject"}
        save_review_decisions(data, dest)
        loaded = load_review_decisions(dest)
        assert loaded == data


def test_get_current_false_holds() -> None:
    """Assert get_current_false_holds correctly computes false holds on shift_a validation data."""
    df = pd.read_csv("gate/FAKE_scores.csv")
    fh = get_current_false_holds(df, active_version="v1_current", condition="shift_a")
    assert fh == 6
