# ShiftGate Scenario: The Scripted Inspection Bank Update

> [!IMPORTANT]
> The "bad update" scenario described here is **deliberately scripted by us** to simulate a careless engineering action. It is an intentional test case for the ShiftGate regression gating workflow, not a natural defect discovery.

## Context
In high-throughput PCB manufacturing, visual inspection stations rely on reference image banks (patch memory banks) of known-good boards. When factory conditions drift (e.g. natural day-to-evening lighting shifts, component supply variations), good boards trigger false holds because their visual features differ from the baseline reference bank.

To adapt to the shift (`shift_a`), engineers collect new reference candidates from the production floor to expand the memory bank.

## The Scripted Contamination Incident
1. **Candidate Pool Submission**: A set of candidate boards operating under `shift_a` is submitted to update the reference bank.
2. **The Scripted Flaw**: Along with legitimate normal boards, one or more actual defect boards (`contaminant`, exhibiting defect patterns such as Soldering Melt or Scratch) are mixed into the candidate pool.
3. **Two Update Scenarios**:
   - **Careless Update (`v2_candidate_loose`)**: An engineer bulk-approves all candidates without thorough review. The contaminant defect patches enter the reference memory bank. As a result, the detector learns that this defect appearance is "normal", newly missing real defects on the line.
   - **Reviewed Update (`v3_candidate_reviewed`)**: An engineer or automated gate properly identifies and excludes the contaminant image, including only verified normal boards from the candidate pool into the memory bank.

## Model Versions
- `v1_current`: Built solely from baseline good images (`reference_v1`). Catches defects well on baseline, but yields elevated false hold rates on `shift_a`.
- `v2_candidate_loose`: Contains `v1_current` + `candidate_pool` + scripted `contaminant`. Resolves false holds on `shift_a`, but creates catastrophic regression (misses critical defects).
- `v3_candidate_reviewed`: Contains `v1_current` + `candidate_pool` (clean). Resolves false holds on `shift_a` while maintaining high defect catch rate.

## Goal of ShiftGate
ShiftGate's automated gate evaluates candidate updates against a regression suite before deployment, catching and blocking `v2_candidate_loose` while allowing `v3_candidate_reviewed`.
