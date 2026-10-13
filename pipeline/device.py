"""Device selection and metadata inspection for AMD ROCm and CPU execution."""
import os
from typing import Any, Dict
import torch


def get_device_info(config_device: str = "auto") -> Dict[str, Any]:
    """Resolve compute device and query ROCm/GPU hardware metadata."""
    req_device = os.environ.get("SHIFTGATE_DEVICE", config_device).strip().lower()
    hip_version = getattr(torch.version, "hip", None)
    torch_version = torch.__version__
    has_gpu = torch.cuda.is_available()

    if req_device == "cuda":
        if not has_gpu:
            raise RuntimeError("Device 'cuda' requested, but no GPU is available.")
        target_torch_device = "cuda"
    elif req_device == "cpu":
        target_torch_device = "cpu"
    elif req_device == "auto":
        target_torch_device = "cuda" if has_gpu else "cpu"
    else:
        raise ValueError(f"Unknown device specification: {req_device}")

    if target_torch_device == "cpu":
        return {
            "torch_device": "cpu",
            "label": "cpu",
            "gpu_name": None,
            "hip_version": None,
            "torch_version": torch_version,
        }

    # GPU execution branch
    gpu_name = torch.cuda.get_device_name(0) if has_gpu else None
    if hip_version is not None:
        label = "rocm"
    else:
        label = "other_gpu"
        print("WARNING: NOT an AMD GPU! Detected non-ROCm GPU environment.")

    return {
        "torch_device": "cuda",
        "label": label,
        "gpu_name": gpu_name,
        "hip_version": hip_version,
        "torch_version": torch_version,
    }


def sync_device(device: torch.device) -> None:
    """Synchronize compute device stream if running on GPU hardware."""
    if device.type != "cpu" and torch.cuda.is_available():
        torch.cuda.synchronize()
