# System 2: Gate logic + review app + hosting + submission

Read `00_SHARED_CONTRACT.md` first and follow its working rules. You own `gate/`, `app/`, `docs/`, `submission/`, `tests/gate_*`, `tests/app_*`, `README.md`, and these files inside `results/`: `gate_report_*.json`, `review_decisions.json`, `exports/`. You never touch AMD resources or GPU/model code. You consume files that System 1 writes in `results/`.

## Work order (do not reorder)
1. **Part A: Gate** on `gate/FAKE_scores.csv`.
2. **Part B: App** on FAKE data, calling the real `gate.api`.
3. **STOP B:** swap in real scores from System 1 (CPU sample first, AMD run later).
4. **STOP C:** hosting + AMD visibility decision (the human decides).
5. **Part C: Submission package + README**, using real results only.

## Sync points with System 1
- Sync 1: System 1 commits the CPU-sample `results/` (run id starts with `sample-`). Pull it at STOP B.
- Sync 2: System 1 commits the AMD run. Re-run the gate, app and docs against it.

---

# Part A: Gate (`gate/`)

Expose everything through `gate/api.py` exactly as in the contract (section 9). Put logic in the small modules below; `api.py` only wires them together.

## A1: Schema validation (`gate/schema.py`)
`validate_scores(df, versions_needed)` raises `ScoresError` with a plain-language message. Checks:
- all contract columns exist; `anomaly_score` is numeric and finite (no NaN);
- `true_label` in {good, defect}; `split` in {calibration, validation, test}; `device` in {cpu, rocm, other_gpu};
- exactly one `run_id`;
- no duplicate (`image_id`, `model_version`); each `image_id` is in exactly one split;
- `calibration` rows are all `good`;
- both compared versions exist, and **every validation image is scored by both** (name the missing image ids).

CHECK: `pytest tests/gate_test_schema.py -q`.

## A2: Fake data (`gate/fake_data.py`)
Generate `gate/FAKE_scores.csv` with a fixed seed. Rules: run id starts with `FAKE-`, image ids start with `fake_`, never write it into `results/`. Build it so the story holds by construction (not by luck):
- About 40 calibration normals, 30 validation good, 8 validation defects, split across `baseline` and `shift_a`.
- `v1_current`: good `shift_a` boards score high (several false holds); all defects held.
- `v2_candidate_loose`: fewer false holds, but exactly one `shift_a` defect scores just under its threshold.
- `v3_candidate_reviewed`: fewer false holds than v1 and all defects held.
- Include one score exactly equal to a threshold-adjacent value in a unit test (see A6) to cover ties.
- Add a test that asserts this story on the fake file, so it cannot silently drift.
- Also generate `gate/FAKE_run_meta.json` (device `cpu`, run id matches, `notes: "FAKE"`).

## A3: Thresholds, decisions, metrics
- `gate/thresholds.py`: `compute_thresholds(df, percentile) -> dict[version, float]` = `numpy.percentile` of that version's **calibration** scores only. Add a warning string to the report when a version has fewer than 20 calibration normals ("threshold is based on N images").
- `gate/decisions.py`: `decide(scores, threshold)`: `HOLD` if score > threshold else `PASS`.
- `gate/metrics.py`: `compute_metrics(df_val, decisions) ->` the exact fields in the contract, overall and per condition. Division by zero gives `null`, never a made-up number.

## A4: Comparator and policy
- `gate/policy.yaml`: the default from the contract.
- `gate/compare.py`: join validation images on `image_id`, assign `change_type`, sort in the contract order.
- Policy checks (collect ALL failures, do not stop at the first):
  1. newly missed defects > `max_newly_missed_defects`;
  2. candidate `defect_recall` < `min_defect_recall`;
  3. false-hold reduction (current minus candidate) < `min_false_hold_reduction`;
  4. if `require_all_conditions`: rules 1 and 2 are also checked inside each condition.
- `activation = "BLOCK"` if any check fails, else `"ALLOW"` (approval is still required).
- `reasons[]` in plain language an operator understands, with counts and image ids, e.g. `"1 defect now passes: image <id> (condition shift_a)"`, `"candidate has 2 fewer false holds than current"`. When ALLOW, still give one reason line explaining why.

