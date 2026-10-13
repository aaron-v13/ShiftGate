"""Tests for thresholds, decisions, and metrics calculation."""

import numpy as np
import pandas as pd
import pytest
from gate.decisions import decide
from gate.metrics import compute_metrics
from gate.thresholds import compute_thresholds, get_threshold_warnings


def test_decide_ties_are_pass() -> None:
    """Assert that a score strictly greater than threshold is HOLD, but equal is PASS."""
    assert decide(0.50, 0.50) == "PASS"
    assert decide(0.5001, 0.50) == "HOLD"
    assert decide(0.4999, 0.50) == "PASS"

    arr = np.array([0.4, 0.5, 0.6])
    res = decide(arr, 0.5)
    assert list(res) == ["PASS", "PASS", "HOLD"]


def test_thresholds_calibration_only() -> None:
    """Assert that compute_thresholds only depends on calibration scores."""
    df = pd.DataFrame([
        {"split": "calibration", "model_version": "v1", "anomaly_score": 0.1, "image_id": "i1"},
        {"split": "calibration", "model_version": "v1", "anomaly_score": 0.9, "image_id": "i2"},
        {"split": "validation", "model_version": "v1", "anomaly_score": 100.0, "image_id": "i3"},
    ])
    th = compute_thresholds(df, percentile=50.0)
    assert pytest.approx(th["v1"]) == 0.5

    # Changing validation score should not affect calibration threshold
    df.loc[2, "anomaly_score"] = 999.0
    th2 = compute_thresholds(df, percentile=50.0)
    assert pytest.approx(th2["v1"]) == 0.5


def test_threshold_warnings() -> None:
    """Assert warning emitted when version has fewer than 20 calibration images."""
    df = pd.DataFrame([
        {"split": "calibration", "model_version": "v1", "image_id": f"img_{i}", "anomaly_score": 0.1}
        for i in range(10)
    ])
    warns = get_threshold_warnings(df, min_count=20)
    assert len(warns) == 1
    assert "threshold for version 'v1' is based on 10 images" in warns[0]


def test_compute_metrics_zero_division() -> None:
    """Assert that empty defect/good sets yield None rates, not crash or invented values."""
    df_val = pd.DataFrame([
        {"image_id": "1", "condition": "c1", "true_label": "good"},
        {"image_id": "2", "condition": "c1", "true_label": "good"},
    ])
    metrics = compute_metrics(df_val, ["PASS", "HOLD"])
    assert metrics["n_good"] == 2
    assert metrics["n_defect"] == 0
    assert metrics["false_holds"] == 1
    assert metrics["defects_caught"] == 0
    assert metrics["false_hold_rate"] == 0.5
    assert metrics["defect_recall"] is None
    assert metrics["per_condition"]["c1"]["defect_recall"] is None
