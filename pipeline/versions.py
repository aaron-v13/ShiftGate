"""Model version memory bank generation and scripted contamination integration."""
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
import torch

from pipeline.features import FeatureExtractor, load_image_tensor, subsample_patches
from pipeline.patchcore import PatchBank
from pipeline.timing import PhaseTimer


def add_scripted_contaminant(
    clean_patches: List[torch.Tensor],
    contaminant_patches: List[torch.Tensor],
) -> List[torch.Tensor]:
    """Inject scripted unreviewed contaminant defect patches into candidate bank."""
    return clean_patches + contaminant_patches


def _extract_image_patches(
    row: Dict[str, Any],
    extractor: FeatureExtractor,
    cfg: Dict[str, Any],
    ratio: float,
    timers: Dict[str, float],
) -> torch.Tensor:
    """Load image, extract features, and return subsampled patch embeddings."""
    with PhaseTimer("features", timers, extractor.device):
        tensor = load_image_tensor(row["path"], cfg, row["condition"])
        batch = tensor.unsqueeze(0)
        feats = extractor.extract(batch)  # [1, P, D]
        img_feats = feats.squeeze(0)  # [P, D]

    sub = subsample_patches(img_feats, row["image_id"], cfg.get("seed", 42), ratio)
    return sub


def build_banks(
    splits_df: pd.DataFrame,
    extractor: FeatureExtractor,
    cfg: Dict[str, Any],
    timers: Dict[str, float],
) -> Tuple[Dict[str, PatchBank], pd.DataFrame]:
    """Construct memory banks for v1_current, v2_candidate_loose, and v3_candidate_reviewed."""
    coreset_ratio = cfg.get("coreset_ratio", 0.1)
    contam_ratio = cfg.get("contaminant_keep_ratio", 1.0)
    seed = cfg.get("seed", 42)

    # Filter target splits
    ref_rows = splits_df[splits_df["split"] == "reference_v1"].to_dict(orient="records")
    cand_rows = splits_df[splits_df["split"] == "candidate_pool"].to_dict(orient="records")
    contam_rows = splits_df[splits_df["split"] == "contaminant"].to_dict(orient="records")

    ref_v1_patches: List[torch.Tensor] = []
    for row in ref_rows:
        p = _extract_image_patches(row, extractor, cfg, coreset_ratio, timers)
        ref_v1_patches.append(p)

    cand_pool_patches: List[torch.Tensor] = []
    for row in cand_rows:
        p = _extract_image_patches(row, extractor, cfg, coreset_ratio, timers)
        cand_pool_patches.append(p)

    contam_patches: List[torch.Tensor] = []
    for row in contam_rows:
        p = _extract_image_patches(row, extractor, cfg, contam_ratio, timers)
        contam_patches.append(p)

    # Assemble patches for each version
    v1_patches = ref_v1_patches
    v3_patches = ref_v1_patches + cand_pool_patches
    v2_patches = add_scripted_contaminant(v3_patches, contam_patches)

    with PhaseTimer("bank", timers, extractor.device):
        banks = {
            "v1_current": PatchBank.build(v1_patches, device=extractor.device),
            "v2_candidate_loose": PatchBank.build(v2_patches, device=extractor.device),
            "v3_candidate_reviewed": PatchBank.build(v3_patches, device=extractor.device),
        }

    # Build candidate_list_df
    cand_records = []
    for row in cand_rows:
        cand_records.append({
            "image_id": row["image_id"],
            "path": row["path"],
            "condition": row["condition"],
            "is_contaminant": False,
            "in_v3_bank": True,
        })
    for row in contam_rows:
        cand_records.append({
            "image_id": row["image_id"],
            "path": row["path"],
            "condition": row["condition"],
            "is_contaminant": True,
            "in_v3_bank": False,
        })

    cand_df = pd.DataFrame(cand_records, columns=["image_id", "path", "condition", "is_contaminant", "in_v3_bank"])
    # Deterministic shuffle
    rng = np.random.default_rng(seed)
    cand_df = cand_df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    results_dir = Path(cfg.get("results_dir", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    cand_df.to_csv(results_dir / "candidate_list.csv", index=False)

    return banks, cand_df
