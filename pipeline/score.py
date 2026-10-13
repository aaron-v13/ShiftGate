"""Image scoring loop across model versions and anomaly heatmap rendering."""
import math
from pathlib import Path
from typing import Any, Dict, List
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from PIL import Image
import torch
import torch.nn.functional as F

from pipeline.features import FeatureExtractor, load_image_tensor
from pipeline.patchcore import PatchBank
from pipeline.timing import PhaseTimer


def _save_anomaly_map(
    raw_img_path: str,
    patch_dists: torch.Tensor,
    crop_size: int,
    version: str,
    image_id: str,
    results_dir: Path,
) -> str:
    """Render 50% alpha blended anomaly heatmap on cropped input image."""
    num_patches = patch_dists.shape[0]
    side = int(math.isqrt(num_patches))
    dist_2d = patch_dists.reshape(1, 1, side, side).float()

    upsampled = F.interpolate(dist_2d, size=(crop_size, crop_size), mode="bilinear", align_corners=False)
    m_min = upsampled.min()
    m_max = upsampled.max()
    normalized = (upsampled - m_min) / (m_max - m_min + 1e-8)
    norm_np = normalized.squeeze().cpu().numpy()

    # Colorize with jet colormap
    colormap = cm.get_cmap("jet")
    heatmap_rgba = (colormap(norm_np) * 255).astype(np.uint8)
    heatmap_img = Image.fromarray(heatmap_rgba, mode="RGBA")

    # Load and crop base image
    base_img = Image.open(raw_img_path).convert("RGBA")
    # Resize and center crop to crop_size
    w, h = base_img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    cropped = base_img.crop((left, top, left + min_dim, top + min_dim)).resize((crop_size, crop_size))

    # Blend 50%
    blended = Image.blend(cropped, heatmap_img, alpha=0.5)

    out_dir = results_dir / "maps" / version
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{image_id}.png"
    blended.convert("RGB").save(out_file)

    # Return relative path with forward slashes
    return out_file.as_posix()


def score_images(
    df: pd.DataFrame,
    banks: Dict[str, PatchBank],
    extractor: FeatureExtractor,
    cfg: Dict[str, Any],
    timers: Dict[str, float],
    run_id: str,
    device_label: str,
) -> pd.DataFrame:
    """Stream batches through extractor and memory banks, producing scores.csv records."""
    eval_splits = ["calibration", "validation", "test"]
    df_eval = df[df["split"].isin(eval_splits)].copy()

    batch_size = cfg.get("batch_size", 8)
    crop_size = cfg.get("crop_size", 224)
    save_maps = cfg.get("save_maps", True)
    results_dir = Path(cfg.get("results_dir", "results"))

    records: List[Dict[str, Any]] = []

    # Process in batches
    num_samples = len(df_eval)
    eval_rows = df_eval.to_dict(orient="records")

    for i in range(0, num_samples, batch_size):
        batch_rows = eval_rows[i : i + batch_size]
        tensors = []
        for row in batch_rows:
            t = load_image_tensor(row["path"], cfg, row["condition"])
            tensors.append(t)
        batch_tensor = torch.stack(tensors, dim=0)

        # Feature extraction phase
        with PhaseTimer("features", timers, extractor.device):
            feats = extractor.extract(batch_tensor)

        # Scoring phase across each version
        with PhaseTimer("scoring", timers, extractor.device):
            for version_name, bank in banks.items():
                img_scores, patch_dists = bank.score(feats)
                img_scores_cpu = img_scores.cpu().numpy()

                for b, row in enumerate(batch_rows):
                    map_path = ""
                    if save_maps and row["split"] == "validation":
                        map_path = _save_anomaly_map(
                            row["path"],
                            patch_dists[b],
                            crop_size,
                            version_name,
                            row["image_id"],
                            results_dir,
                        )

                    records.append({
                        "run_id": run_id,
                        "image_id": row["image_id"],
                        "path": row["path"],
                        "category": row["category"],
                        "condition": row["condition"],
                        "split": row["split"],
                        "true_label": row["true_label"],
                        "model_version": version_name,
                        "anomaly_score": float(img_scores_cpu[b]),
                        "map_path": map_path,
                        "device": device_label,
                    })

    scores_df = pd.DataFrame(records, columns=[
        "run_id", "image_id", "path", "category", "condition", "split",
        "true_label", "model_version", "anomaly_score", "map_path", "device"
    ])
    return scores_df
