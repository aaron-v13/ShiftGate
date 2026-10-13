"""Comparison logic between current and candidate model versions and policy evaluation."""

from typing import Any
import pandas as pd
from gate.decisions import decide

CHANGE_TYPE_ORDER = {
    "newly_missed_defect": 1,
    "good_newly_held": 2,
    "newly_caught_defect": 3,
    "good_released": 4,
}


def find_changed_decisions(
    df_val_current: pd.DataFrame,
    current_thresh: float,
    df_val_cand: pd.DataFrame,
    cand_thresh: float,
) -> list[dict[str, Any]]:
    """Compare validation decisions between versions and return ordered changed decisions."""
    curr_df = df_val_current.set_index("image_id")
    cand_df = df_val_cand.set_index("image_id")

    common_ids = sorted(list(set(curr_df.index).intersection(set(cand_df.index))))
    changed: list[dict[str, Any]] = []

    for img_id in common_ids:
        curr_row = curr_df.loc[img_id]
        cand_row = cand_df.loc[img_id]

        curr_score = float(curr_row["anomaly_score"])
        cand_score = float(cand_row["anomaly_score"])

        curr_dec = decide(curr_score, current_thresh)
        cand_dec = decide(cand_score, cand_thresh)

        if curr_dec == cand_dec:
            continue

        true_label = str(curr_row["true_label"])
        condition = str(curr_row["condition"])

        if true_label == "defect":
            if curr_dec == "HOLD" and cand_dec == "PASS":
                change_type = "newly_missed_defect"
            elif curr_dec == "PASS" and cand_dec == "HOLD":
                change_type = "newly_caught_defect"
            else:
                continue
        elif true_label == "good":
            if curr_dec == "HOLD" and cand_dec == "PASS":
                change_type = "good_released"
            elif curr_dec == "PASS" and cand_dec == "HOLD":
                change_type = "good_newly_held"
            else:
                continue
        else:
            continue

        changed.append({
            "image_id": img_id,
            "condition": condition,
            "true_label": true_label,
            "current_decision": curr_dec,
            "candidate_decision": cand_dec,
            "change_type": change_type,
        })

    # Sort in contract order: newly_missed_defect, good_newly_held, newly_caught_defect, good_released
    changed.sort(key=lambda d: (CHANGE_TYPE_ORDER.get(d["change_type"], 99), d["image_id"]))
    return changed


def evaluate_policy(
    current_metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
    changed_decisions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[str, list[str]]:
    """Evaluate candidate against policy thresholds, returning activation status and plain-language reasons."""
    reasons: list[str] = []

    max_missed = policy.get("max_newly_missed_defects", 0)
    min_recall = policy.get("min_defect_recall", 0.8)
    min_fh_red = policy.get("min_false_hold_reduction", 1)
    require_all_cond = policy.get("require_all_conditions", True)

    missed_list = [d for d in changed_decisions if d["change_type"] == "newly_missed_defect"]
    n_missed = len(missed_list)

    # 1. Newly missed defects
    if n_missed > max_missed:
        missed_details = [f"image {d['image_id']} (condition {d['condition']})" for d in missed_list]
        reasons.append(f"{n_missed} defect(s) now pass: " + ", ".join(missed_details))

    # 2. Defect recall
    cand_recall = candidate_metrics.get("defect_recall")
    if cand_recall is not None and cand_recall < min_recall:
        reasons.append(
            f"Candidate overall defect recall ({cand_recall:.1%}) is below required minimum ({min_recall:.1%})"
        )

    # 3. False-hold reduction
    fh_reduction = current_metrics["false_holds"] - candidate_metrics["false_holds"]
    if fh_reduction < min_fh_red:
        reasons.append(
            f"Candidate false-hold reduction ({fh_reduction}) is less than required minimum ({min_fh_red})"
        )

    # 4. Require all conditions
    if require_all_cond:
        per_cond = candidate_metrics.get("per_condition", {})
        for cond, cond_met in sorted(per_cond.items()):
            cond_missed = [d for d in missed_list if d["condition"] == cond]
            if len(cond_missed) > max_missed and n_missed <= max_missed:
                # If already flagged globally, this provides condition-specific context if not already listed
                missed_details = [f"image {d['image_id']}" for d in cond_missed]
                reasons.append(f"Condition '{cond}' has {len(cond_missed)} newly missed defect(s): " + ", ".join(missed_details))

            cond_recall = cond_met.get("defect_recall")
            if cond_recall is not None and cond_recall < min_recall:
                reasons.append(
                    f"Candidate defect recall for condition '{cond}' ({cond_recall:.1%}) is below required minimum ({min_recall:.1%})"
                )

    if reasons:
        activation = "BLOCK"
    else:
        activation = "ALLOW"
        recall_str = f"{cand_recall:.1%}" if cand_recall is not None else "N/A"
        reasons.append(
            f"Candidate reduces false holds by {fh_reduction} (from {current_metrics['false_holds']} to {candidate_metrics['false_holds']}) with zero newly missed defects and defect recall {recall_str}."
        )

    return activation, reasons
