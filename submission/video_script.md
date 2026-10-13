# ShiftGate Demo Video Script (2–3 Minutes)

This video script follows the click-path demonstrated in `docs/DEMO_FLOW.md`.

---

## Scene 1: Introduction & The Factory Floor Crisis (0:00 – 0:30)
- **Visual**:
  - Title card: **ShiftGate: Safe Reference Updates for Visual AI Inspection on AMD ROCm**.
  - B-roll or schematic of a PCB manufacturing line with an automated optical inspection (AOI) station.
- **Narrator**:
  - "In electronics manufacturing, visual anomaly detectors like PatchCore inspect thousands of printed circuit boards every day.
  - But factory conditions change: ambient lighting shifts, suppliers alter solder mask finishes, or camera optics drift.
  - Suddenly, the station begins falsely flagging acceptable boards as defective, stalling production lines.
  - To clear the bottleneck, engineers often rush to update the model's reference bank with newly captured boards. But if an unreviewed defect slips into that reference bank, the AI learns that the defect is normal—allowing real defects to escape to customers.
  - This is ShiftGate: an automated safety gate that prevents dangerous inspection updates before they reach production."
- **On-Screen Captions**:
  - *Problem: Factory lighting drift spikes false alarms.*
  - *The Danger: Careless updates slip defects into reference banks.*
  - *Solution: ShiftGate verifies updates before deployment.*

---

## Scene 2: Station Profile & False-Hold Surge (0:30 – 0:55)
- **Visual**:
  - Screen recording of `app/main.py` (Station Profile).
  - Cursor highlights Active Version: `v1_current`, Station Category: `PCB`.
  - Cursor points to the false-hold count indicator under shifted condition (`shift_a`).
  - Demonstrator clicks `🔄 Reset Demo Registry`.
- **Narrator**:
  - "Here is our PCB station running in production on baseline version `v1_current`.
  - Because of lighting changes on the line, our current baseline is triggering false holds on acceptable boards.
  - Production wants an updated model immediately. But how can a quality engineer be certain that the proposed update won't compromise defect detection?"
- **On-Screen Captions**:
  - *Station Status: Active on v1_current baseline.*
  - *Alert: False holds detected on shifted boards.*

---

## Scene 3: The Update Pool & Careless Approval (0:55 – 1:20)
- **Visual**:
  - Navigate to Screen 2: `pages/2_Reference_Review.py`.
  - Display grid of proposed reference candidates collected under shifted conditions.
  - Highlight candidate images, pausing briefly on the contaminant defect image.
- **Narrator**:
  - "Here is the candidate pool collected from the shifted line.
  - Notice this candidate board: to an untrained eye or under time pressure, it might be approved in bulk. But it actually contains a subtle defect.
  - If an engineer carelessly approves all candidates including this defect, we create candidate `v2_candidate_loose`.
  - If we carefully screen it out, we create candidate `v3_candidate_reviewed`.
  - Let's see what happens if someone attempts to deploy the careless update."
- **On-Screen Captions**:
  - *Candidate Pool: Proposed boards from shifted distribution.*
  - *The Trap: An unreviewed defect in the reference pool.*

---

## Scene 4: The Hero Screen & The Blocked Regression (1:20 – 1:55)
- **Visual**:
  - Navigate to Screen 3: `pages/3_Compare_Versions.py`.
  - Select `v2_candidate_loose` in sidebar. False holds drop significantly.
  - Navigate to Screen 4: `pages/4_Changed_Decisions.py` (Hero Screen).
  - Prominent red alert banner appears: **`CRITICAL SAFETY VIOLATION: newly missed defect`**.
  - Click on the red highlighted defect row. Split viewer displays the PCB image and PatchCore anomaly heatmap.
  - Cursor highlights the score drop (dropping below threshold into PASS).
- **Narrator**:
  - "Looking at standard dashboard metrics, candidate v2 looks like an apparent success: false holds dropped dramatically!
  - But our Changed Decisions screen reveals what aggregate metrics hide: a critical safety violation!
  - Under candidate v2, a real defective board that was previously caught by baseline v1 now passes straight through.
  - Why? Because the contaminant defect in v2's reference bank taught the model that this flaw is normal.
  - ShiftGate pinpoints the exact image, the score drop, and the heatmap before this update can ever touch the line."
- **On-Screen Captions**:
  - *Dashboard Trap: False holds dropped, but...*
  - *CRITICAL REGRESSION: Real defect now passes!*
  - *Hero Screen: Exact image and anomaly score regression exposed.*

---

## Scene 5: Gate Enforcement, Reviewed Update & Safe Activation (1:55 – 2:25)
- **Visual**:
  - Navigate to Screen 5: `pages/5_Decision.py`.
  - Show the prominent red **`🛑 BLOCK`** badge for candidate v2 with disabled deployment controls.
  - Switch candidate to `v3_candidate_reviewed`.
  - Screen updates to a bright green **`✅ ALLOW`** badge.
  - Type reviewer name and note, then click **`🚀 Approve & Activate Update`**.
  - Show active version change to `v3_candidate_reviewed` and rollback button available.
- **Narrator**:
  - "On the Decision screen, ShiftGate's safety policy enforces an immutable BLOCK on candidate v2. Activation is completely locked.
  - When we switch to candidate `v3_candidate_reviewed`—where the contaminant was excluded—the gate evaluates all policy checks: false holds are reduced, defect recall remains 100%, and zero defects are missed.
  - The status switches to ALLOW.
  - Quality sign-off is mandatory: the engineer enters their credentials and audit note, then activates the update.
  - ShiftGate immediately updates the station registry, while retaining one-click instant rollback to the previous baseline."
- **On-Screen Captions**:
  - *Policy: Candidate v2 is BLOCKED from deployment.*
  - *Candidate v3 ALLOWED: False holds reduced, zero defect escapes.*
  - *Audited Activation & Instant Rollback.*

---

## Scene 6: AMD ROCm Execution & Audit Export (2:25 – 2:50)
- **Visual**:
  - Cut to terminal/video overlay showing live execution on AMD Developer Cloud:
    `python -m pipeline.run_pipeline --config config.yaml --device cuda`
  - Show HIP / ROCm device verification: `torch.version.hip`.
  - Cut back to Screen 6: `pages/6_Export.py`.
  - Show SHA-256 hashes of the scores file, policy snapshot, and version IDs stored in the export.
  - Click `⬇️ Download Audit Package`.
- **Narrator**:
  - "Under the hood, feature extraction and reference scoring run on AMD ROCm GPUs using AMD Developer Cloud hardware. GPU speed and benchmark throughput are tracked in the benchmark suite once the full run completes.
  - On the Export screen, ShiftGate compiles an audit bundle where SHA-256 hashes of the scores file and policy are stored in the audit export so later changes can be detected.
  - Quality teams download a complete, audit-ready package meeting ISO 9001 and IATF 16949 standards."
- **On-Screen Captions**:
  - *Executed on AMD ROCm (AMD Developer Cloud).*
  - *Hardware-verified via PyTorch HIP (Speed: TODO(human) pending benchmark.json).*
  - *SHA-256 hashes stored in audit export to detect later changes.*

---

## Scene 7: Conclusion (2:50 – 3:00)
- **Visual**:
  - Project summary slide with GitHub link and AMD Hackathon branding.
- **Narrator**:
  - "ShiftGate brings reliability, safety, and accountability to industrial visual AI updates. Powered by AMD ROCm. Thank you."
- **On-Screen Captions**:
  - *ShiftGate — Safe Visual Inspection Updates.*
  - *AMD Developer Hackathon ACT III.*
