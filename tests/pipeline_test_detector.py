"""Unit tests for feature extraction, patch bank scoring, and distance chunking."""
import torch
from pipeline.device import get_device_info
from pipeline.features import FeatureExtractor, subsample_patches
from pipeline.patchcore import PatchBank, chunked_nearest_neighbor_dists


def test_chunked_cdist_matches_full():
    """Verify chunked nearest neighbor distance calculation matches full torch.cdist."""
    device = torch.device(get_device_info("auto")["torch_device"])
    queries = torch.randn(128, 64, device=device)
    bank = torch.randn(512, 64, device=device)

    chunked_res = chunked_nearest_neighbor_dists(queries, bank)
    full_dists = torch.cdist(queries, bank, p=2.0)
    expected_res = full_dists.min(dim=1).values

    assert torch.allclose(chunked_res, expected_res, atol=1e-5)


def test_subsample_patches_determinism_and_ratio():
    """Verify patch subsampling keeps the specified ratio and is deterministic."""
    p, d = 784, 128
    dummy_feats = torch.randn(p, d)
    image_id = "test__image__01"
    seed = 42

    ratio = 0.1
    sub1 = subsample_patches(dummy_feats, image_id, seed, ratio)
    sub2 = subsample_patches(dummy_feats, image_id, seed, ratio)

    expected_k = max(1, int(round(p * ratio)))
    assert sub1.shape == (expected_k, d)
    assert torch.equal(sub1, sub2)


def test_patch_bank_scores_identical_lower_than_noise():
    """Verify that a reference memory bank scores an identical patch lower than a noisy patch."""
    device = torch.device(get_device_info("auto")["torch_device"])
    ref_patch = torch.ones(1, 10, 64, device=device)
    bank = PatchBank.build([ref_patch.reshape(-1, 64)], device=device)

    identical_query = torch.ones(1, 10, 64, device=device)
    noisy_query = torch.ones(1, 10, 64, device=device) + 2.5

    score_ident, _ = bank.score(identical_query)
    score_noise, _ = bank.score(noisy_query)

    assert score_ident.item() < score_noise.item()
    assert torch.isclose(score_ident, torch.tensor([0.0], device=device), atol=1e-5)


def test_feature_extractor_forward():
    """Verify FeatureExtractor runs forward with weights=None and produces expected dimensions."""
    device = torch.device(get_device_info("auto")["torch_device"])
    extractor = FeatureExtractor(device=device, weights=None)
    dummy_batch = torch.randn(2, 3, 224, 224, device=device)

    feats = extractor.extract(dummy_batch)
    assert feats.shape == (2, 784, 1536)
