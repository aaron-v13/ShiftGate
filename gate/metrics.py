"""Compute evaluation metrics on validation split."""

from typing import Any, Sequence
import pandas as pd


def _calculate_subset_metrics(df_sub: pd.DataFrame, decisions_sub: Sequence[str]) -> dict[str, Any]:
    """Calculate counts and rates for a given subset of validation rows."""
    n_good = int((df_sub["true_label"] == "good").sum())
    n_defect = int((df_sub["true_label"] == "defect").sum())

    is_hold = [d == "HOLD" for d in decisions_sub]
    is_good = (df_sub["true_label"] == "good").tolist()
    is_defect = (df_sub["true_label"] == "defect").tolist()

    false_holds = sum(1 for g, h in zip(is_good, is_hold) if g and h)
    defects_caught = sum(1 for dfct, h in zip(is_defect, is_hold) if dfct and h)

    false_hold_rate = round(false_holds / n_good, 4) if n_good > 0 else None
    defect_recall = round(defects_caught / n_defect, 4) if n_defect > 0 else None

    return {
        "n_good": n_good,
        "n_defect": n_defect,
        "false_holds": false_holds,
        "defects_caught": defects_caught,
        "false_hold_rate": false_hold_rate,
        "defect_recall": defect_recall,
    }


def compute_metrics(df_val: pd.DataFrame, decisions: Sequence[str]) -> dict[str, Any]:
    """Compute overall and per-condition validation metrics."""
    if len(df_val) != len(decisions):
        raise ValueError(f"Length mismatch: {len(df_val)} rows vs {len(decisions)} decisions")

    overall = _calculate_subset_metrics(df_val, decisions)

    # Per condition metrics
    per_condition: dict[str, dict[str, Any]] = {}
    conditions = sorted(df_val["condition"].unique().tolist())
    for cond in conditions:
        mask = (df_val["condition"] == cond).tolist()
        df_cond = df_val[mask]
        dec_cond = [d for d, m in zip(decisions, mask) if m]
        per_condition[cond] = _calculate_subset_metrics(df_cond, dec_cond)

    overall["per_condition"] = per_condition
    return overall
