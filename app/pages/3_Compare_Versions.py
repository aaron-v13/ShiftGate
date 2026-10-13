"""ShiftGate Compare Versions Screen (Screen 3)."""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so app.* and gate.* are importable
# when Streamlit runs this file directly (Streamlit does not use pytest.ini).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from app.lib import (
    check_missing_files,
    get_app_paths,
    load_run_metadata,
    render_header,
    render_run_info,
    save_gate_report,
)
from gate.api import get_registry, run_gate

st.set_page_config(
    page_title="ShiftGate - Compare Versions",
    page_icon="⚖️",
    layout="wide",
)

paths = get_app_paths()
missing = check_missing_files(paths)
if missing:
    for m in missing:
        st.error(m)
    st.stop()

meta = load_run_metadata(paths.meta_path)
registry = get_registry(paths.registry_path)
active_version = registry.get("active_version", "v1_current")

render_header(
    title="⚖️ Side-by-Side Model Version Comparison",
    is_mock=paths.is_mock,
    subtitle="Evaluate regression metrics and false-hold reductions between current active and candidate model",
)

candidate_option = st.sidebar.selectbox(
    "Select Candidate Version to Compare",
    options=["v2_candidate_loose", "v3_candidate_reviewed"],
    index=0,
)

try:
    report = run_gate(
        paths.scores_path,
        paths.policy_path,
        current=active_version,
        candidate=candidate_option,
    )
    save_gate_report(report, candidate_option, paths)
except Exception as e:
    st.error(f"Error executing gate comparator: {e}")
    st.stop()

st.subheader(f"Current: `{active_version}` vs Candidate: `{candidate_option}`")

col_curr, col_cand = st.columns(2)

curr_met = report["metrics"]["current"]
cand_met = report["metrics"]["candidate"]
curr_th = report["thresholds"]["current"]
cand_th = report["thresholds"]["candidate"]

def format_rate(val: float | None) -> str:
    """Format float rate as percentage or N/A."""
    return f"{val:.1%}" if val is not None else "N/A"

with col_curr:
    st.markdown(f"### 📍 Current Baseline (`{active_version}`)")
    st.caption(f"Decision Threshold: `{curr_th:.4f}` (99th percentile of calibration)")

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            label="False Holds (Good boards held)",
            value=f"{curr_met['false_holds']} / {curr_met['n_good']}",
            help=f"Rate: {format_rate(curr_met['false_hold_rate'])}",
        )
    with c2:
        st.metric(
            label="Defects Caught (Recall)",
            value=f"{curr_met['defects_caught']} / {curr_met['n_defect']}",
            help=f"Rate: {format_rate(curr_met['defect_recall'])}",
        )

    st.markdown("**Per-Condition Breakdown (Validation Suite):**")
    for cond, cm in sorted(curr_met.get("per_condition", {}).items()):
        st.write(
            f"- **{cond}:** False Holds = `{cm['false_holds']}/{cm['n_good']}` ({format_rate(cm['false_hold_rate'])}) | "
            f"Defects Caught = `{cm['defects_caught']}/{cm['n_defect']}` ({format_rate(cm['defect_recall'])})"
        )

with col_cand:
    st.markdown(f"### 🚀 Candidate Version (`{candidate_option}`)")
    st.caption(f"Decision Threshold: `{cand_th:.4f}` (99th percentile of calibration)")

    fh_diff = curr_met['false_holds'] - cand_met['false_holds']
    def_diff = cand_met['defects_caught'] - curr_met['defects_caught']

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            label="False Holds (Good boards held)",
            value=f"{cand_met['false_holds']} / {cand_met['n_good']}",
            delta=f"-{fh_diff} holds" if fh_diff > 0 else (f"+{-fh_diff} holds" if fh_diff < 0 else "0 change"),
            delta_color="normal",
            help=f"Rate: {format_rate(cand_met['false_hold_rate'])}",
        )
    with c2:
        st.metric(
            label="Defects Caught (Recall)",
            value=f"{cand_met['defects_caught']} / {cand_met['n_defect']}",
            delta=f"{def_diff:+d} caught" if def_diff != 0 else "0 change",
            delta_color="normal",
            help=f"Rate: {format_rate(cand_met['defect_recall'])}",
        )

    st.markdown("**Per-Condition Breakdown (Validation Suite):**")
    for cond, cm in sorted(cand_met.get("per_condition", {}).items()):
        st.write(
            f"- **{cond}:** False Holds = `{cm['false_holds']}/{cm['n_good']}` ({format_rate(cm['false_hold_rate'])}) | "
            f"Defects Caught = `{cm['defects_caught']}/{cm['n_defect']}` ({format_rate(cm['defect_recall'])})"
        )

st.markdown("---")
st.info("👉 Check the **4_Changed_Decisions** screen to see individual board changes and newly missed defects.")

render_run_info(meta, paths.is_mock)
