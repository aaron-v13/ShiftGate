"""Comprehensive tests for gate.api, registry, approval, activation, rollback, and export."""

import hashlib
import json
from pathlib import Path
import tempfile
import pandas as pd
import pytest
import yaml

from gate.api import (
    activate,
    export_bundle,
    get_registry,
    record_approval,
    reset_registry,
    rollback,
    run_gate,
)
from gate.decisions import decide
from gate.schema import ScoresError
from gate.thresholds import compute_thresholds


@pytest.fixture
def fake_paths() -> tuple[Path, Path]:
    """Return paths to FAKE_scores.csv and policy.yaml."""
    scores_path = Path("gate/FAKE_scores.csv")
    policy_path = Path("gate/policy.yaml")
    assert scores_path.exists()
    assert policy_path.exists()
    return scores_path, policy_path


def test_loose_candidate_blocks_and_names_missed_defect(fake_paths: tuple[Path, Path]) -> None:
    """Assert loose candidate produces BLOCK and explicitly names the newly missed defect image."""
    scores_path, policy_path = fake_paths
    report = run_gate(scores_path, policy_path, "v1_current", "v2_candidate_loose")

    assert report["activation"] == "BLOCK"
    reasons_text = " ".join(report["reasons"])
    assert "fake_val_defect_007" in reasons_text
    assert any(d["image_id"] == "fake_val_defect_007" and d["change_type"] == "newly_missed_defect"
               for d in report["changed_decisions"])


def test_reviewed_candidate_allows(fake_paths: tuple[Path, Path]) -> None:
    """Assert reviewed candidate produces ALLOW with zero newly missed defects."""
    scores_path, policy_path = fake_paths
    report = run_gate(scores_path, policy_path, "v1_current", "v3_candidate_reviewed")

    assert report["activation"] == "ALLOW"
    assert not any(d["change_type"] == "newly_missed_defect" for d in report["changed_decisions"])
    assert len(report["reasons"]) >= 1


def test_threshold_tie_is_pass() -> None:
    """Assert a score exactly equal to threshold is evaluated as PASS."""
    assert decide(0.5000, 0.5000) == "PASS"


def test_missing_validation_image_raises_scores_error(fake_paths: tuple[Path, Path]) -> None:
    """Assert that a missing validation image raises a clear ScoresError naming the image."""
    scores_path, policy_path = fake_paths
    df = pd.read_csv(scores_path)
    # Remove one validation image from v2
    df = df[~((df["model_version"] == "v2_candidate_loose") & (df["image_id"] == "fake_val_good_000"))]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_scores = Path(tmpdir) / "scores.csv"
        df.to_csv(tmp_scores, index=False)
        with pytest.raises(ScoresError, match="fake_val_good_000"):
            run_gate(tmp_scores, policy_path, "v1_current", "v2_candidate_loose")


def test_thresholds_use_calibration_only() -> None:
    """Assert that mutating validation or test scores does not alter computed thresholds."""
    df = pd.read_csv("gate/FAKE_scores.csv")
    th_orig = compute_thresholds(df, percentile=99.0)

    # Corrupt validation anomaly scores
    df_corrupt = df.copy()
    val_mask = df_corrupt["split"] == "validation"
    df_corrupt.loc[val_mask, "anomaly_score"] = 9999.0
    th_corrupt = compute_thresholds(df_corrupt, percentile=99.0)

    assert th_orig == th_corrupt


def test_activation_refused_before_approval(fake_paths: tuple[Path, Path]) -> None:
    """Assert activate refuses with clear error when report has not been approved."""
    scores_path, policy_path = fake_paths
    report = run_gate(scores_path, policy_path, "v1_current", "v3_candidate_reviewed")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "registry.json"
        with pytest.raises(ValueError, match="without approval"):
            activate(report, registry_path=tmp_reg)


def test_activation_refused_on_block_report(fake_paths: tuple[Path, Path]) -> None:
    """Assert activate refuses with clear error when report status is BLOCK."""
    scores_path, policy_path = fake_paths
    report = run_gate(scores_path, policy_path, "v1_current", "v2_candidate_loose")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "registry.json"
        approved = record_approval(report, "Quality Engineer", "Override attempt", registry_path=tmp_reg)
        with pytest.raises(ValueError, match="when activation is BLOCK"):
            activate(approved, registry_path=tmp_reg)


def test_registry_workflow_approve_activate_rollback() -> None:
    """Assert registry workflow: approve -> activate -> rollback using isolated temporary registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_reg = Path(tmpdir) / "registry.json"

        # 1. Initial state
        reg = get_registry(tmp_reg)
        assert reg["active_version"] == "v1_current"
        assert reg["previous_version"] is None

        # 2. Rollback with no history errors clearly
        with pytest.raises(ValueError, match="no previous version"):
            rollback(registry_path=tmp_reg)

        # 3. Create ALLOW report and approve
        report = {
            "run_id": "test-run",
            "current_version": "v1_current",
            "candidate_version": "v3_candidate_reviewed",
            "activation": "ALLOW",
            "approved_by": None,
        }
        approved = record_approval(report, "Alice", "Looks solid", registry_path=tmp_reg)
        assert approved["approved_by"] == "Alice"
        assert report["approved_by"] is None  # Input was not mutated

        # 4. Activate
        reg_active = activate(approved, registry_path=tmp_reg)
        assert reg_active["active_version"] == "v3_candidate_reviewed"
        assert reg_active["previous_version"] == "v1_current"

        # 5. Rollback
        reg_rolled = rollback(registry_path=tmp_reg)
        assert reg_rolled["active_version"] == "v1_current"

        # 6. Reset
        reg_reset = reset_registry(registry_path=tmp_reg)
        assert reg_reset["active_version"] == "v1_current"
        assert reg_reset["history"] == []


def test_export_bundle_hashes_match_recomputation(fake_paths: tuple[Path, Path]) -> None:
    """Assert exported bundle files exist and SHA-256 hashes match independent recomputation."""
    scores_path, policy_path = fake_paths
    report = run_gate(scores_path, policy_path, "v1_current", "v3_candidate_reviewed")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "bundle"
        result_dir = export_bundle(report, out_dir)
        assert Path(result_dir) == out_dir

        # Check files exist
        assert (out_dir / "gate_report.json").exists()
        assert (out_dir / "changed_decisions.csv").exists()
        assert (out_dir / "policy_snapshot.yaml").exists()
        assert (out_dir / "hashes.json").exists()

        # Check hashes
        with open(out_dir / "hashes.json", "r", encoding="utf-8") as f:
            saved_hashes = json.load(f)

        expected_scores_hash = hashlib.sha256(scores_path.read_bytes()).hexdigest()
        expected_policy_hash = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        expected_v1_hash = hashlib.sha256("v1_current".encode("utf-8")).hexdigest()
        expected_v3_hash = hashlib.sha256("v3_candidate_reviewed".encode("utf-8")).hexdigest()

        assert saved_hashes["scores_file_sha256"] == expected_scores_hash
        assert saved_hashes["policy_file_sha256"] == expected_policy_hash
        assert saved_hashes["current_version_sha256"] == expected_v1_hash
        assert saved_hashes["candidate_version_sha256"] == expected_v3_hash
