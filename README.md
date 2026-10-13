# ShiftGate

> **Safe Reference Updates for Visual AI Inspection on AMD ROCm**  
> *Track 1: Intelligent Industry — AMD Developer Hackathon ACT III (lablab.ai)*

---

## 1. Problem & Industrial Context

In modern electronics manufacturing, automated optical inspection (AOI) systems rely on patch-based visual anomaly detection (such as PatchCore) to inspect high-density printed circuit boards (PCBs). However, production environments constantly shift: factory ambient lighting changes across work shifts, camera mounts undergo subtle vibration drift, or substrate batches exhibit visual surface variations.

When visual distribution shift occurs:
1. **False Alarms Spike**: The baseline model flags acceptable boards as anomalies, backing up production lines.
2. **The Update Pressure**: Under intense operational pressure to restore line throughput, quality engineers collect recent images from the shifted line to build a new reference memory bank.
3. **The Silent Trap**: If even a single unreviewed board containing a subtle defect (e.g. solder splash, component misalignment, scratch) enters the reference memory bank, the model memorizes that defect appearance as "normal."
4. **Catastrophic Defect Escapes**: Standard dashboards celebrate a reduction in false holds, while real defects now pass undetected to downstream assembly and end customers.

**ShiftGate** introduces a safety gate and inspection review cockpit between model updates and station deployment. It differential-evaluates candidate updates against locked regression suites, exposes newly missed defects, blocks dangerous updates automatically, and maintains an auditable deployment registry with one-click rollback.

---

## 2. Who It Is For

- **Quality & Process Engineers**: Reviewing and approving vision model updates with explainable, differential metrics and defect-level attribution before line activation.
- **Station Line Operators**: Protected from false alarm surges while assured that critical defect detection remains uncompromised.
- **Factory Quality Directors & Auditors**: Demanding tamper-evident, cryptographically verifiable compliance trails (ISO 9001, IATF 16949) for all vision AI updates.

---

## 3. How ShiftGate Works

```
                                      +------------------------------------+
                                      |   Factory Floor Visual Drift       |
                                      |   (Shifted Boards Collected)       |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |   System 1: Pipeline (AMD ROCm)    |
                                      |   - PatchCore Feature Extraction   |
                                      |   - Memory Bank Construction       |
                                      |   - Anomaly Scoring & Maps         |
                                      +-----------------+------------------+
                                                        | results/scores.csv
                                                        | results/run_meta.json
                                                        v
+-------------------------------------------------------------------------------------------------------+
| System 2: ShiftGate Core & Decision Cockpit                                                          |
|                                                                                                       |
|  [ Schema & Split Validation ]                                                                        |
|                 v                                                                                     |
|  [ Calibration Thresholds ]   (Derived exclusively from calibration normals at 99th percentile)       |
|                 v                                                                                     |
|  [ Differential Evaluator ]   (Candidate vs Baseline: false-hold delta, recall, changed decisions)    |
|                 v                                                                                     |
|  [ Policy Safety Engine ]                                                                             |
|         |                                                                                             |
|         +--> Newly Missed Defects > 0?  ------------>  🛑 BLOCK (Deployment Locked)                  |
|         +--> Defect Recall Degraded?    ------------>  🛑 BLOCK                                       |
|         +--> False-Hold Reduction OK?   ------------>  ✅ ALLOW (Awaiting Human Sign-off)             |
|                                                                                                       |
|  [ Governance & Activation ]                                                                          |
|         +--> Quality Reviewer Approval & Audit Note Required                                          |
|         +--> Atomic Version Registry Promotion (`v1_current` -> `v3_candidate_reviewed`)              |
|         +--> Instant One-Click Rollback Support                                                       |
|         +--> Cryptographic Compliance Export (SHA-256 Bundle: report, policy, decisions, hashes)      |
+-------------------------------------------------------------------------------------------------------+
```

---

## 4. Architecture & Repository Structure

ShiftGate cleanly decouples compute-heavy feature extraction from decision logic and UI:

```
ShiftGate/
├── app/                  # Streamlit review application (System 2)
│   ├── main.py           # Station Profile (Screen 1)
│   ├── lib.py            # UI logic, run-info cards, mode management
│   └── pages/            # Multi-page cockpit (Screens 2 through 6)
├── gate/                 # Core Gate logic (System 2)
│   ├── api.py            # Public gate API
│   ├── schema.py         # Schema validation & integrity guards
│   ├── thresholds.py     # Calibration-only percentile thresholding
│   ├── decisions.py      # Binary HOLD/PASS classification
│   ├── metrics.py        # False-hold and defect recall computations
│   ├── compare.py        # Decision delta analysis & policy evaluation
│   ├── registry.py       # Station version registry & rollback
│   └── policy.yaml       # Default inspection safety policy
├── pipeline/             # AMD ROCm detection pipeline (System 1)
│   ├── detector.py       # PatchCore feature extraction & nearest-neighbor scoring
│   ├── splits.py         # Deterministic split generation
│   ├── versions.py       # Reference bank construction (v1, v2 loose, v3 reviewed)
│   ├── run_pipeline.py   # End-to-end pipeline CLI
│   └── amd_smoke_test.py # Hardware verification on AMD ROCm (HIP)
├── data/sample/          # Minimal sample dataset for local plumbing tests
├── contracts/            # System boundary contracts & specifications
├── docs/                 # Walkthrough guides & click-paths (DEMO_FLOW.md)
├── submission/           # Lablab submission materials & pitch outlines
├── tests/                # Unit and integration test suites (pytest)
├── results/              # Verifiable outputs from pipeline runs
└── requirements.txt      # Two-section dependency manifest (torch unpinned)
```

