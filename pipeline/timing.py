"""Timing utilities with hardware synchronization for pipeline phases."""
import time
from typing import Dict
import torch

from pipeline.device import sync_device


class PhaseTimer:
    """Context manager for accurate wall-clock phase measurement with device sync."""

    def __init__(self, phase: str, timings: Dict[str, float], device: torch.device) -> None:
        """Initialize timer for a specific pipeline phase."""
        self.phase = phase
        self.timings = timings
        self.device = device
        self.start_time = 0.0

    def __enter__(self) -> "PhaseTimer":
        """Synchronize hardware and record start timestamp."""
        sync_device(self.device)
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Synchronize hardware, record duration, and accumulate timing."""
        sync_device(self.device)
        duration = time.perf_counter() - self.start_time
        current = self.timings.get(self.phase, 0.0)
        self.timings[self.phase] = round(current + duration, 3)
