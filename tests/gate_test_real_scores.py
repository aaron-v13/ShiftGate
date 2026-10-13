"""Test gate evaluation with sample real scores fixture (plumbing test / SAMPLE RUN, not evidence)."""

from pathlib import Path
import pytest
from gate.api import run_gate
from gate.schema import validate_scores
import pandas as pd


@pytest.fixture
def sample_real_scores_path() -> Path:
    """Return path to sample_real_scores fixture (plumbing test / SAMPLE RUN)."""
    p = Path("tests/fixtures/sample_real_scores.csv")
    assert p.exists()
    return p


def test_sample_real_scores_schema(sample_real_scores_path: Path) -> None:
    """Assert sample real scores fixture passes schema validation."""
    df = pd.read_csv(sample_real_scores_path)
    validate_scores(df, ["v1_current", "v2_candidate_loose"])


def test_sample_real_scores_gate_evaluation(sample_real_scores_path: Path) -> None:
    """Assert gate evaluation executes correctly on sample real scores fixture (plumbing test)."""
    policy_path = Path("gate/policy.yaml")
    report = run_gate(sample_real_scores_path, policy_path, "v1_current", "v2_candidate_loose")

    assert report["activation"] == "BLOCK"
    assert report["device"] == "cpu"
    assert report["run_id"] == "sample-cpu-20261013T232238"
    missed = [d for d in report["changed_decisions"] if d["change_type"] == "newly_missed_defect"]
    assert len(missed) >= 1
