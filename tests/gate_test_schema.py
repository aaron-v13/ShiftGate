"""Tests for schema validation in gate/schema.py."""

import pandas as pd
import pytest
from gate.schema import ScoresError, validate_scores


def make_valid_df() -> pd.DataFrame:
    """Create a minimal valid DataFrame meeting all contract requirements."""
    rows = [
        # calibration (good only)
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_cal_1",
            "path": "data/sample/cal1.png",
            "category": "pcb",
            "condition": "baseline",
            "split": "calibration",
            "true_label": "good",
            "model_version": "v1_current",
            "anomaly_score": 0.12,
            "map_path": "",
            "device": "cpu",
        },
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_cal_1",
            "path": "data/sample/cal1.png",
            "category": "pcb",
            "condition": "baseline",
            "split": "calibration",
            "true_label": "good",
            "model_version": "v2_candidate_loose",
            "anomaly_score": 0.10,
            "map_path": "",
            "device": "cpu",
        },
        # validation (good and defect)
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_val_good_1",
            "path": "data/sample/val1.png",
            "category": "pcb",
            "condition": "baseline",
            "split": "validation",
            "true_label": "good",
            "model_version": "v1_current",
            "anomaly_score": 0.20,
            "map_path": "",
            "device": "cpu",
        },
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_val_good_1",
            "path": "data/sample/val1.png",
            "category": "pcb",
            "condition": "baseline",
            "split": "validation",
            "true_label": "good",
            "model_version": "v2_candidate_loose",
            "anomaly_score": 0.15,
            "map_path": "",
            "device": "cpu",
        },
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_val_def_1",
            "path": "data/sample/val2.png",
            "category": "pcb",
            "condition": "shift_a",
            "split": "validation",
            "true_label": "defect",
            "model_version": "v1_current",
            "anomaly_score": 0.85,
            "map_path": "results/maps/v1/val2.png",
            "device": "cpu",
        },
        {
            "run_id": "sample-cpu-20261013T120000",
            "image_id": "img_val_def_1",
            "path": "data/sample/val2.png",
            "category": "pcb",
            "condition": "shift_a",
            "split": "validation",
            "true_label": "defect",
            "model_version": "v2_candidate_loose",
            "anomaly_score": 0.35,
            "map_path": "results/maps/v2/val2.png",
            "device": "cpu",
        },
    ]
    return pd.DataFrame(rows)


def test_valid_scores_passes() -> None:
    """Assert that a valid DataFrame passes without raising an error."""
    df = make_valid_df()
    validate_scores(df, versions_needed=["v1_current", "v2_candidate_loose"])


def test_missing_column_raises() -> None:
    """Assert that missing required columns raise ScoresError."""
    df = make_valid_df().drop(columns=["anomaly_score"])
    with pytest.raises(ScoresError, match="Missing required columns"):
        validate_scores(df)


def test_nan_anomaly_score_raises() -> None:
    """Assert that NaN anomaly scores raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "anomaly_score"] = float("nan")
    with pytest.raises(ScoresError, match="contains NaN or infinite values"):
        validate_scores(df)


def test_invalid_label_raises() -> None:
    """Assert that invalid true_label values raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "true_label"] = "unknown"
    with pytest.raises(ScoresError, match="Invalid true_label values"):
        validate_scores(df)


def test_invalid_split_raises() -> None:
    """Assert that invalid split values raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "split"] = "train"
    with pytest.raises(ScoresError, match="Invalid split values"):
        validate_scores(df)


def test_invalid_device_raises() -> None:
    """Assert that invalid device values raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "device"] = "cuda:0"
    with pytest.raises(ScoresError, match="Invalid device values"):
        validate_scores(df)


def test_multiple_run_ids_raises() -> None:
    """Assert that multiple run_ids in the same file raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "run_id"] = "sample-cpu-20261013T999999"
    with pytest.raises(ScoresError, match="Expected exactly one run_id"):
        validate_scores(df)


def test_duplicate_image_model_version_raises() -> None:
    """Assert that duplicate (image_id, model_version) rows raise ScoresError."""
    df = make_valid_df()
    extra_row = df.iloc[[0]].copy()
    df = pd.concat([df, extra_row], ignore_index=True)
    with pytest.raises(ScoresError, match="Duplicate"):
        validate_scores(df)


def test_image_in_multiple_splits_raises() -> None:
    """Assert that an image appearing in multiple splits raises ScoresError."""
    df = make_valid_df()
    df.loc[1, "split"] = "validation"  # img_cal_1 is now in both calibration and validation
    with pytest.raises(ScoresError, match="Images present in multiple splits"):
        validate_scores(df)


def test_calibration_with_defect_raises() -> None:
    """Assert that defect labels in calibration split raise ScoresError."""
    df = make_valid_df()
    df.loc[0, "true_label"] = "defect"
    with pytest.raises(ScoresError, match="Calibration split contains non-good images"):
        validate_scores(df)


def test_missing_required_model_version_raises() -> None:
    """Assert that missing required version raises ScoresError."""
    df = make_valid_df()
    with pytest.raises(ScoresError, match="Required model version.*missing"):
        validate_scores(df, versions_needed=["v1_current", "v3_candidate_reviewed"])


def test_validation_image_missing_in_one_version_raises() -> None:
    """Assert that an un-scored validation image in one version is reported by name."""
    df = make_valid_df()
    # Remove v2 score for img_val_def_1
    df = df[~((df["model_version"] == "v2_candidate_loose") & (df["image_id"] == "img_val_def_1"))]
    with pytest.raises(ScoresError, match=r"Validation images missing in version 'v2_candidate_loose': \['img_val_def_1'\]"):
        validate_scores(df, versions_needed=["v1_current", "v2_candidate_loose"])
