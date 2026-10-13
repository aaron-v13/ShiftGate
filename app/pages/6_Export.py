"""ShiftGate Audit Export Screen (Screen 6)."""

import json
from pathlib import Path
import streamlit as st

from app.lib import (
    build_zip_archive,
    check_missing_files,
    get_app_paths,
    load_run_metadata,
    render_header,
    render_run_info,
)
from gate.api import export_bundle, get_registry, run_gate

st.set_page_config(
    page_title="ShiftGate - Audit Export",
    page_icon="📦",
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
    title="📦 Audit & Compliance Bundle Export",
    is_mock=paths.is_mock,
    subtitle="Export cryptographically verifiable evaluation bundles for production quality audit trails",
)

candidate_option = st.sidebar.selectbox(
    "Select Candidate Version to Export",
    options=["v2_candidate_loose", "v3_candidate_reviewed"],
    index=1,
)

try:
    report = run_gate(
        paths.scores_path,
        paths.policy_path,
        current=active_version,
        candidate=candidate_option,
    )
except Exception as e:
    st.error(f"Error preparing gate report: {e}")
    st.stop()

st.subheader(f"Export Bundle for Candidate `{candidate_option}`")
st.markdown(
    """
    Every inspection model deployment generates an immutable audit package containing:
    1. **`gate_report.json`**: Complete metrics, condition breakdowns, activation verdict, and timestamps.
    2. **`changed_decisions.csv`**: Granular itemized record of all decision shifts.
    3. **`policy_snapshot.yaml`**: Precise policy configuration governing the evaluation.
    4. **`hashes.json`**: SHA-256 checksums of raw scores, policy rules, and version identifiers.
    5. **`review_decisions.json`**: Operator candidate sign-offs (if available).
    """
)

# Export bundle to target directory
bundle_dir = paths.out_dir / f"bundle_{candidate_option}"
extra_files = []
if paths.review_decisions_path.exists():
    extra_files.append(paths.review_decisions_path)

try:
    exported_path = export_bundle(report, bundle_dir, extra_files=extra_files)
    zip_bytes = build_zip_archive(exported_path)
except Exception as e:
    st.error(f"Failed to assemble export bundle: {e}")
    st.stop()

st.markdown("### Cryptographic Hashes (SHA-256)")
hashes = report.get("hashes", {})
for k, v in hashes.items():
    st.code(f"{k}: {v}", language="text")

st.markdown("---")

col_dl, col_info = st.columns([1, 2])
with col_dl:
    st.download_button(
        label=f"⬇️ Download Audit Package ({candidate_option}.zip)",
        data=zip_bytes,
        file_name=f"shiftgate_bundle_{candidate_option}.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )

with col_info:
    st.info(f"Bundle successfully created on disk at: `{exported_path}`")

render_run_info(meta, paths.is_mock)
