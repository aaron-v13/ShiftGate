# ShiftGate: Repository & Submission Checklist

Use this checklist to verify repository cleanliness, security, compliance, and readiness before submitting to Lablab.ai.

---

## 1. Repository Cleanliness & Source Control
- [x] **Branching & Git Structure**: Work completed on development branches (`system1-pipeline`, `system2-gate-app`) with clean history.
- [x] **No Secrets Committed**: Checked `.gitignore` and git history. No API keys, tokens, credentials, or private keys in the repository.
- [x] **No Raw Large Data**: `data/raw/` is excluded from git tracking. Only a minimal sample directory (`data/sample/`) is committed for testing.
- [x] **No Heavy Model Weights**: Pretrained embeddings downloaded via torchvision cache dynamically; no multi-gigabyte `.pt` or `.bin` weights committed.
- [x] **Clean Ignored Files**: Python cache (`__pycache__`, `.pytest_cache`), virtual environments (`.venv`, `env`), and OS artifacts (`.DS_Store`, `Thumbs.db`) properly excluded.

---

## 2. Requirements & Dependency Verification
- [x] **Two-Section Structure**: `requirements.txt` contains clean, separated sections for System 1 (AMD pipeline) and System 2 (Gate logic & review app).
- [x] **No Pinned Torch/Torchvision**: `torch` and `torchvision` are deliberately unpinned in `requirements.txt` to avoid conflicting with platform-specific AMD ROCm wheel indices (`--index-url https://download.pytorch.org/whl/rocm...`).
- [x] **Installation Instructions in README**: README clearly provides separate, working installation instructions for CPU development and AMD ROCm GPU deployment.

---

## 3. Dataset Licensing & Legal Compliance
- [x] **Dataset Source**: PCB inspection imagery sourced from Amazon Science RobustAD dataset (`AmazonScience/RobustAD`).
- [x] **License**: Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
- [x] **Attribution Included**: Proper copyright and attribution notice included in README, pipeline metadata, and submission documentation.

---

## 4. Hardware Verification & AMD Integrity
- [x] **AMD Smoke Test**: `pipeline/amd_smoke_test.py` validates AMD ROCm hardware presence and checks `torch.version.hip`.
- [x] **Hardware Labeling**: Run metadata truthfully logs `device: "rocm"` only when running on AMD HIP; CPU execution is explicitly labeled as `cpu` without claims of hardware acceleration.
- [x] **Plumbing Test vs Evidence**: CPU sample run (`sample-cpu-20261013T232238`) is clearly documented in all files as a plumbing test (SAMPLE RUN), not evidence.
- [x] **No Unsupported Claims**: All unbacked claims (cryptographic verification, speedup, savings, novelty, accuracy) removed or clarified. SHA-256 hashes of the scores file and policy are documented as stored in the audit export so later changes can be detected. All AMD speed claims are marked as TODO(human) until results/benchmark.json exists.
- [x] **Provisional Hosting Option**: Option 2 selected (host app reading precomputed AMD results + recorded live AMD ROCm GPU run), pending organizer confirmation.

---

## 5. Test Suite Verification
- [x] `tests/gate_test_schema.py`: Schema validation and error handling pass.
- [x] `tests/gate_test_fake_data.py`: Deterministic synthetic dataset scenario passes.
- [x] `tests/gate_test_metrics.py`: Metric calculation and division-by-zero guards pass.
- [x] `tests/gate_test_compare.py`: Priority sort and multi-rule policy evaluation pass.
- [x] `tests/gate_test_api.py`: Approval, activation, rollback, and export hashing pass.
- [x] `tests/gate_test_real_scores.py`: Plumbing test fixture verification passes.
- [x] `tests/app_test_lib.py`: Mode switching, UI helpers, and run info cards pass.
- [x] Full test pass: All 41 unit and integration tests passing.

---

## 6. Submission Finalization (Human Tasks)
- [ ] Push clean branch / tag to public GitHub repository (`TODO(human)`: URL in `submission/project_info.md`).
- [ ] Populate final AMD Developer Cloud run metrics in `README.md`, `submission/pitch_outline.md`, and `submission/project_info.md` upon completion of the full AMD ROCm run.
- [ ] Record and upload 2-3 minute demo video following `submission/video_script.md` (`TODO(human)`: link in `project_info.md`).
- [ ] Upload slide deck (`TODO(human)`: link in `project_info.md`).
- [ ] Export final cover image according to `submission/cover_image_brief.md`.
- [ ] Deploy live Streamlit application according to provisional Option 2 and verify public URL.
