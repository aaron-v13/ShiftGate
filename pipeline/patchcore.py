"""PatchCore memory bank construction, chunked distance calculation, and scoring."""
from typing import Iterable, List, Optional, Tuple
import torch

BANK_CHUNK_SIZE: int = 4096
QUERY_CHUNK_SIZE: int = 1024


def chunked_nearest_neighbor_dists(queries: torch.Tensor, bank: torch.Tensor) -> torch.Tensor:
    """Compute minimum Euclidean distance for each query patch to the bank in bounded memory chunks."""
    num_queries = queries.shape[0]
    num_bank = bank.shape[0]

    min_dists = torch.full((num_queries,), float("inf"), device=queries.device, dtype=queries.dtype)

    for q_start in range(0, num_queries, QUERY_CHUNK_SIZE):
        q_end = min(q_start + QUERY_CHUNK_SIZE, num_queries)
        q_chunk = queries[q_start:q_end]

        chunk_mins = torch.full((q_end - q_start,), float("inf"), device=queries.device, dtype=queries.dtype)

        for b_start in range(0, num_bank, BANK_CHUNK_SIZE):
            b_end = min(b_start + BANK_CHUNK_SIZE, num_bank)
            b_chunk = bank[b_start:b_end]

            dists = torch.cdist(q_chunk, b_chunk, p=2.0)
            dists_min = dists.min(dim=1).values
            chunk_mins = torch.minimum(chunk_mins, dists_min)

        min_dists[q_start:q_end] = chunk_mins

    return min_dists


class PatchBank:
    """Storage and nearest-neighbor scoring against a collection of reference patch embeddings."""

    def __init__(self, bank_tensor: torch.Tensor) -> None:
        """Store patch embeddings tensor in contiguous memory."""
        self.bank = bank_tensor.contiguous()

    @classmethod
    def build(cls, patch_list: List[torch.Tensor], device: Optional[torch.device] = None) -> "PatchBank":
        """Concatenate a list of patch tensors into a single memory bank."""
        if not patch_list:
            raise ValueError("Cannot build PatchBank from an empty list of patches.")
        all_patches = torch.cat(patch_list, dim=0)
        if device is not None:
            all_patches = all_patches.to(device)
        return cls(all_patches)

    def score(self, feats: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute maximum anomaly score and per-patch distance maps for a batch of patch features."""
        batch_size, num_patches, _ = feats.shape
        image_scores = torch.empty(batch_size, device=feats.device, dtype=feats.dtype)
        patch_dists = torch.empty((batch_size, num_patches), device=feats.device, dtype=feats.dtype)

        for b in range(batch_size):
            img_patches = feats[b]
            dists = chunked_nearest_neighbor_dists(img_patches, self.bank)
            patch_dists[b] = dists
            image_scores[b] = dists.max()

        return image_scores, patch_dists


class Detector:
    """Modular anomaly detector wrapper providing fit and score lifecycle methods."""

    def __init__(self, device: torch.device) -> None:
        """Initialize detector with target execution hardware."""
        self.device = device
        self.bank: Optional[PatchBank] = None

    def fit(self, patch_list: List[torch.Tensor]) -> None:
        """Construct internal reference memory bank from reference patches."""
        self.bank = PatchBank.build(patch_list, device=self.device)

    def score(self, feats: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Evaluate input batch features against fitted reference memory bank."""
        if self.bank is None:
            raise RuntimeError("Detector must be fitted before scoring.")
        return self.bank.score(feats)
