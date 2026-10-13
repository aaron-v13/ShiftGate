# ShiftGate System 1: Detection Pipeline & AMD Execution

This package implements the PatchCore-style anomaly detection pipeline, condition splitting, reference memory bank construction with scripted contamination, scoring, and hardware acceleration on AMD ROCm (HIP).

## 1. Installation

### CPU Environment (Development & Smoke Testing)
```bash
# PyTorch and torchvision CPU build (Python 3.10+)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install pipeline dependencies
pip install -r requirements.txt
```

### AMD ROCm Environment (GPU Execution)
Follow the official AMD ROCm PyTorch installation on the AMD Developer Cloud instance:
```bash
# Example for ROCm 6.0+ (adjust according to instance driver)
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
pip install -r requirements.txt
```

## 2. Hardware Smoke Test
Verify ROCm hardware support and HIP detection:
```bash
python -m pipeline.amd_smoke_test
```
- Exit code 0: AMD ROCm GPU verified and functional.
- Exit code 2: CPU only or non-AMD environment.

## 3. Run CPU Sample
Run the complete pipeline end-to-end on the local CPU sample:
```bash
python -m pipeline.run_pipeline --config config.yaml --device cpu
```
This produces:
- `results/splits.csv`: Dataset split assignments.
- `results/candidate_list.csv`: Candidate images with unreviewed contaminant flags.
- `results/scores.csv`: Per-image anomaly scores for v1, v2, and v3.
- `results/run_meta.json`: Hardware, timings, and configuration metadata.
- `results/maps/`: Blended anomaly heatmaps for validation images.

## 4. Run on AMD ROCm GPU
To run on the AMD GPU instance:
```bash
python -m pipeline.run_pipeline --config config.yaml --device cuda
```
Note: In PyTorch ROCm builds, `--device cuda` maps directly to the AMD GPU via the HIP compatibility layer. `pipeline/device.py` automatically validates `torch.version.hip`.

## 5. Tests
Run pytest across split logic and detector components:
```bash
pytest -q
```
