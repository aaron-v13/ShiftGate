"""Schema validation for scores DataFrame."""

from typing import Iterable, Sequence
import numpy as np
import pandas as pd


class ScoresError(ValueError):
    """Raised when scores data violates the contract schema."""
    pass


REQUIRED_COLUMNS: list[str] = [
    "run_id",
    "image_id",
    "path",
    "category",
    "condition",
    "split",
    "true_label",
    "model_version",
    "anomaly_score",
    "map_path",
    "device",
]

ALLOWED_LABELS: set[str] = {"good", "defect"}
ALLOWED_SPLITS: set[str] = {"calibration", "validation", "test"}
ALLOWED_DEVICES: set[str] = {"cpu", "rocm", "other_gpu"}


def validate_scores(df: pd.DataFrame, versions_needed: Sequence[str] | None = None) -> None:
    """Validate scores dataframe against contract schema and raise ScoresError on failure."""
    if not isinstance(df, pd.DataFrame):
        raise ScoresError("Input scores must be a pandas DataFrame.")

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ScoresError(f"Missing required columns: {sorted(missing_cols)}")

    if not pd.api.types.is_numeric_dtype(df["anomaly_score"]):
        raise ScoresError("Column 'anomaly_score' must be numeric.")

    if df["anomaly_score"].isna().any() or np.isinf(df["anomaly_score"]).any():
        raise ScoresError("Column 'anomaly_score' contains NaN or infinite values.")

    invalid_labels = set(df["true_label"].unique()) - ALLOWED_LABELS
    if invalid_labels:
        raise ScoresError(f"Invalid true_label values: {sorted(invalid_labels)}")

    invalid_splits = set(df["split"].unique()) - ALLOWED_SPLITS
    if invalid_splits:
        raise ScoresError(f"Invalid split values: {sorted(invalid_splits)}")

    invalid_devices = set(df["device"].unique()) - ALLOWED_DEVICES
    if invalid_devices:
        raise ScoresError(f"Invalid device values: {sorted(invalid_devices)}")

    unique_run_ids = df["run_id"].dropna().unique()
    if len(unique_run_ids) != 1:
        raise ScoresError(f"Expected exactly one run_id, found {len(unique_run_ids)}: {list(unique_run_ids)}")

    dups = df.duplicated(subset=["image_id", "model_version"])
    if dups.any():
        dup_rows = df[dups][["image_id", "model_version"]].to_dict(orient="records")
        raise ScoresError(f"Duplicate (image_id, model_version) found: {dup_rows[:5]}")

    splits_per_image = df.groupby("image_id")["split"].nunique()
    multi_split_images = splits_per_image[splits_per_image > 1].index.tolist()
    if multi_split_images:
        raise ScoresError(f"Images present in multiple splits: {sorted(multi_split_images)}")

    cal_rows = df[df["split"] == "calibration"]
    cal_non_good = cal_rows[cal_rows["true_label"] != "good"]
    if not cal_non_good.empty:
        raise ScoresError(f"Calibration split contains non-good images: {cal_non_good['image_id'].tolist()[:5]}")

    if versions_needed is not None:
        if isinstance(versions_needed, str):
            versions_list = [versions_needed]
        else:
            versions_list = list(versions_needed)

        available_versions = set(df["model_version"].unique())
        missing_versions = [v for v in versions_list if v not in available_versions]
        if missing_versions:
            raise ScoresError(f"Required model version(s) missing from scores: {missing_versions}")

        val_df = df[df["split"] == "validation"]
        all_val_images = set(val_df["image_id"].unique())
        for v in versions_list:
            v_val_images = set(val_df[val_df["model_version"] == v]["image_id"].unique())
            missing_images = all_val_images - v_val_images
            if missing_images:
                raise ScoresError(
                    f"Validation images missing in version '{v}': {sorted(list(missing_images))}"
                )