## A5: Approval, activation, rollback, export
- `gate/registry.py`: JSON file (default `gate/registry.json`, overridable via `registry_path`). Shape: `{"active_version": "v1_current", "previous_version": null, "history": [{"ts","action","version","reviewer","note","report_run_id"}]}`. Missing file means start from the initial state.
- `record_approval(report, reviewer, note)`: reviewer must be non-empty; sets `approved_by`, `approval_note`, `approved_at`; logs `approve` in history. Returns the updated report (do not mutate the input).
- `activate(report, registry_path=None)`: refuses with a clear error unless `activation == "ALLOW"`, `approved_by` is set, and `report["current_version"] == registry active_version` (stale report check). On success sets active to the candidate, stores the previous, logs `activate`.
- `rollback(registry_path=None)`: restores `previous_version`, logs `rollback`; clear error if there is nothing to roll back to.
- `reset_registry(...)` and `get_registry(...)` for the demo reset and the station screen.
- `export_bundle(report, out_dir, extra_files=None)` writes: `gate_report.json`, `changed_decisions.csv`, `policy_snapshot.yaml`, `hashes.json`, plus any `extra_files` (e.g. `review_decisions.json`). Returns `out_dir`.
- Hashes: real SHA-256 of the actual scores file, the policy file, and the UTF-8 bytes of each version id. Computed in `run_gate` and stored in `report["hashes"]`. Never placeholders.

## A6: Tests (`tests/gate_test_*.py`, pytest)
Must pass:
- loose candidate => `BLOCK`, and the reason names the missed defect image;
- reviewed candidate => `ALLOW`;
- a score exactly equal to the threshold is `PASS`;
- missing validation image => clear `ScoresError`;
- thresholds use calibration only (changing validation/test scores must not change them);
- `activate` before approval is refused; `activate` on a `BLOCK` report is refused;
- rollback restores the previous version; rollback with no history errors clearly;
- export hashes equal an independent recomputation;
- registry tests use a temp file, never the real `gate/registry.json`.

CHECK: `pytest tests/gate_* -q` all green. Then write `gate/README.md` documenting every public function in 1-3 lines.

## >>> STOP B: REAL-DATA SWAP <<<
Halt after Part B's mock-data screens work (B1 to B3 below), then ask the human to pull System 1's real `results/` (first the CPU sample, later the AMD run). Then:
1. Run the gate on the real scores. Do NOT edit gate logic to force a story.
2. Report in 8 lines: counts per version, thresholds, BLOCK/ALLOW per candidate, reasons, warnings, and the run id/device.
3. If the real data does not show "v2 misses a defect", say so plainly and ask the human what to do (any scenario change belongs to System 1).
4. Re-run tests. Add one test with a small real-scores fixture (a trimmed copy under `tests/fixtures/`, labelled real or sample).

---

# Part B: App (`app/`), Streamlit

Keep the app free of model/GPU code. Put all non-UI logic in `app/lib.py` (pure functions that are unit-testable); pages only call them.

## B1: Mode switch and data loading
- Env var `SHIFTGATE_MODE=mock|real` (default `mock`).
- Mock: uses `gate/FAKE_scores.csv` + `gate/FAKE_run_meta.json`; the gate report is produced by really running `gate.api.run_gate` on those fake scores (never hand-written). A permanent red **"SAMPLE DATA"** banner on every page. Mock outputs go to `app/.mock_out/` and the registry to `gate/registry_mock.json`.
- Real: loads `results/scores.csv` and `results/run_meta.json`; writes reports to `results/gate_report_<candidate>.json`; registry `gate/registry.json`. If a run id starts with `sample-`, show a "SAMPLE RUN" badge.
- Missing or invalid files show a helpful `st.error` message saying what is missing and which system produces it. No stack traces in the UI.

