"""Deterministic train/validation/test/calibration split generation."""
import argparse
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd
import yaml

from pipeline.dataset import list_images
from pipeline.shifts import assign_conditions


def _partition_indices(indices: List[int], fractions: Dict[str, float], rng: np.random.Generator) -> Dict[str, List[int]]:
    """Partition indices according to target fractional proportions deterministically."""
    n = len(indices)
    keys = list(fractions.keys())
    # Compute initial target counts
    raw_counts = [int(round(n * fractions[k])) for k in keys]
    # Ensure at least 1 in each partition if possible
    counts = [max(1, c) for c in raw_counts]
    diff = sum(counts) - n
    if diff > 0:
        # Subtract from largest counts until sum matches
        while diff > 0:
            max_idx = int(np.argmax(counts))
            if counts[max_idx] > 1:
                counts[max_idx] -= 1
                diff -= 1
            else:
                break
    elif diff < 0:
        # Add to largest counts until sum matches
        while diff < 0:
            max_idx = int(np.argmax(counts))
            counts[max_idx] += 1
            diff += 1

    shuffled = rng.permutation(indices).tolist()
    partitions = {}
    start = 0
    for k, cnt in zip(keys, counts):
        partitions[k] = shuffled[start : start + cnt]
        start += cnt
    return partitions


def make_splits(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Assign every image deterministically to a split and write splits.csv."""
    rng = np.random.default_rng(cfg.get("seed", 42))
    df_work = df.copy()
    splits = [""] * len(df_work)
    df_work["split"] = splits

    # Step 1: Pick n_contaminant defect images
    n_contaminant = cfg.get("n_contaminant", 1)
    defects_mask = df_work["true_label"] == "defect"
    defect_indices = df_work[defects_mask].index.to_numpy()

    # Sort indices deterministically by image_id
    defect_indices = sorted(defect_indices, key=lambda idx: df_work.loc[idx, "image_id"])

    # Group defect indices by defect_type
    defects_by_type: Dict[str, List[int]] = {}
    for idx in defect_indices:
        dt = df_work.loc[idx, "defect_type"]
        defects_by_type.setdefault(dt, []).append(idx)

    # Prefer choosing contaminant from a defect type that has >= 2 images so validation gets same type
    chosen_dt = None
    for dt, idxs in defects_by_type.items():
        if len(idxs) >= (n_contaminant + 1):
            chosen_dt = dt
            break
    if chosen_dt is None:
        chosen_dt = list(defects_by_type.keys())[0]

    # Select contaminant from chosen type
    type_idxs = defects_by_type[chosen_dt]
    perm = rng.permutation(len(type_idxs)).tolist()
    contaminant_indices = [type_idxs[i] for i in perm[:n_contaminant]]
    for idx in contaminant_indices:
        df_work.loc[idx, "split"] = "contaminant"

    # Step 2: Split remaining defects by defect_fractions ensuring both conditions represented
    remaining_defects = [idx for idx in defect_indices if idx not in contaminant_indices]
    rem_baseline = [idx for idx in remaining_defects if df_work.loc[idx, "condition"] == "baseline"]
    rem_shift_a = [idx for idx in remaining_defects if df_work.loc[idx, "condition"] == "shift_a"]

    if len(rem_baseline) == 0 or len(rem_shift_a) == 0:
        raise ValueError("Cannot form defect splits: baseline or shift_a defects are empty.")

    part_def_base = _partition_indices(rem_baseline, cfg["defect_fractions"], rng)
    part_def_shift = _partition_indices(rem_shift_a, cfg["defect_fractions"], rng)

    for sp in ["validation", "test"]:
        for idx in part_def_base.get(sp, []):
            df_work.loc[idx, "split"] = sp
        for idx in part_def_shift.get(sp, []):
            df_work.loc[idx, "split"] = sp

    # Step 3: Split good images per condition by fractions
    good_mask = df_work["true_label"] == "good"
    good_indices = df_work[good_mask].index.to_numpy()
    good_indices = sorted(good_indices, key=lambda idx: df_work.loc[idx, "image_id"])

    good_base = [idx for idx in good_indices if df_work.loc[idx, "condition"] == "baseline"]
    good_shift = [idx for idx in good_indices if df_work.loc[idx, "condition"] == "shift_a"]

    if len(good_base) == 0 or len(good_shift) == 0:
        raise ValueError("Cannot form good splits: baseline or shift_a good images are empty.")

    part_good_base = _partition_indices(good_base, cfg["fractions"]["baseline"], rng)
    part_good_shift = _partition_indices(good_shift, cfg["fractions"]["shift_a"], rng)

    for sp, idxs in part_good_base.items():
        for idx in idxs:
            df_work.loc[idx, "split"] = sp

    for sp, idxs in part_good_shift.items():
        for idx in idxs:
            df_work.loc[idx, "split"] = sp

    # Verification: check for any empty required cell
    required_cells = [
        ("reference_v1", "baseline", "good"),
        ("candidate_pool", "shift_a", "good"),
        ("calibration", "baseline", "good"),
        ("calibration", "shift_a", "good"),
        ("validation", "baseline", "good"),
        ("validation", "shift_a", "good"),
        ("validation", "baseline", "defect"),
        ("validation", "shift_a", "defect"),
        ("test", "baseline", "good"),
        ("test", "shift_a", "good"),
        ("test", "baseline", "defect"),
        ("test", "shift_a", "defect"),
        ("contaminant", df_work.loc[contaminant_indices[0], "condition"], "defect"),
    ]

    for sp, cond, lbl in required_cells:
        match_cnt = len(df_work[(df_work["split"] == sp) & (df_work["condition"] == cond) & (df_work["true_label"] == lbl)])
        if match_cnt == 0:
            raise ValueError(f"Required split cell is empty: split={sp}, condition={cond}, label={lbl}")

    # Reorder columns as in contract: image_id, path, category, condition, split, true_label, defect_type
    out_cols = ["image_id", "path", "category", "condition", "split", "true_label", "defect_type"]
    result_df = df_work[out_cols].copy()

    # Write results/splits.csv
    results_dir = Path(cfg.get("results_dir", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(results_dir / "splits.csv", index=False)

    return result_df


def main() -> None:
    """CLI entrypoint for split generation and distribution reporting."""
    parser = argparse.ArgumentParser(description="Generate ShiftGate dataset splits")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    df_raw = list_images(cfg)
    df_cond = assign_conditions(df_raw, cfg)
    df_splits = make_splits(df_cond, cfg)

    print("Counts per split x condition x true_label:")
    summary = df_splits.groupby(["split", "condition", "true_label"]).size().reset_index(name="count")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
