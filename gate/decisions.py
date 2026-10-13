"""Per-image decision logic given anomaly scores and a threshold."""

from typing import Union
import numpy as np
import pandas as pd


def decide(
    scores: Union[float, int, pd.Series, np.ndarray, list[float]],
    threshold: float,
) -> Union[str, pd.Series, list[str]]:
    """Determine decision: HOLD if anomaly score is strictly greater than threshold, else PASS."""
    if isinstance(scores, (int, float, np.floating, np.integer)):
        return "HOLD" if float(scores) > threshold else "PASS"

    if isinstance(scores, pd.Series):
        return scores.apply(lambda s: "HOLD" if float(s) > threshold else "PASS")

    if isinstance(scores, np.ndarray):
        return np.where(scores > threshold, "HOLD", "PASS")

    # List or general iterable
    return ["HOLD" if float(s) > threshold else "PASS" for s in scores]
