"""ShiftGate Station Profile Screen (Screen 1)."""

import streamlit as st
from app.lib import (
    check_missing_files,
    get_app_paths,
    get_current_false_holds,
    load_run_metadata,
    load_scores_df,
    render_header,
    render_run_info,
)
from gate.api import get_registry, reset_registry

st.set_page_config(
    page_title="ShiftGate - Station Profile",
    page_icon="🛡️",
    layout="wide",
)

paths = get_app_paths()
missing = check_missing_files(paths)
if missing:
    for m in missing:
        st.error(m)
    st.stop()

meta = load_run_metadata(paths.meta_path)
df_scores = load_scores_df(paths.scores_path)
registry = get_registry(paths.registry_path)

render_header(
    title="🛡️ ShiftGate Inspection Station Profile",
    is_mock=paths.is_mock,
    subtitle="Automated update safety gate for visual PCB inspection stations",
)

# Station KPI Banner
col1, col2, col3, col4 = st.columns(4)

active_version = registry.get("active_version", "v1_current")
prev_version = registry.get("previous_version") or "None"
category = meta.get("dataset", {}).get("category", "pcb").upper()
current_fh = get_current_false_holds(df_scores, active_version, condition="shift_a")

with col1:
    st.metric(label="Inspection Station Category", value=category)

with col2:
    st.metric(label="Active Model Version", value=active_version)

with col3:
    st.metric(label="Previous Version (Rollback target)", value=prev_version)

with col4:
    st.metric(
        label="Current False Holds (shift_a validation)",
        value=f"{current_fh} boards",
        delta="- high hold rate" if current_fh > 0 else "optimal",
        delta_color="inverse",
    )

st.markdown("---")

left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("Station Status & Problem Overview")
    st.markdown(
        f"""
        - **Problem:** Production environmental change (`shift_a`, e.g. lighting or component variance) causes
          the current reference model (`{active_version}`) to flag normal boards as defects (**{current_fh} false holds**).
        - **Solution:** Engineers propose updated reference image banks to clear the false holds.
        - **Safety Risk:** An unverified or contaminated candidate bank might clear false holds while newly missing real defects.
        - **ShiftGate Role:** Validates candidate banks against regression suites, guarantees zero newly missed defects, and enables instantaneous one-click rollback.
        """
    )

with right_col:
    st.subheader("Demonstration Controls")
    st.write("Reset the station registry back to initial factory baseline:")
    if st.button("🔄 Reset Demo Registry", type="secondary", use_container_width=True):
        reset_registry(paths.registry_path)
        st.success("Station registry reset to baseline (active: `v1_current`, history cleared).")
        st.rerun()

    st.info("Navigate through the sidebar screens to review candidates, inspect changes, and evaluate safety gating.")

render_run_info(meta, paths.is_mock)
