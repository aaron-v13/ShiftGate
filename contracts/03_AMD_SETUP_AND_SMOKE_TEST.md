# AMD setup and smoke test (for the human, with System 1's agent)

This replaces the missing `04_AMD_INTEGRATION_STOP_POINTS.md`. I could not verify the current AMD Developer Cloud screens or instance images, so follow the instance's own instructions for login and starting it, and use this file for what to check.

## Do this on day one, in parallel with writing code
1. Sign up for the **AMD AI Developer Program** (required for approval) and enroll on lablab.ai and the lablab Discord.
2. Start an AMD Developer Cloud GPU instance and log in (SSH or its notebook/terminal).
3. Clone the repo on the instance (public GitHub, or a private one with your own login; never paste tokens into the agent).
4. Run the smoke test (below). Paste its full output to the System 1 agent so it goes into `pipeline/AMD_NOTES.md`.
5. Confirm the dataset is reachable (download it on the instance, or copy a sample). Ask the agent not to commit `data/raw/`.
6. Ask the organizers on Discord: can the app be hosted from the instance or must it be hosted elsewhere, and does the demo need to show a live GPU run? (This feeds STOP C.)

## Quick manual checks on the instance
```bash
rocm-smi                      # should list the GPU(s)
rocminfo | head -n 30         # should show a gfx... agent
python -c "import torch; print(torch.__version__, torch.version.hip, torch.cuda.is_available())"
pip list | grep -i torch      # a ROCm build usually has a +rocm suffix in the version
```
- `torch.version.hip` should be a version string (not `None`) and `torch.cuda.is_available()` should be `True`.
- If `is_available()` is `False`: you are probably in a CPU-only Python environment. Use the instance's ROCm PyTorch environment/container or the install command from the AMD/PyTorch ROCm docs for that instance. Do not "fix" it by editing our code.

## Smoke test script
`System 1` creates this file as `pipeline/amd_smoke_test.py` in Stage 0. It is allowed to use the device words directly (it is the one exception, together with `pipeline/device.py`).

```python
"""ShiftGate smoke test: is PyTorch really using an AMD (ROCm) GPU?

Runs anywhere. On a CPU-only machine it reports that clearly and exits with 2.
Exit codes: 0 = AMD ROCm GPU works, 1 = GPU problem, 2 = CPU only / not AMD.
"""
import sys
import time

import torch
import torchvision


def sync(dev) -> None:
    if dev.type != "cpu":
        torch.cuda.synchronize()


def main() -> int:
    hip = getattr(torch.version, "hip", None)
    has_gpu = torch.cuda.is_available()
    print(f"torch={torch.__version__} torchvision={torchvision.__version__}")
    print(f"torch.version.hip={hip}")
    print(f"gpu_available={has_gpu}")
    if not has_gpu:
        print("RESULT: CPU only. This is NOT an AMD GPU run.")
        return 2
    dev = torch.device("cuda")
    print(f"gpu_name={torch.cuda.get_device_name(0)}")
    if hip is None:
        print("RESULT: a GPU is present but this is NOT a ROCm/HIP build. Not an AMD GPU run.")
        return 2
    try:
        a = torch.randn(2048, 2048, device=dev)
        b = torch.randn(2048, 2048, device=dev)
        sync(dev)
        t0 = time.perf_counter()
        for _ in range(10):
            c = a @ b
        sync(dev)
        print(f"matmul_ok shape={tuple(c.shape)} time_10x={time.perf_counter() - t0:.4f}s")

        model = torchvision.models.wide_resnet50_2(weights=None).to(dev).eval()
        x = torch.randn(4, 3, 224, 224, device=dev)
        with torch.no_grad():
            model(x)  # warm-up
            sync(dev)
            t0 = time.perf_counter()
            y = model(x)
            sync(dev)
        print(f"wide_resnet50_2_forward_ok out={tuple(y.shape)} time={time.perf_counter() - t0:.4f}s")

        d = torch.cdist(torch.randn(512, 64, device=dev), torch.randn(4096, 64, device=dev))
        sync(dev)
        print(f"cdist_ok shape={tuple(d.shape)}")
    except Exception as exc:  # report the exact error, do not hide it
        print(f"RESULT: GPU test FAILED: {type(exc).__name__}: {exc}")
        return 1
    print("RESULT: AMD ROCm GPU smoke test PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
Run: `python -m pipeline.amd_smoke_test` (it uses `weights=None`, so no download is needed).

## Running the pipeline on the instance (after STOP A)
```bash
git clone <your repo> && cd shiftgate && git checkout system1-pipeline
# put the dataset path in config.yaml (data_root) or symlink data/raw
python -m pipeline.run_pipeline --config config.yaml --device cuda   # "cuda" is PyTorch's name for ROCm GPUs too
```
The run is only called an AMD run if `results/run_meta.json` shows `device: rocm` with a `hip_version`.

## Showing the app from the instance (only after STOP C)
```bash
SHIFTGATE_MODE=real streamlit run app/main.py --server.address 0.0.0.0 --server.port 8501
# from your laptop, a private tunnel works even if the port is not public:
ssh -L 8501:localhost:8501 <user>@<instance-host>   # then open http://localhost:8501
```
Whether the instance can expose a public port is unknown. That is the STOP C question for the organizers.
