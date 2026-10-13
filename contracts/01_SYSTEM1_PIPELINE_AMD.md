# System 1: Detection pipeline + AMD GPU run (critical path)

Read `00_SHARED_CONTRACT.md` first and follow its working rules. You own `pipeline/`, `config.yaml`, `data/sample/`, `tests/pipeline_*`, and the real-run files in `results/`.

## Goal
Produce `results/splits.csv`, `results/scores.csv`, `results/run_meta.json`, `results/candidate_list.csv` per the contract, using a minimal PatchCore-style anomaly detector. Everything must run on CPU on a small sample first, then on the AMD GPU.

## Design decisions (already made, do not change)
- Pure PyTorch + torchvision. Do NOT depend on Anomalib.
- Backbone: torchvision `wide_resnet50_2` pretrained, `eval()`, `torch.no_grad()`.
- No fp16/bf16 tricks. No algorithm changes to chase speed.
- Banks are built per version from **per-image subsampled patches** (so v2 = v3 + the contaminant, exactly).

---

## Stage 0: Setup and dataset check (human helps)

1. Create the folder layout from the contract and an empty `requirements.txt` with a `# System 1` section.
2. Create `pipeline/amd_smoke_test.py` using the exact code in `03_AMD_SETUP_AND_SMOKE_TEST.md` (section "Smoke test script"). Do not run it on AMD; just make sure it runs on CPU.
3. **Ask the human these three things in ONE message, then wait:**
   - Where is the dataset folder? Which category/categories (PCB)? Candidates: Hugging Face `AmazonScience/RobustAD` (PCB subset, CC BY 4.0, docs are incomplete so inspect real files) or VisA PCB (CC BY 4.0) as fallback.
   - May `torchvision` download the pretrained `wide_resnet50_2` weights (about 130 MB, one time)?
   - Is a ~20-40 image sample allowed to be committed to `data/sample/`?
4. Inspect the real folder yourself (list files, count images). Write `pipeline/DATASET_NOTES.md`: folder structure found, categories, counts of good and defect, defect types if present, whether shift conditions exist, licence, and **what you could NOT verify**.

CHECK: `pipeline/DATASET_NOTES.md` exists and every count in it came from code you ran (put the command you used in the file).

## Stage 1: Skeleton

- `config.yaml` with exactly these keys (edit values after Stage 0):
```yaml
seed: 42
category: TODO_set_after_stage0
data_root: data/sample
results_dir: results
mode: sample              # sample | full  (goes into run_id and run_meta notes)
device: auto              # auto | cpu | cuda
image_size: 256
crop_size: 224
batch_size: 8
coreset_ratio: 0.1        # fraction of patches kept per bank image
contaminant_keep_ratio: 1.0
n_contaminant: 1
save_maps: true           # validation split only
shift:
  type: auto              # auto = native if dataset has it, else synthetic
  brightness: 0.7
  contrast: 0.9
  wb_red: 1.08
  wb_blue: 0.92
fractions:                # of the GOOD images in each condition
  baseline: {reference_v1: 0.4, calibration: 0.2, validation: 0.2, test: 0.2}
  shift_a:  {candidate_pool: 0.4, calibration: 0.2, validation: 0.2, test: 0.2}
defect_fractions: {validation: 0.5, test: 0.5}   # after removing the contaminant
```
- `pipeline/device.py`:
  - `get_device_info(config_device="auto") -> dict` returning `{"torch_device": str, "label": "cpu"|"rocm"|"other_gpu", "gpu_name": str|None, "hip_version": str|None, "torch_version": str}`.
  - Logic: env var `SHIFTGATE_DEVICE` overrides config. `auto` picks the GPU if `torch.cuda.is_available()` (true on ROCm builds too), else CPU. Label is `rocm` only if `torch.version.hip` is not None; a GPU without HIP is `other_gpu` and must print a visible warning "NOT an AMD GPU". If the user asked for `cuda` but no GPU exists, raise a clear error (no silent fallback).
