# ShiftGate Demo Flow (3-Minute Click Path)

This demo walkthrough tests the complete ShiftGate workflow using the sample dataset and mock environment.

---

## 0. Initial Setup & Launch
1. Ensure the app is running in mock mode:
   ```bash
   python -m streamlit run app/main.py
   ```
2. Note the prominent red **`SAMPLE DATA`** banner across all pages, signifying sample mock data.

---

## 1. Station Profile (`main.py`)
- **What to look at:**
  - Station category: **`PCB`**.
  - Active model version: **`v1_current`**.
  - Current false-hold count: **`6 boards`** on `shift_a` validation set.
- **Story to explain:**
  - Production lighting/environmental changes (`shift_a`) cause the current baseline reference model to flag 6 good circuit boards as false defects.
  - The station needs an updated reference bank to cut false alarms without compromising defect detection.
- **Action:**
  - Click **`🔄 Reset Demo Registry`** to confirm the station baseline starts fresh at `v1_current`.

---

## 2. Reference Review (`pages/2_Reference_Review.py`)
- **What to look at:**
  - The proposed candidates pool (`fake_cand_001` through `fake_cand_004`).
- **Story to explain:**
  - Proposed reference candidates were collected under `shift_a`.
  - Notice candidate `fake_cand_004` is a defective board (contaminant).
- **Action:**
  - If an engineer carelessly approves all candidates (including `fake_cand_004`), they create `v2_candidate_loose`.
  - If an engineer reviews carefully and rejects `fake_cand_004`, they build `v3_candidate_reviewed`.
  - Click **`💾 Save Review Decisions`**.

---

## 3. Compare Versions (`pages/3_Compare_Versions.py`)
- **What to look at:**
  - Select candidate **`v2_candidate_loose`** in the sidebar.
  - Metrics show false holds dropped from 6 to 1 (a reduction of 5 false holds!).
  - Defect recall appears high (7 of 8 defects caught).
- **Story to explain:**
  - At first glance in standard dashboard metrics, candidate v2 looks like an improvement because false holds dropped drastically.
  - But aggregate metrics hide individual escaped defects!

---

## 4. Changed Decisions (`pages/4_Changed_Decisions.py`) &mdash; The Hero Screen
- **What to look at:**
  - Notice the prominent red alert banner: **`CRITICAL SAFETY VIOLATION: 1 newly missed defect`**.
  - The Changed Decisions table highlights image `fake_val_defect_007` in red (`newly_missed_defect`).
- **Story to explain:**
  - Select `fake_val_defect_007` in the dropdown inspector.
  - Its anomaly score dropped from `0.85` in baseline to `0.44` in candidate v2 (below threshold `0.50`).
  - Because `fake_cand_004` (a similar defect) contaminated the reference bank, the model now considers this real defect to be "normal"!
  - ShiftGate exposes this regression immediately before it reaches the production line.

---

## 5. Gate Decision & Deployment (`pages/5_Decision.py`)
- **Step A: Inspect Candidate v2 (`v2_candidate_loose`):**
  - Big red **`🛑 BLOCK`** badge is displayed.
  - Reason clearly states: `1 defect(s) now pass: image fake_val_defect_007 (condition shift_a)`.
  - The "Approve & Activate Update" button is permanently locked.
- **Step B: Switch to Candidate v3 (`v3_candidate_reviewed`):**
  - Select `v3_candidate_reviewed` in the sidebar.
  - Status switches to big green **`✅ ALLOW`**.
  - Reason explains: `Candidate reduces false holds by 5 with zero newly missed defects and defect recall 100.0%`.
  - Enter reviewer name (e.g. `Jane Doe, Lead QA`) and approval note (`Curated shift_a bank with zero regressions`).
  - Click **`🚀 Approve & Activate Update`**.
  - Active version in the station registry updates immediately to `v3_candidate_reviewed`.
- **Step C: Rollback Capability:**
  - Note the "Rollback Target" now shows `v1_current`.
  - Clicking **`⏪ Rollback to Previous Baseline`** instantaneously restores `v1_current` if ever needed.

---

## 6. Audit & Compliance Export (`pages/6_Export.py`)
- **What to look at:**
  - Select `v3_candidate_reviewed`.
  - Review the SHA-256 hashes for the scores file, policy snapshot, and version IDs, which are stored in the audit export so later changes can be detected.
- **Action:**
  - Click **`⬇️ Download Audit Package`** to receive a timestamped zip archive containing `gate_report.json`, `changed_decisions.csv`, `policy_snapshot.yaml`, `hashes.json`, and `review_decisions.json`.
