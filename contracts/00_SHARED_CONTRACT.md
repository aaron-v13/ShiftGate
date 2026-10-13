# ShiftGate: Shared Contract (both systems read this first)

**One-liner:** ShiftGate lets a quality engineer test an inspection update (new reference examples for a PCB visual-inspection station) *before* activating it. It blocks updates that clear more good boards but newly miss a known defect.

**Hackathon:** AMD Developer Hackathon ACT III (lablab.ai), Track 1 Intelligent Industry. A meaningful part of the working demo MUST run on an AMD GPU (ROCm). Judges score: Application of Technology, Presentation, Business Value, Originality.

---

## 1. How to work (rules for the coding agent)

1. Read this file and your own brief completely before writing any code.
2. Work in the stages given. After each stage: run that stage's **CHECK** command, then print a summary of at most 5 lines: done / check result / files created / assumptions / next stage.
3. At every **STOP** marker, halt and wait for the human. Never continue past a STOP on your own.
4. Do not ask the human questions outside STOP markers. If something is unclear, pick the simplest option, write the assumption as one line in `NOTES.md` (inside your own folder), and continue.
5. If a command or test fails: read the error, make the smallest fix, retry. After 3 failed tries on the same problem, stop and report the exact error text.
6. Edit ONLY your own folders (section 3). If you need a change elsewhere, stop and tell the human.
7. Python 3.10+. Type hints and a one-line docstring per function. Small functions, plain code, no clever abstractions, no new frameworks.
8. Small commits with clear messages. Never force-push. Never commit data, model weights, or secrets. Never ask for API keys.
9. The words `cuda` / `cpu` as hard-coded device literals are allowed ONLY in `pipeline/device.py` and `pipeline/amd_smoke_test.py`. No `.cuda()` calls. No NVIDIA-only packages.
10. After installing a package, add it with its installed version to `requirements.txt` (your own section). Exception: `torch` and `torchvision` are NOT pinned in `requirements.txt` (the AMD build differs from the CPU build); describe them in the README instead.

## 2. Honesty rules (every agent, every file)

- NEVER invent results, metrics, dataset facts, or benchmark numbers. Every number shown anywhere must come from a file produced by a real run.
- Anything fake or mock must have `FAKE` in the filename and be shown as "SAMPLE DATA" in the UI.
- The "bad update" scenario is **scripted by us** (a deliberately careless update). Say so in docs. Never present it as a natural discovery.
- Do not claim novelty in anomaly detection (PatchCore is existing work). Our contribution is the **update-gating workflow**: compare versions, expose newly missed defects, approval, rollback, audit export.
- Validation sets are small. Always show **counts next to rates**. Describe results as evidence for a workflow, not as production accuracy.
- If real results do not show the intended story, report what actually happened. Never edit logic or data to force the story.
- Do not download datasets or model weights silently. Ask the human first (at the STOP/Stage 0 point that says so).

## 3. The two systems and who owns what

| | System 1: AMD side | System 2: Decision side |
|---|---|---|
| Builds | detector, splits, versions, scoring, the AMD GPU run | gate logic, review app, hosting, submission |
| Owns folders | `pipeline/`, `config.yaml`, `data/sample/`, `results/` (except files System 2 writes, see below) | `gate/`, `app/`, `docs/`, `submission/`, `tests/gate_*`, `tests/app_*`, `README.md` |
| Brief | `01_SYSTEM1_PIPELINE_AMD.md` | `02_SYSTEM2_GATE_APP_SUBMISSION.md` |

System 2 may write ONLY these files inside `results/`: `gate_report_*.json`, `review_decisions.json`, `exports/`.
System 1 tests live in `tests/pipeline_*`.

**The only handoff** is `results/scores.csv` + `results/run_meta.json` (+ `results/splits.csv`, `results/candidate_list.csv`, `results/maps/`). System 2 starts on `FAKE` data and swaps to real files at its STOP B.

## 4. Repo layout

```
shiftgate/
  README.md            (System 2)
  requirements.txt     (each system appends its own section)
  config.yaml          (System 1)
  contracts/           (shared; changes need human approval)  <- copy these 5 .md files here
  data/raw/            (NOT committed; human downloads)
  data/sample/         (tiny sample, ~20-40 images, only if the licence allows)
  results/             (real run outputs only; never FAKE files)
  pipeline/            (System 1)
  gate/                (System 2)
  app/  docs/  submission/   (System 2)
  tests/               (pytest; prefixes above)
```
Git: `main` + branch `system1-pipeline` + branch `system2-gate-app`. Merge to `main` only when the human says so.

## 5. Data conventions

- `image_id`: unique, stable string = dataset-relative file path without extension, with `/` replaced by `__`. Same image = same id in every file.
- `path`: path as the pipeline opened it, relative to the repo root when the file is inside the repo, otherwise absolute. The app must handle "file not found on this machine" gracefully.
- Conditions: `baseline` or `shift_a`. If the dataset has no native shift, System 1 applies a documented synthetic shift (brightness/contrast/white-balance) to a seeded half of images and records `shift_type: synthetic` in `run_meta.json`. Never present synthetic shift as a natural factory change.
- Seed lives in `config.yaml`. Every random choice uses it.