- `pipeline/dataset.py`: `list_images(cfg) -> DataFrame[image_id, path, category, true_label, condition, defect_type]`. Implement it from what Stage 0 found. If the dataset has no native condition, set `condition` to `baseline` for all and let `shifts.py` assign.
- `pipeline/shifts.py`: `assign_conditions(df, cfg)` (seeded 50/50 split of GOOD and DEFECT images into `baseline`/`shift_a` when synthetic) and `apply_shift(pil_image, cfg)` (brightness x`brightness`, contrast x`contrast`, red channel x`wb_red`, blue channel x`wb_blue`). Documented, deterministic. Applied at load time only for `shift_a` images when `shift_type == synthetic`. Never save shifted copies over originals.
- `pipeline/splits.py`: `make_splits(df, cfg) -> DataFrame` following the contract split table and the fractions above. Steps: pick `n_contaminant` defect images first (same `defect_type` as a defect that will be in validation when types exist); split remaining defects by `defect_fractions` with both conditions represented; split good images per condition by `fractions`. Use one seeded `numpy` RNG. Raise a clear error if any split/condition cell would be empty. Write `results/splits.csv`.
- Tests (`tests/pipeline_test_splits.py`): no `image_id` in two splits; same seed gives identical output; `calibration` has only `good`; `reference_v1` is only `baseline`; `candidate_pool` is only `shift_a`; `contaminant` is only `defect`.

CHECK: `pytest tests/pipeline_test_splits.py -q` passes, and `python -m pipeline.splits --config config.yaml` prints counts per split x condition x label.

## Stage 2: Detector (CPU, sample of 20-40 images)

- `pipeline/features.py`
  - `load_image_tensor(path, cfg, condition) -> Tensor[3,crop,crop]`: open RGB, apply synthetic shift if needed, resize to `image_size`, center-crop to `crop_size`, ImageNet normalize.
  - `class FeatureExtractor`: wraps `wide_resnet50_2`, returns `layer2` (512 ch) and `layer3` (1024 ch). For each: `avg_pool2d(kernel=3, stride=1, padding=1)`; upsample `layer3` to the `layer2` spatial size (bilinear); concatenate to 1536 channels. `extract(batch[B,3,H,W]) -> Tensor[B, P, 1536]` where P = h*w (28*28 = 784 at crop 224).
  - `subsample_patches(feats[P,D], image_id, seed, ratio) -> Tensor[k,D]`: deterministic per image. Use `torch.Generator` seeded with `seed + zlib.crc32(image_id.encode())`. `ratio=1.0` keeps all.
- `pipeline/patchcore.py`
  - `class PatchBank`: holds a `[N,D]` tensor on the device. `PatchBank.build(list_of_[k,D]) -> PatchBank`.
  - `PatchBank.score(feats[B,P,D]) -> (image_scores[B], patch_dists[B,P])`: for each image compute distance from every patch to its nearest bank patch using **chunked** `torch.cdist` (chunk over bank rows and query rows so memory stays bounded; chunk size from a constant at the top of the file). Image score = max patch distance.
  - `class Detector` wrapper: `fit(images_iterable)` / `score(images)` (interface so Anomalib could be swapped in later).
- `pipeline/score.py`: `score_images(df, banks: dict[str,PatchBank], extractor, cfg, timers) -> DataFrame` streaming in batches: extract features once per batch, score against every bank, discard features. Optionally save maps (below).
- Anomaly maps (only if `save_maps` and split is `validation`): reshape `patch_dists[b]` to `[h,w]`, upsample to `crop_size`, min-max normalize per map, colorize (matplotlib `jet`), blend 50% over the image, save to `results/maps/<version>/<image_id>.png`, put the relative path in `map_path`.
- Timing: `pipeline/timing.py` with a context manager that calls `torch.cuda.synchronize()` before and after when on a GPU (this works on ROCm too). Phases: `features`, `bank`, `scoring`. Store seconds, rounded to 3 decimals.
- Tests (`tests/pipeline_test_detector.py`, CPU, tiny random tensors, no downloads: use `weights=None` via a test flag): bank built from near-identical tensors scores an identical tensor lower than a noise-corrupted one; `subsample_patches` is deterministic and keeps `ratio` of the patches; chunked `cdist` equals a plain full `cdist` on a small example.

