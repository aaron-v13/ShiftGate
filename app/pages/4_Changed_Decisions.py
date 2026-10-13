"""ShiftGate Changed Decisions Hero Screen (Screen 4)."""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so app.* and gate.* are importable
# when Streamlit runs this file directly (Streamlit does not use pytest.ini).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd
import streamlit as st

from app.lib import (
    check_missing_files,
    get_app_paths,
    load_run_metadata,
    load_scores_df,
    render_header,
    render_run_info,
)
from gate.api import get_registry, run_gate

st.set_page_config(
    page_title="ShiftGate - Changed Decisions",
    page_icon="🚨",
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
active_version = registry.get("active_version", "v1_current")

render_header(
    title="🚨 Changed Decisions Inspector",
    is_mock=paths.is_mock,
    subtitle="Hero screen: Surface critical regression anomalies, good boards released, and newly missed defects",
)

candidate_option = st.sidebar.selectbox(
    "Select Candidate Version to Inspect",
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
    st.error(f"Error running gate comparator: {e}")
    st.stop()

changed_decisions = report.get("changed_decisions", [])
missed_defects = [d for d in changed_decisions if d["change_type"] == "newly_missed_defect"]
good_released = [d for d in changed_decisions if d["change_type"] == "good_released"]

# Alert banner
if missed_defects:
    st.error(
        f"🚨 **CRITICAL SAFETY VIOLATION:** Candidate `{candidate_option}` introduces "
        f"**{len(missed_defects)} newly missed defect(s)**! This candidate must be BLOCKED."
    )
else:
    st.success(
        f"✅ **NO MISSED DEFECTS:** Candidate `{candidate_option}` safely preserves 100% defect detection "
        f"while releasing {len(good_released)} false holds."
    )

st.markdown("### Summary of Inspection Decision Changes")
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(
        "Newly Missed Defects",
        len(missed_defects),
        delta="BLOCKER" if missed_defects else "Clean",
        delta_color="inverse",
    )
with m2:
    st.metric("Good Boards Released", len(good_released))
with m3:
    st.metric("Good Boards Newly Held", len([d for d in changed_decisions if d["change_type"] == "good_newly_held"]))
with m4:
    st.metric("Newly Caught Defects", len([d for d in changed_decisions if d["change_type"] == "newly_caught_defect"]))

if not changed_decisions:
    st.info("No changed decisions detected between versions.")
    st.stop()

# Convert changed decisions to DataFrame for interactive display
df_changed = pd.DataFrame(changed_decisions)

# Highlight styling function
def highlight_changes(val: str) -> str:
    """Colorize change types for table display."""
    if val == "newly_missed_defect":
        return "background-color: #7F1D1D; color: #FEE2E2; font-weight: bold;"
    if val == "good_released":
        return "background-color: #064E3B; color: #D1FAE5;"
    if val == "good_newly_held":
        return "background-color: #78350F; color: #FEF3C7;"
    if val == "newly_caught_defect":
        return "background-color: #1E3A8A; color: #DBEAFE;"
    return ""

st.subheader("Decision Changes Table")
styled_df = df_changed.style.map(highlight_changes, subset=["change_type"])
st.dataframe(styled_df, use_container_width=True)

st.markdown("---")
st.subheader("Inspect Specific Image & Anomaly Localization")

selected_id = st.selectbox(
    "Choose an image from changed decisions to examine:",
    options=df_changed["image_id"].tolist(),
    index=0,
)

selected_row = df_changed[df_changed["image_id"] == selected_id].iloc[0]
change_type = selected_row["change_type"]

# Retrieve scores for selected image
scores_sub = df_scores[df_scores["image_id"] == selected_id]
curr_row = scores_sub[scores_sub["model_version"] == active_version]
cand_row = scores_sub[scores_sub["model_version"] == candidate_option]

curr_score = float(curr_row["anomaly_score"].iloc[0]) if not curr_row.empty else 0.0
cand_score = float(cand_row["anomaly_score"].iloc[0]) if not cand_row.empty else 0.0
curr_th = report["thresholds"]["current"]
cand_th = report["thresholds"]["candidate"]

raw_img_path = str(curr_row["path"].iloc[0]) if not curr_row.empty else ""
map_img_path = str(cand_row["map_path"].iloc[0]) if not cand_row.empty else ""

col_meta, col_img, col_map = st.columns([1.5, 2, 2])

with col_meta:
    st.markdown(f"**Image:** `{selected_id}`")
    st.markdown(f"**True Label:** `{selected_row['true_label'].upper()}`")
    st.markdown(f"**Condition:** `{selected_row['condition']}`")
    st.markdown(f"**Change Type:** `{change_type}`")

    st.markdown("---")
    st.markdown(f"**Baseline (`{active_version}`):**")
    st.write(f"Score: `{curr_score:.4f}` | Thresh: `{curr_th:.4f}`")
    st.write(f"Decision: **`{selected_row['current_decision']}`**")

    st.markdown(f"**Candidate (`{candidate_option}`):**")
    st.write(f"Score: `{cand_score:.4f}` | Thresh: `{cand_th:.4f}`")
    st.write(f"Decision: **`{selected_row['candidate_decision']}`**")

    if change_type == "newly_missed_defect":
        st.error("⚠️ Score dropped below threshold due to reference contaminant!")


def get_placeholder(label: str, w: int = 280, h: int = 280) -> Image.Image:
    """Generate visual placeholder for missing files."""
    img = Image.new("RGB", (w, h), color=(15, 23, 42))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, w - 4, h - 4], outline=(71, 85, 105), width=2)
    d.text((20, h // 2 - 10), label, fill=(226, 232, 240))
    return img


with col_img:
    st.markdown("**Original Inspection Image**")
    p_img = Path(raw_img_path)
    if p_img.exists():
        try:
            st.image(Image.open(p_img), caption=f"Raw: {selected_id}", use_container_width=True)
        except Exception:
            st.image(get_placeholder(f"Image File:\n{selected_id}"), use_container_width=True)
    else:
        st.image(get_placeholder(f"Image Placeholder:\n{selected_id}"), use_container_width=True)

with col_map:
    st.markdown("**Anomaly Heatmap**")
    p_map = Path(map_img_path) if map_img_path else None
    if p_map and p_map.exists():
        try:
            st.image(Image.open(p_map), caption=f"Heatmap: {selected_id}", use_container_width=True)
        except Exception:
            st.image(get_placeholder(f"Heatmap:\n{selected_id}"), use_container_width=True)
    else:
        st.image(get_placeholder(f"Heatmap Placeholder:\n{selected_id}"), use_container_width=True)

render_run_info(meta, paths.is_mock)
