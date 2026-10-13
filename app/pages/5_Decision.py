"""ShiftGate Decision Screen (Screen 5)."""

import streamlit as st

from app.lib import (
    check_missing_files,
    get_app_paths,
    load_run_metadata,
    render_header,
    render_run_info,
)
from gate.api import activate, get_registry, record_approval, rollback, run_gate

st.set_page_config(
    page_title="ShiftGate - Gate Decision",
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
prev_version = registry.get("previous_version")

render_header(
    title="⚖️ Gate Decision & Deployment Control",
    is_mock=paths.is_mock,
    subtitle="Enforce safety policy gates, record quality engineer approval, and activate or roll back updates",
)

candidate_option = st.sidebar.selectbox(
    "Select Candidate Version for Decision",
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
except Exception as e:
    st.error(f"Error computing gate decision: {e}")
    st.stop()

activation = report.get("activation", "BLOCK")
reasons = report.get("reasons", [])
warnings = report.get("warnings", [])

# Large Status Badge
if activation == "ALLOW":
    st.markdown(
        """
        <div style="background-color: #065F46; color: #ECFDF5; padding: 24px; border-radius: 10px;
                    text-align: center; margin-bottom: 24px; border: 2px solid #10B981;">
            <h1 style="margin: 0; font-size: 3rem; letter-spacing: 2px;">✅ ALLOW</h1>
            <p style="font-size: 1.25rem; margin-top: 8px;">Candidate passed all regression rules. Ready for quality engineer approval and activation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div style="background-color: #991B1B; color: #FEF2F2; padding: 24px; border-radius: 10px;
                    text-align: center; margin-bottom: 24px; border: 2px solid #EF4444;">
            <h1 style="margin: 0; font-size: 3rem; letter-spacing: 2px;">🛑 BLOCK</h1>
            <p style="font-size: 1.25rem; margin-top: 8px;">Candidate failed safety policy checks. Activation is strictly prohibited.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Policy Evaluation Reasons")
for r in reasons:
    if activation == "ALLOW":
        st.markdown(f"- 🟢 **Pass:** {r}")
    else:
        st.markdown(f"- 🔴 **Violation:** {r}")

if warnings:
    st.subheader("Statistical Warnings")
    for w in warnings:
        st.warning(f"⚠️ {w}")

st.markdown("---")

col_act, col_roll = st.columns(2)

with col_act:
    st.subheader("Reviewer Sign-off & Activation")
    st.markdown(
        f"Promote `{candidate_option}` to replace `{active_version}` on the production station."
    )

    reviewer = st.text_input("Quality Reviewer Name (required)", placeholder="e.g. Jane Doe, PE")
    note = st.text_area("Approval / Context Note", placeholder="e.g. Verified against lighting shift batch; no defects missed.")

    allow_can_activate = (activation == "ALLOW") and bool(reviewer.strip())

    if st.button("🚀 Approve & Activate Update", type="primary", disabled=not allow_can_activate):
        try:
            approved_report = record_approval(report, reviewer.strip(), note, registry_path=paths.registry_path)
            new_reg = activate(approved_report, registry_path=paths.registry_path)
            st.success(
                f"🎉 Successfully activated candidate `{new_reg['active_version']}`! "
                f"Previous version `{new_reg['previous_version']}` is preserved for rollback."
            )
            st.rerun()
        except Exception as err:
            st.error(f"Activation failed: {err}")

    if activation == "BLOCK":
        st.caption("🔒 Activation is locked because safety policy evaluated to BLOCK.")
    elif not reviewer.strip():
        st.caption("✍️ Please provide a reviewer name to unlock activation.")

with col_roll:
    st.subheader("Instant Rollback")
    st.markdown(
        f"Active Version: **`{active_version}`** | Rollback Target: **`{prev_version or 'None'}`**"
    )
    st.write(
        "If unexpected station behavior is detected on the factory floor, restore the previous baseline immediately."
    )

    can_rollback = prev_version is not None

    if st.button("⏪ Rollback to Previous Baseline", type="secondary", disabled=not can_rollback):
        try:
            rolled_reg = rollback(registry_path=paths.registry_path)
            st.success(f"Restored previous model version `{rolled_reg['active_version']}` as active.")
            st.rerun()
        except Exception as err:
            st.error(f"Rollback failed: {err}")

    if not can_rollback:
        st.caption("No previous version recorded in registry yet.")

render_run_info(meta, paths.is_mock)