## 6. Data splits (System 1 writes `results/splits.csv`; deterministic; no image in two splits)

| split | contents | use |
|---|---|---|
| `reference_v1` | normal, `baseline` only | source of the current reference bank |
| `candidate_pool` | normal, `shift_a` only | new reference examples offered for approval |
| `contaminant` | 1-2 **defect** images (same defect type as at least one validation defect when the dataset has defect types) | the scripted "careless" addition, used ONLY in v2 |
| `calibration` | normal only, both conditions | per-version thresholds (and nothing else) |
| `validation` | good + defect, both conditions | the gate's regression suite |
| `test` | good + defect, both conditions | untouched until the final report |

`splits.csv` columns: `image_id, path, category, condition, split, true_label, defect_type` (`defect_type` may be empty).

## 7. Versions (System 1 builds, System 2 compares)

- `v1_current`: bank from `reference_v1` images.
- `v3_candidate_reviewed`: v1 bank + all `candidate_pool` images (the reviewer rejected the contaminant).
- `v2_candidate_loose`: v3 bank + the unreviewed `contaminant` image(s) (the careless engineer approved everything).
- Intended story: v2 and v3 both cut false holds on `shift_a`; v2 misses a defect because of the contaminant; v3 keeps catching defects. This is a hypothesis to test, not a guarantee. Report real results.

## 8. Files in `results/`

`scores.csv` columns (System 1 writes; System 2 reads):
`run_id, image_id, path, category, condition, split, true_label, model_version, anomaly_score, map_path, device`
- One row per (image x version) for splits `calibration`, `validation`, `test`. Other splits appear only in `splits.csv`.
- `true_label`: `good` | `defect`. `map_path` may be empty.
- `device`: `cpu` | `rocm` | `other_gpu`. Use `rocm` ONLY when `torch.version.hip` is set. A CUDA GPU without HIP is `other_gpu` (never claim it as AMD).
- `run_id` format: `<sample|full>-<device>-<YYYYmmddTHHMMSS>`. FAKE data uses `FAKE-...` run ids and `fake_` image ids.

`run_meta.json`:
```json
{"run_id": "", "device": "cpu|rocm|other_gpu", "gpu_name": null, "torch_version": "", "hip_version": null,
 "seed": 0, "n_images": 0, "batch_size": 0, "image_size": 0,
 "timings_sec": {"features": 0.0, "bank": 0.0, "scoring": 0.0},
 "dataset": {"name": "", "category": "", "licence": "", "shift_type": "native|synthetic"}, "notes": ""}
```
Other files: `splits.csv`, `candidate_list.csv` (`image_id, path, condition, is_contaminant, in_v3_bank`), `benchmark.json` (real runs only), `maps/<version>/<image_id>.png` (optional).

## 9. Gate API (System 2 implements and uses). Import `gate.api`

```python
run_gate(scores_path, policy_path, current, candidate) -> dict          # gate_report
record_approval(report, reviewer, note) -> dict
activate(report, registry_path=None) -> dict      # only if report["activation"]=="ALLOW" and approved
rollback(registry_path=None) -> dict
export_bundle(report, out_dir, extra_files=None) -> str   # writes files, returns out_dir
get_registry(registry_path=None) -> dict
reset_registry(registry_path=None) -> dict        # demo reset: active = v1_current, empty history
```
`gate_report` keys: `run_id, current_version, candidate_version, policy, thresholds{current,candidate}, metrics{current,candidate:{n_good,n_defect,false_holds,defects_caught,false_hold_rate,defect_recall,per_condition{<cond>:{same fields}}}}, changed_decisions[{image_id,condition,true_label,current_decision,candidate_decision,change_type}], activation ("ALLOW"|"BLOCK"), reasons[], warnings[], hashes{}, approved_by, approval_note, device`

Rules:
- decision = `HOLD` if `anomaly_score > threshold` else `PASS` (a tie is `PASS`).
- threshold per version = percentile (`policy.yaml: threshold_percentile`, default 99) of that version's `calibration` normal scores. Nothing else is used for thresholds.
- metrics use the `validation` split only. `false_holds` = good images decided HOLD. `defects_caught` = defect images decided HOLD.
- `change_type`: defect HOLD->PASS = `newly_missed_defect`; defect PASS->HOLD = `newly_caught_defect`; good HOLD->PASS = `good_released`; good PASS->HOLD = `good_newly_held`. Unchanged images are not listed.
- Sort order of `changed_decisions`: `newly_missed_defect`, `good_newly_held`, `newly_caught_defect`, `good_released`.
- ANY `newly_missed_defect` => `BLOCK` (default policy).

`gate/policy.yaml` default:
```yaml
threshold_percentile: 99
max_newly_missed_defects: 0
min_defect_recall: 0.8
min_false_hold_reduction: 1     # candidate must have at least this many fewer false holds
require_all_conditions: true    # recall and missed-defect rules are also checked per condition
```
These are our policy knobs, not industry standards. Say so in docs.