CHECK: `pytest tests/pipeline_test_detector.py -q` passes.

## Stage 3: Versions + full output

- `pipeline/versions.py`: `build_banks(splits_df, extractor, cfg, timers) -> (dict, candidate_list_df)`.
  - `v1_current` = patches of `reference_v1` images at `coreset_ratio`.
  - `v3_candidate_reviewed` = v1 patches + `candidate_pool` patches at `coreset_ratio`.
  - `v2_candidate_loose` = v3 patches + `contaminant` patches at `contaminant_keep_ratio`.
  - The contamination must be obvious in the code (a clearly named function `add_scripted_contaminant`) and documented in `pipeline/SCENARIO.md`: what it is, why we do it, and that it is a **scripted** careless update.
  - Compute each image's subsampled patches ONCE and reuse for the banks that include it.
  - `candidate_list_df` columns: `image_id, path, condition, is_contaminant, in_v3_bank`; write it to `results/candidate_list.csv` (candidate_pool rows + contaminant rows, shuffled with the seed).
- `pipeline/run_pipeline.py --config config.yaml --device auto|cpu|cuda`:
  1. read config and device info, 2. build/load splits, 3. build banks, 4. score `calibration`, `validation`, `test` for all three versions, 5. write `scores.csv` (contract columns, `device` = the label), 6. write `run_meta.json` (all contract fields; `notes` includes the mode and anything unusual), 7. validate both files against the contract and fail loudly if columns or values are wrong.
  - `run_id` = `<mode>-<label>-<YYYYmmddTHHMMSS>`.
- Print a short real summary at the end: number of images per split, timings, and per-version mean score on calibration normals. Do NOT compute or print any "false hold" or "recall" claims here; that is the gate's job.

CHECK: on the CPU sample, `python -m pipeline.run_pipeline --config config.yaml --device cpu` finishes and `results/` has all files; a validation function confirms the contract.

## Stage 4: Hand-off prep

- `pipeline/README.md`: exact commands (install, CPU sample, AMD GPU).
- Run the sample on CPU. Commit `results/` from this sample run ONLY if `mode: sample` is in the run id and notes. Never commit `data/raw/`.
- Tell the human: the commit/branch System 2 should pull, and the CPU timings.

## >>> STOP A: AMD INTEGRATION POINT <<<
Halt. Report in 8 lines max: what runs on CPU, sample timings, and any code that might assume NVIDIA (search for `.cuda`, `cuda` literals, `nvidia`). The human now follows `03_AMD_SETUP_AND_SMOKE_TEST.md` on the AMD instance and tells you to continue.

## Stage 5 (ONLY after the human says AMD is ready)

1. Paste the smoke-test output the human gives you into `pipeline/AMD_NOTES.md` (verbatim, with date).
2. Run the sample with `--device cuda`. Compare to the CPU sample scores: write the max absolute difference and rank agreement per version in `AMD_NOTES.md`. Small float differences are normal; large ones are a bug to report.
3. Tune only `batch_size` for the GPU. Do not change the algorithm.
4. Run the full chosen category (`mode: full`). `run_meta.json` must show the real `device` label, `gpu_name`, `hip_version`.
5. Write `results/benchmark.json` from real runs only: `{"runs":[{"run_id","device","gpu_name","n_images","batch_size","timings_sec"}], "notes": ""}`. Run the SAME images on CPU and GPU so the comparison is fair, and say which CPU was used.
6. If anything fails on ROCm: save the exact error in `AMD_NOTES.md`, try the smallest fix (version/env var/batch size), then stop and report. Never silently fall back to CPU and call it AMD.

## Done when
`scores.csv` from a real AMD GPU run exists, `run_meta.json` shows the ROCm device, tests pass, and `pipeline/README.md` commands reproduce it. Tell the human which commit System 2 should pull.