## B2: Screens (`app/main.py` is screen 1; the rest are `app/pages/2_...py` to `6_...py`)
1. **Station profile** (`main.py`): category, active version from `get_registry`, current false-hold count on the `shift_a` validation images, demo-reset button (calls `reset_registry`).
2. **Reference review**: thumbnails of `candidate_list.csv` rows (image + anomaly map if present). Approve/reject per image. Save to `results/review_decisions.json` (or the mock folder). After saving, compare to `in_v3_bank` and show a plain note if the engineer's choices differ from the set v3 was built from. If an image file is missing, show a labelled placeholder.
3. **Compare versions**: sidebar selector for the candidate (`v2_candidate_loose` or `v3_candidate_reviewed`). Side-by-side metrics with **counts** (n_good, n_defect, false holds, defects caught) next to rates.
4. **Changed decisions** (hero screen): table plus image viewer. `newly_missed_defect` rows are visually prominent (red). Click a row to see the image and its anomaly map.
5. **Decision**: big `ALLOW`/`BLOCK` badge with the plain-language `reasons`. Approve/activate works only on `ALLOW` (reviewer name + note required, then `record_approval` then `activate`). Rollback button is always available.
6. **Export**: build the bundle with `export_bundle` (include `review_decisions.json`), zip it with `zipfile`, offer `st.download_button`.
- **Run info footer on every page** (`lib.render_run_info()`): device label, GPU name, HIP/ROCm version, torch version, timings from `run_meta.json`. If `device == cpu` show "Not an AMD GPU run." If `other_gpu` show "Not an AMD GPU." In mock mode show "SAMPLE DATA: not a real run." Never fake this panel.
- Design: big status badges, minimal text, readable at demo-video resolution (1080p).

## B3: Demo support
- `docs/DEMO_FLOW.md`: a 3-minute click path: load batch, see good parts held, candidate A looks better, changed decisions reveal a missed defect, BLOCK, candidate B passes, approve, export. Describe ONLY what the app really shows in the mode you tested.
- Tests (`tests/app_test_lib.py`): the pure functions in `app/lib.py` (loading, mode switch, run-info text for cpu / rocm / other_gpu / mock, missing-file messages).

CHECK: `pytest tests/app_* -q` passes, and `SHIFTGATE_MODE=mock streamlit run app/main.py` starts without errors (say in your summary that you could not visually check the UI if you could not).

Now go to **STOP B** (above), then continue.

## >>> STOP C: HOSTING + AMD VISIBILITY DECISION <<<
Halt and ask the human. Do not decide alone. The rules say the AMD component must be part of the working product shown to judges, and the submission needs an application URL. Present these options with pros and cons:
1. Host the whole app on the AMD Developer Cloud instance (the AMD part is truly live) if the instance can expose a public port.
2. Host the app elsewhere reading precomputed AMD results, plus a short recorded live GPU run in the demo video.
3. App has a "Re-score on AMD GPU" button that calls the GPU machine, if reachable.
Tell the human to confirm which option is acceptable with the organizers on the lablab Discord. Do not assume.

---

# Part C: Submission package (`submission/`) and README

Draft only from facts in this repo. Anything unfinished is marked `TODO(human)`. Use only real numbers from `results/` files; copy them with their run id.

- `project_info.md`: all lablab form fields in one file: project title; short description (max 2 sentences); long description; selected challenge (Track 1 Intelligent Industry); technology tags (only those actually used, e.g. AMD ROCm, AMD Developer Cloud, PyTorch, PatchCore, Streamlit); cover image file; demo video link; slide presentation link; public GitHub repo URL; demo application platform; application URL. Unknown items are `TODO(human)`.
- `pitch_outline.md` (slide outline): problem, user, demo, how AMD is used, measurable result (real numbers only), limits and honesty note (scripted scenario, small validation set, synthetic shift if used), who benefits and the value hypothesis (less engineering/review effort; state it as a hypothesis to validate, never a proven saving).
- `video_script.md`: about 2-3 minutes, scene by scene, with on-screen captions; matches `docs/DEMO_FLOW.md`.
- `cover_image_brief.md`: layout, text, colours.
- `repo_checklist.md`: public GitHub repo, README with run steps, requirements, dataset licence note (CC BY 4.0, with attribution), no secrets, no raw data committed.
- `README.md`: problem, who it is for, how it works, architecture sketch, setup and run commands (CPU sample and AMD GPU), results from real runs (with run ids), limitations, credits and dataset licences.

## Done when
App runs in mock and real mode; the hero screen demonstrably shows a blocked candidate (on real data if the real data supports it, otherwise say so); the run-info panel is truthful; `pytest` is green; all submission files are drafted for the human to finalize.
