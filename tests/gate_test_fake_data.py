"""Tests asserting that gate/FAKE_scores.csv satisfies all contract properties."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from gate.schema import validate_scores


@pytest.fixture
def fake_scores_df() -> pd.DataFrame:
    """Load gate/FAKE_scores.csv."""
    path = Path("gate/FAKE_scores.csv")
    assert path.exists(), "gate/FAKE_scores.csv must exist"
    return pd.read_csv(path)


@pytest.fixture
def fake_meta() -> dict:
    """Load gate/FAKE_run_meta.json."""
    path = Path("gate/FAKE_run_meta.json")
    assert path.exists(), "gate/FAKE_run_meta.json must exist"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_fake_scores_schema(fake_scores_df: pd.DataFrame) -> None:
    """Assert that FAKE_scores passes strict schema validation."""
    validate_scores(fake_scores_df, ["v1_current", "v2_candidate_loose", "v3_candidate_reviewed"])


def test_fake_scores_ids_and_meta(fake_scores_df: pd.DataFrame, fake_meta: dict) -> None:
    """Assert run_id and image_id prefixes and metadata contract fields."""
    assert fake_meta["run_id"].startswith("FAKE-")
    assert fake_meta["notes"] == "FAKE"
    assert fake_meta["device"] == "cpu"
    assert not Path("results/FAKE_scores.csv").exists()

    run_id = fake_scores_df["run_id"].iloc[0]
    assert run_id.startswith("FAKE-")
    assert run_id == fake_meta["run_id"]

    for img_id in fake_scores_df["image_id"].unique():
        assert img_id.startswith("fake_"), f"image_id {img_id} must start with 'fake_'"


def test_fake_scores_splits_and_counts(fake_scores_df: pd.DataFrame) -> None:
    """Assert split and label counts per version."""
    for v in ["v1_current", "v2_candidate_loose", "v3_candidate_reviewed"]:
        v_df = fake_scores_df[fake_scores_df["model_version"] == v]
        cal = v_df[v_df["split"] == "calibration"]
        val = v_df[v_df["split"] == "validation"]

        assert len(cal) == 40
        assert (cal["true_label"] == "good").all()
        assert (cal["condition"] == "baseline").sum() == 20
        assert (cal["condition"] == "shift_a").sum() == 20

        val_good = val[val["true_label"] == "good"]
        val_defect = val[val["true_label"] == "defect"]
        assert len(val_good) == 30
        assert len(val_defect) == 8


def test_fake_scores_story_by_construction(fake_scores_df: pd.DataFrame) -> None:
    """Assert the core story holds: v2 misses a shift_a defect; v3 catches all; both cut false holds."""
    # Thresholds are 99th percentile of calibration
    thresholds = {}
    for v in ["v1_current", "v2_candidate_loose", "v3_candidate_reviewed"]:
        cal_scores = fake_scores_df[
            (fake_scores_df["model_version"] == v) & (fake_scores_df["split"] == "calibration")
        ]["anomaly_score"]
        thresholds[v] = float(np.percentile(cal_scores, 99))

    # Evaluate validation for each version
    def evaluate(v: str) -> tuple[int, int, list[str]]:
        val = fake_scores_df[
            (fake_scores_df["model_version"] == v) & (fake_scores_df["split"] == "validation")
        ]
        thresh = thresholds[v]
        # HOLD if score > thresh else PASS
        holds = val[val["anomaly_score"] > thresh]
        passes = val[val["anomaly_score"] <= thresh]

        false_holds = len(holds[holds["true_label"] == "good"])
        defects_caught = len(holds[holds["true_label"] == "defect"])
        missed_defects = passes[passes["true_label"] == "defect"]["image_id"].tolist()
        return false_holds, defects_caught, missed_defects

    v1_fh, v1_caught, v1_missed = evaluate("v1_current")
    v2_fh, v2_caught, v2_missed = evaluate("v2_candidate_loose")
    v3_fh, v3_caught, v3_missed = evaluate("v3_candidate_reviewed")

    # Story assertions
    assert v1_fh == 6, f"v1 expected 6 false holds, got {v1_fh}"
    assert v1_caught == 8 and len(v1_missed) == 0, "v1 must catch all 8 defects"

    assert v2_fh == 1, f"v2 expected 1 false hold, got {v2_fh}"
    assert len(v2_missed) == 1, f"v2 must miss exactly 1 defect, got {v2_missed}"
    assert v2_missed[0] == "fake_val_defect_007", f"v2 missed wrong defect: {v2_missed}"

    assert v3_fh == 1, f"v3 expected 1 false hold, got {v3_fh}"
    assert v3_caught == 8 and len(v3_missed) == 0, "v3 must catch all 8 defects"
