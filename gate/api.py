"""Main API surface for Gate system (implements contract Section 9)."""

import hashlib
from pathlib import Path
from typing import Any, Sequence
import pandas as pd
import yaml

from gate.compare import evaluate_policy, find_changed_decisions
from gate.decisions import decide
from gate.export import export_bundle
from gate.metrics import compute_metrics
from gate.registry import (
    activate,
    get_registry,
    record_approval,
    reset_registry,
    rollback,
)
from gate.schema import validate_scores
from gate.thresholds import compute_thresholds, get_threshold_warnings

__all__ = [
    "run_gate",
    "record_approval",
    "activate",
    "rollback",
    "export_bundle",
    "get_registry",
    "reset_registry",
]


def _sha256_bytes(data: bytes) -> str:
    """Compute sha256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str | Path) -> str:
    """Compute sha256 hex digest of file contents."""
    return _sha256_bytes(Path(path).read_bytes())


def run_gate(
    scores_path: str | Path,
    policy_path: str | Path,
    current: str,
    candidate: str,
) -> dict[str, Any]:
    """Execute gate comparison between current and candidate versions and return gate report."""
    scores_p = Path(scores_path)
    policy_p = Path(policy_path)

    if not scores_p.exists():
        raise FileNotFoundError(f"Scores file not found: {scores_p}")
    if not policy_p.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_p}")

    df = pd.read_csv(scores_p)
    validate_scores(df, [current, candidate])

    with open(policy_p, "r", encoding="utf-8") as f:
        policy = yaml.safe_load(f) or {}

    threshold_pct = float(policy.get("threshold_percentile", 99.0))
    thresholds = compute_thresholds(df, percentile=threshold_pct, versions=[current, candidate])
    warnings = get_threshold_warnings(df, versions=[current, candidate])

    val_df = df[df["split"] == "validation"]
    val_curr = val_df[val_df["model_version"] == current]
    val_cand = val_df[val_df["model_version"] == candidate]

    curr_thresh = thresholds[current]
    cand_thresh = thresholds[candidate]

    curr_decisions = decide(val_curr["anomaly_score"], curr_thresh)
    cand_decisions = decide(val_cand["anomaly_score"], cand_thresh)

    curr_metrics = compute_metrics(val_curr, curr_decisions)
    cand_metrics = compute_metrics(val_cand, cand_decisions)

    changed_decisions = find_changed_decisions(val_curr, curr_thresh, val_cand, cand_thresh)
    activation, reasons = evaluate_policy(curr_metrics, cand_metrics, changed_decisions, policy)

    hashes = {
        "scores_file_sha256": _sha256_file(scores_p),
        "policy_file_sha256": _sha256_file(policy_p),
        "current_version_sha256": _sha256_bytes(current.encode("utf-8")),
        "candidate_version_sha256": _sha256_bytes(candidate.encode("utf-8")),
    }

    run_id = str(df["run_id"].iloc[0])
    device = str(df["device"].iloc[0])

    report: dict[str, Any] = {
        "run_id": run_id,
        "current_version": current,
        "candidate_version": candidate,
        "policy": policy,
        "thresholds": {
            "current": curr_thresh,
            "candidate": cand_thresh,
        },
        "metrics": {
            "current": curr_metrics,
            "candidate": cand_metrics,
        },
        "changed_decisions": changed_decisions,
        "activation": activation,
        "reasons": reasons,
        "warnings": warnings,
        "hashes": hashes,
        "approved_by": None,
        "approval_note": None,
        "approved_at": None,
        "device": device,
    }
    return report
