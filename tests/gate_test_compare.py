"""Tests for version comparator and policy checks."""

import pandas as pd
import pytest
import yaml
from gate.compare import find_changed_decisions, evaluate_policy


def test_changed_decisions_ordering_and_filtering() -> None:
    """Assert changed decisions identify changes correctly and sort by contract order."""
    df_curr = pd.DataFrame([
        {"image_id": "img1", "true_label": "defect", "condition": "c1", "anomaly_score": 0.8}, # HOLD -> PASS
        {"image_id": "img2", "true_label": "good", "condition": "c1", "anomaly_score": 0.2},   # PASS -> HOLD
        {"image_id": "img3", "true_label": "defect", "condition": "c1", "anomaly_score": 0.2}, # PASS -> HOLD
        {"image_id": "img4", "true_label": "good", "condition": "c1", "anomaly_score": 0.8},   # HOLD -> PASS
        {"image_id": "img5", "true_label": "good", "condition": "c1", "anomaly_score": 0.2},   # PASS -> PASS (unchanged)
    ])
    df_cand = pd.DataFrame([
        {"image_id": "img1", "true_label": "defect", "condition": "c1", "anomaly_score": 0.2},
        {"image_id": "img2", "true_label": "good", "condition": "c1", "anomaly_score": 0.8},
        {"image_id": "img3", "true_label": "defect", "condition": "c1", "anomaly_score": 0.8},
        {"image_id": "img4", "true_label": "good", "condition": "c1", "anomaly_score": 0.2},
        {"image_id": "img5", "true_label": "good", "condition": "c1", "anomaly_score": 0.2},
    ])

    changed = find_changed_decisions(df_curr, 0.5, df_cand, 0.5)
    types = [d["change_type"] for d in changed]
    assert types == [
        "newly_missed_defect",
        "good_newly_held",
        "newly_caught_defect",
        "good_released",
    ]
    assert len(changed) == 4  # img5 is omitted


def test_evaluate_policy_block_and_allow() -> None:
    """Assert policy evaluation collects multiple failures and reports clear reasons."""
    policy = {
        "max_newly_missed_defects": 0,
        "min_defect_recall": 0.8,
        "min_false_hold_reduction": 1,
        "require_all_conditions": True,
    }

    # Case 1: Failure with newly missed defect and negative reduction
    curr_met = {"false_holds": 2, "defect_recall": 1.0}
    cand_met = {
        "false_holds": 3,  # reduction = -1 < 1
        "defect_recall": 0.75,  # 0.75 < 0.8
        "per_condition": {
            "c1": {"defect_recall": 0.75}
        }
    }
    changed = [
        {"image_id": "img_d1", "condition": "c1", "true_label": "defect", "change_type": "newly_missed_defect"}
    ]

    activation, reasons = evaluate_policy(curr_met, cand_met, changed, policy)
    assert activation == "BLOCK"
    assert len(reasons) >= 3
    assert any("img_d1" in r for r in reasons)
    assert any("recall" in r.lower() for r in reasons)
    assert any("false-hold reduction" in r.lower() for r in reasons)

    # Case 2: Clean pass
    cand_met_clean = {
        "false_holds": 0,
        "defect_recall": 1.0,
        "per_condition": {"c1": {"defect_recall": 1.0}}
    }
    activation_ok, reasons_ok = evaluate_policy(curr_met, cand_met_clean, [], policy)
    assert activation_ok == "ALLOW"
    assert len(reasons_ok) == 1
    assert "reduces false holds by 2" in reasons_ok[0]
