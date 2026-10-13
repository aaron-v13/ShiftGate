"""Feature extraction and patch representation using WideResNet50."""
from typing import Any, Dict, Optional
import zlib
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as T

from pipeline.shifts import apply_shift


def load_image_tensor(path: str, cfg: Dict[str, Any], condition: str) -> torch.Tensor:
    """Load an image, apply synthetic shift if conditioned, and return normalized tensor."""
    pil_img = Image.open(path).convert("RGB")

    shift_cfg = cfg.get("shift", {})
    shift_type = shift_cfg.get("type", "auto")
    # Apply synthetic shift only if condition is shift_a and shift_type is synthetic or auto
    if condition == "shift_a" and shift_type in ["synthetic", "auto"]:
        pil_img = apply_shift(pil_img, cfg)

    image_size = cfg.get("image_size", 256)
    crop_size = cfg.get("crop_size", 224)

    transform = T.Compose([
        T.Resize((image_size, image_size)),
        T.CenterCrop(crop_size),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return transform(pil_img)


class FeatureExtractor:
    """Extract multi-scale patch embeddings from WideResNet50 backbone."""

    def __init__(self, device: torch.device, weights: Optional[Any] = "DEFAULT") -> None:
        """Initialize backbone architecture and transfer layers to the execution device."""
        self.device = device
        if weights == "DEFAULT":
            weights_val = models.Wide_ResNet50_2_Weights.DEFAULT
        else:
            weights_val = weights

        backbone = models.wide_resnet50_2(weights=weights_val)
        backbone.eval()
        self.model = backbone.to(device)

    def extract(self, batch: torch.Tensor) -> torch.Tensor:
        """Extract and concatenate locally pooled layer2 and layer3 patch tokens."""
        batch = batch.to(self.device)
        with torch.no_grad():
            x = self.model.conv1(batch)
            x = self.model.bn1(x)
            x = self.model.relu(x)
            x = self.model.maxpool(x)
            x = self.model.layer1(x)
            l2 = self.model.layer2(x)
            l3 = self.model.layer3(l2)

            p2 = F.avg_pool2d(l2, kernel_size=3, stride=1, padding=1)
            p3 = F.avg_pool2d(l3, kernel_size=3, stride=1, padding=1)
            p3_up = F.interpolate(p3, size=p2.shape[-2:], mode="bilinear", align_corners=False)

            concat = torch.cat([p2, p3_up], dim=1)
            b, c, h, w = concat.shape
            # Reshape to [B, P, C]
            patches = concat.permute(0, 2, 3, 1).reshape(b, h * w, c)
            return patches


def subsample_patches(feats: torch.Tensor, image_id: str, seed: int, ratio: float) -> torch.Tensor:
    """Subsample patch vectors per image using a deterministic CRC32 seed offset."""
    p, d = feats.shape
    if ratio >= 1.0:
        return feats

    k = max(1, int(round(p * ratio)))
    crc_offset = zlib.crc32(image_id.encode("utf-8")) & 0xFFFFFFFF
    combined_seed = (seed + crc_offset) & 0x7FFFFFFF

    gen = torch.Generator()
    gen.manual_seed(combined_seed)

    perm = torch.randperm(p, generator=gen)
    selected_indices = perm[:k]
    return feats[selected_indices]
