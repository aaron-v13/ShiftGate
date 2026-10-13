"""Unit tests for pipeline split generation and consistency."""
import yaml
import pytest
from pipeline.dataset import list_images
from pipeline.shifts import assign_conditions
from pipeline.splits import make_splits


@pytest.fixture
def base_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_splits_no_overlap(base_config):
    """Verify that no image_id appears in multiple splits."""
    df_raw = list_images(base_config)
    df_cond = assign_conditions(df_raw, base_config)
    df_splits = make_splits(df_cond, base_config)

    assert len(df_splits) == len(df_splits["image_id"].unique())
    assert df_splits["split"].isna().sum() == 0
    assert (df_splits["split"] == "").sum() == 0


def test_splits_determinism(base_config):
    """Verify that using the same seed produces identical splits."""
    df_raw = list_images(base_config)
    df_cond1 = assign_conditions(df_raw, base_config)
    df_splits1 = make_splits(df_cond1, base_config)

    df_cond2 = assign_conditions(df_raw, base_config)
    df_splits2 = make_splits(df_cond2, base_config)

    assert df_splits1.equals(df_splits2)


def test_calibration_only_good(base_config):
    """Verify that calibration split contains only good images."""
    df_raw = list_images(base_config)
    df_cond = assign_conditions(df_raw, base_config)
    df_splits = make_splits(df_cond, base_config)

    calib = df_splits[df_splits["split"] == "calibration"]
    assert len(calib) > 0
    assert (calib["true_label"] == "good").all()


def test_reference_v1_only_baseline(base_config):
    """Verify that reference_v1 contains only baseline good images."""
    df_raw = list_images(base_config)
    df_cond = assign_conditions(df_raw, base_config)
    df_splits = make_splits(df_cond, base_config)

    ref = df_splits[df_splits["split"] == "reference_v1"]
    assert len(ref) > 0
    assert (ref["condition"] == "baseline").all()
    assert (ref["true_label"] == "good").all()


def test_candidate_pool_only_shift_a(base_config):
    """Verify that candidate_pool contains only shift_a good images."""
    df_raw = list_images(base_config)
    df_cond = assign_conditions(df_raw, base_config)
    df_splits = make_splits(df_cond, base_config)

    cand = df_splits[df_splits["split"] == "candidate_pool"]
    assert len(cand) > 0
    assert (cand["condition"] == "shift_a").all()
    assert (cand["true_label"] == "good").all()


def test_contaminant_only_defect(base_config):
    """Verify that contaminant contains only defect images."""
    df_raw = list_images(base_config)
    df_cond = assign_conditions(df_raw, base_config)
    df_splits = make_splits(df_cond, base_config)

    contam = df_splits[df_splits["split"] == "contaminant"]
    assert len(contam) > 0
    assert (contam["true_label"] == "defect").all()
