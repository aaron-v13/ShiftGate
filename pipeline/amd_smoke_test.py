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
