"""Threshold calculation based on calibration split."""

from typing import Sequence
import numpy as np
import pandas as pd


def compute_thresholds(
    df: pd.DataFrame,
    percentile: float = 99.0,
    versions: Sequence[str] | None = None,
) -> dict[str, float]:
    """Compute anomaly score threshold for each model version from calibration scores."""
    cal_df = df[df["split"] == "calibration"]
    if versions is None:
        target_versions = sorted(cal_df["model_version"].unique().tolist())
    else:
        target_versions = list(versions)

    thresholds: dict[str, float] = {}
    for v in target_versions:
        v_scores = cal_df[cal_df["model_version"] == v]["anomaly_score"].to_numpy()
        if len(v_scores) == 0:
            thresholds[v] = 0.0
        else:
            thresholds[v] = float(np.percentile(v_scores, percentile))
    return thresholds


def get_threshold_warnings(
    df: pd.DataFrame,
    versions: Sequence[str] | None = None,
    min_count: int = 20,
) -> list[str]:
    """Generate warnings if any model version has fewer than min_count calibration normals."""
    cal_df = df[df["split"] == "calibration"]
    if versions is None:
        target_versions = sorted(cal_df["model_version"].unique().tolist())
    else:
        target_versions = list(versions)

    warnings: list[str] = []
    for v in target_versions:
        n_images = int(cal_df[cal_df["model_version"] == v]["image_id"].nunique())
        if n_images < min_count:
            warnings.append(f"threshold for version '{v}' is based on {n_images} images (fewer than {min_count})")
    return warnings
