# ShiftGate: Pitch Deck Outline (Slide by Slide)

## Slide 1: Title & Hook
- **Headline**: ShiftGate: Safe Reference Updates for Visual AI Inspection
- **Sub-headline**: Preventing Catastrophic Defect Escapes in Electronics Manufacturing
- **Track**: Track 1 — Intelligent Industry | AMD Developer Hackathon ACT III
- **Hook**: When lighting changes on the factory floor, optical AI starts crying wolf. When engineers rush to update it, they risk letting real defects escape to customers. ShiftGate stops dangerous updates at the gate.

---

## Slide 2: The Industrial Problem (False Holds & Drift)
- **The Reality**: High-speed PCB surface-mount lines inspect thousands of components per shift using visual anomaly detection (PatchCore).
- **The Shift**: Daily operational shifts (lighting angle changes, component supplier tint, camera lens adjustments) make normal boards look anomalous to the AI.
- **The Symptom**: False-hold rates spike suddenly (e.g. flagging acceptable boards). Production slows down, operators are inundated with false alarms, and pressure mounts to deploy an updated reference model immediately.

---

## Slide 3: The Hidden Trap: Contaminated Reference Updates
- **The Temptation**: To quickly clear false alarms under the new distribution, engineering gathers recent board images into a new candidate reference bank.
- **The Catastrophe**: If even one unreviewed defective board (e.g. with a subtle component displacement, scratching, or soldering melt) slips into the reference pool, the nearest-neighbor model adopts that defect appearance as "normal".
- **The Blindspot**: Standard model dashboards show false alarms plunging and declare victory—while real critical defects now pass undetected straight to downstream assembly.

---

## Slide 4: The Solution: The ShiftGate Workflow
- **Concept**: A quality gate and review cockpit between reference updates and station activation.
- **Core Pillars**:
  1. **Differential Regression Suite**: Compares every candidate against the baseline on a locked validation split across baseline and shifted conditions.
  2. **Zero-Tolerance Safety Policy**: Automatic immutable `BLOCK` if any previously caught defect is newly missed.
  3. **Changed Decisions Cockpit**: Exposes the exact images where decisions flipped, accompanied by anomaly localization maps.
  4. **Audited Governance**: Requires human reviewer sign-off for allowable updates, enforces a version registry, and enables instantaneous rollback.

---

## Slide 5: Architecture & AMD ROCm Acceleration
- **System 1 (AMD Accelerated Pipeline)**:
  - Deep feature extraction (WideResNet-50) and memory bank coreset subsampling.
  - Accelerated on AMD ROCm (HIP) using AMD Developer Cloud hardware.
  - Generates verifiable scores, metadata, and anomaly localization maps.
- **System 2 (Inspection Gate & Decision Cockpit)**:
  - Pure Python gate engine enforcing policy rules and cryptographic SHA-256 integrity.
  - Streamlit review interface with station status, differential metrics, and tamper-evident audit exports.

---

## Slide 6: Measurable Results (AMD Full Run)
- **Run Identifier**: `TODO(human): [AMD Full Run ID]`
- **Hardware Platform**: `TODO(human): [AMD Instinct GPU / ROCm Version via AMD Developer Cloud]`
- **Candidate Comparison**:
  - **Baseline (`v1_current`)**: High false-hold rate under shifted conditions (`TODO(human): X` false holds).
  - **Careless Update (`v2_candidate_loose`)**: Drastically reduces false holds (`TODO(human): Y` false holds), but newly misses critical defects (`TODO(human): Z` newly missed defects) &rarr; **`🛑 BLOCK`**.
  - **Reviewed Update (`v3_candidate_reviewed`)**: Matches the false-hold reduction (`TODO(human): Y` false holds) while preserving 100% defect recall (`TODO(human): 0` newly missed defects) &rarr; **`✅ ALLOW`**.
- *Note: Final quantitative benchmark numbers will be populated upon completion of the AMD Developer Cloud full run.*

---

## Slide 7: Honesty, Limits & Methodology Notes
- **Scripted Failure Scenario**: The contaminated reference update is scripted by design (simulating an engineer approving an unvetted batch) to rigorously demonstrate the gate mechanism. It is not presented as an accidental finding.
- **Anomaly Detection Novelty**: PatchCore is established literature; our primary innovation is the **update-gating, regression-testing, and approval workflow** for industrial vision systems.
- **Synthetic Shift**: Visual distribution shifts were generated with controlled lighting/contrast perturbations on the AmazonScience RobustAD PCB dataset.
- **Sample Size Context**: Validation sets are compact; results are reported with exact counts alongside percentages to represent workflow fidelity rather than unbounded factory scale.

---

## Slide 8: Business Value Hypothesis
- **Safety**: Eliminates silent defect escapes caused by careless model re-baselining, protecting brand reputation and preventing costly field recalls.
- **Triage Efficiency**: Slashes engineering investigation time by pinpointing exactly which board decisions flipped and why.
- **Auditability**: Produces cryptographic compliance bundles for ISO 9001 / IATF 16949 audit readiness.
- *Value Hypothesis*: Stated as a clear hypothesis to validate in plant trials: reducing update triage time by 70%+ while preventing reference contamination incidents.

---

## Slide 9: Summary & Project Links
- **GitHub Repository**: `TODO(human)`
- **Live Demo Application**: `TODO(human)`
- **Recorded Live AMD ROCm Run**: `TODO(human)`
- **Team**: ShiftGate Team (AMD Developer Hackathon ACT III)
