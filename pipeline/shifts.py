"""Synthetic distribution shift transformations and condition assignment."""
from typing import Any, Dict
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance


def assign_conditions(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Assign baseline or shift_a conditions deterministically to images."""
    shift_cfg = cfg.get("shift", {})
    shift_type = shift_cfg.get("type", "auto")

    # If conditions are already partitioned and not synthetic requested, preserve
    unique_conds = set(df["condition"].unique())
    if shift_type == "auto" and len(unique_conds) > 1 and "baseline" in unique_conds and "shift_a" in unique_conds:
        return df.copy()

    # Synthetic shift: deterministic 50/50 split within each label
    rng = np.random.default_rng(cfg.get("seed", 42))
    df_out = df.copy()

    conditions = df_out["condition"].values.copy()

    for label in ["good", "defect"]:
        indices = df_out[df_out["true_label"] == label].index.to_numpy()
        # Sort indices by image_id for absolute determinism across platforms
        sorted_indices = sorted(indices, key=lambda idx: df_out.loc[idx, "image_id"])
        perm = rng.permutation(len(sorted_indices))
        permuted_indices = [sorted_indices[i] for i in perm]

        half = len(permuted_indices) // 2
        for idx in permuted_indices[:half]:
            conditions[df_out.index.get_loc(idx)] = "baseline"
        for idx in permuted_indices[half:]:
            conditions[df_out.index.get_loc(idx)] = "shift_a"

    df_out["condition"] = conditions
    return df_out


def apply_shift(pil_image: Image.Image, cfg: Dict[str, Any]) -> Image.Image:
    """Apply deterministic brightness, contrast, and white balance shift."""
    shift_cfg = cfg.get("shift", {})
    brightness = shift_cfg.get("brightness", 0.7)
    contrast = shift_cfg.get("contrast", 0.9)
    wb_red = shift_cfg.get("wb_red", 1.08)
    wb_blue = shift_cfg.get("wb_blue", 0.92)

    img = pil_image.convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)

    r, g, b = img.split()
    r = r.point(lambda i: min(255, max(0, int(round(i * wb_red)))))
    b = b.point(lambda i: min(255, max(0, int(round(i * wb_blue)))))
    return Image.merge("RGB", (r, g, b))