---

## 5. Setup & Installation

### A. Environment & Dependencies

`requirements.txt` is structured into two clean sections for System 1 and System 2. In accordance with AMD ROCm deployment best practices, `torch` and `torchvision` are not pinned in `requirements.txt` to avoid conflicting with ROCm wheel indices.

#### For CPU Development / Local Evaluation:
```bash
# 1. Install PyTorch CPU build
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install ShiftGate dependencies
pip install -r requirements.txt
```

#### For AMD ROCm GPU Execution (AMD Developer Cloud):
```bash
# 1. Install ROCm-enabled PyTorch (e.g. ROCm 6.0+)
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0

# 2. Install ShiftGate dependencies
pip install -r requirements.txt
```

### B. Hardware Verification Smoke Test

Verify AMD ROCm hardware presence and HIP compatibility:
```bash
python -m pipeline.amd_smoke_test
```
- **Exit code 0**: AMD ROCm GPU verified and operational.
- **Exit code 2**: CPU or non-AMD environment detected.

---

## 6. Running ShiftGate

### A. Pipeline Execution

#### 1. CPU Plumbing Test (SAMPLE RUN)
To verify end-to-end data plumbing on a minimal sample:
```bash
python -m pipeline.run_pipeline --config config.yaml --device cpu
```
> **Note**: This run produces `sample-cpu-...` outputs and is strictly a plumbing test to verify data pipeline integration, not statistical evidence.

#### 2. AMD ROCm GPU Full Run
On the AMD Developer Cloud instance:
```bash
python -m pipeline.run_pipeline --config config.yaml --device cuda
```
In PyTorch ROCm environments, `--device cuda` maps directly to the AMD GPU via the HIP compatibility layer. `pipeline/device.py` validates `torch.version.hip`.

### B. Launching the Inspection Cockpit

#### Mock Demonstration Mode (Deterministic Synthetic Data)
```bash
python -m streamlit run app/main.py
```
*(Displays a permanent `SAMPLE DATA` banner for safe demonstration).*

#### Real Inspection Mode (Reading Pipeline Results)
```bash
SHIFTGATE_MODE=real python -m streamlit run app/main.py
```

### C. Running Automated Tests

Run the full gate and application test suite:
```bash
pytest tests/gate_test_*.py tests/app_test_*.py -q
```

---

## 7. Results & Verification

### A. AMD ROCm GPU Full Run (Awaiting Execution)

*The AMD Developer Cloud full run is currently in progress. Final quantitative benchmark metrics will be recorded below upon arrival:*

| Metric | Baseline (`v1_current`) | Careless Update (`v2_candidate_loose`) | Reviewed Update (`v3_candidate_reviewed`) |
|---|---|---|---|
| **Run ID** | `TODO(human)` | `TODO(human)` | `TODO(human)` |
| **Hardware** | `TODO(human)` | `TODO(human)` | `TODO(human)` |
| **Decision Threshold** | `TODO(human)` | `TODO(human)` | `TODO(human)` |
| **Shift False Holds** | `TODO(human)` | `TODO(human)` | `TODO(human)` |
| **Defect Recall** | `TODO(human)` | `TODO(human)` | `TODO(human)` |
| **Newly Missed Defects** | — | `TODO(human)` | `TODO(human)` |
| **Gate Safety Decision** | Active Baseline | **`🛑 BLOCK`** | **`✅ ALLOW`** |

### B. Note on the CPU Sample Run

The preliminary run (`sample-cpu-20261013T232238`) was conducted solely as a local **plumbing test (SAMPLE RUN)** to validate tensor pipelines, directory schemas, and score serialization. Containing only 2 calibration normals and 10 validation images, it does not serve as empirical evidence. All benchmark figures are deferred to the AMD full run.

---

## 8. Limitations & Honesty Notes

1. **Scripted Failure Scenario**: The failure case of `v2_candidate_loose` is deliberately scripted by design (simulating an engineer approving an unvetted batch that includes an unreviewed defect) to demonstrate safety gate enforcement. It is not presented as an organic defect discovery.
2. **Prior Work Attribution**: PatchCore is established literature (Roth et al., 2022). ShiftGate's core contribution is the **update-gating, differential regression evaluation, safety policy, and governance workflow**.
3. **Synthetic Shift**: Visual distribution shifts in testing were generated via calibrated lighting and contrast transformations on the PCB dataset.
4. **Validation Dataset Scope**: Because industrial validation sets are compact, ShiftGate always presents exact counts alongside percentage rates to prevent misleading rate interpretations.
5. **Business Value Hypothesis**: Operational savings (e.g. reduced engineering triage hours) are formulated as an empirical value hypothesis to be validated in factory trials, rather than guaranteed figures.

---

## 9. Deployment Architecture (STOP C Decision)

In alignment with hackathon guidelines, ShiftGate adopts **Option 2 (provisional)**:
- The Streamlit review cockpit is hosted publicly reading precomputed, cryptographically verified AMD Developer Cloud run results.
- A recorded live demonstration of the AMD ROCm GPU execution on AMD Developer Cloud hardware accompanies the submission to verify live hardware operation.

---

## 10. Dataset Credits & Licensing

- **Dataset**: Amazon Science RobustAD (PCB visual inspection category).
- **License**: Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
- **Attribution**: Courtesy of Amazon Science. Used for academic and benchmarking evaluation of visual anomaly detection under distribution shifts.
