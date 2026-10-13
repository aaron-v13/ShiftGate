"""Dataset discovery and metadata indexing for PCB visual inspection images."""
from pathlib import Path
from typing import Any, Dict
import pandas as pd


def _extract_defect_type(filename: str) -> str:
    """Identify defect category from filename pattern or return empty string."""
    for dt in ["Missing Component", "Scratch", "Soldering Melt"]:
        if dt in filename:
            return dt
    return "defect"


def list_images(cfg: Dict[str, Any]) -> pd.DataFrame:
    """Index all images under data_root into a standardized DataFrame."""
    data_root = Path(cfg["data_root"])
    repo_root = Path.cwd()
    category = cfg.get("category", "PCB")

    records = []
    # Support both single-split folder (data/sample) and multi-split root
    subdirs_to_search = []
    if (data_root / "normal").exists() or (data_root / "anomaly").exists():
        subdirs_to_search.append(data_root)
    else:
        # Check subdirectories containing normal/anomaly
        for p in sorted(data_root.iterdir()):
            if p.is_dir() and ((p / "normal").exists() or (p / "anomaly").exists()):
                subdirs_to_search.append(p)

    if not subdirs_to_search:
        # Fallback to direct search if subdirectories not named normal/anomaly
        subdirs_to_search.append(data_root)

    img_extensions = {".jpg", ".jpeg", ".png", ".bmp"}

    for base_folder in subdirs_to_search:
        # Search normal images
        norm_dir = base_folder / "normal"
        if norm_dir.exists():
            for img_p in sorted(norm_dir.glob("*.*")):
                if img_p.suffix.lower() in img_extensions:
                    rel_to_data = img_p.relative_to(data_root).as_posix()
                    img_id = str(Path(rel_to_data).with_suffix("")).replace("/", "__").replace("\\", "__")
                    try:
                        p_str = img_p.relative_to(repo_root).as_posix()
                    except ValueError:
                        p_str = img_p.resolve().as_posix()
                    records.append({
                        "image_id": img_id,
                        "path": p_str,
                        "category": category,
                        "true_label": "good",
                        "condition": "baseline",
                        "defect_type": "",
                    })

        # Search anomaly images
        anom_dir = base_folder / "anomaly"
        if anom_dir.exists():
            for img_p in sorted(anom_dir.glob("*.*")):
                if img_p.suffix.lower() in img_extensions:
                    rel_to_data = img_p.relative_to(data_root).as_posix()
                    img_id = str(Path(rel_to_data).with_suffix("")).replace("/", "__").replace("\\", "__")
                    try:
                        p_str = img_p.relative_to(repo_root).as_posix()
                    except ValueError:
                        p_str = img_p.resolve().as_posix()
                    records.append({
                        "image_id": img_id,
                        "path": p_str,
                        "category": category,
                        "true_label": "defect",
                        "condition": "baseline",
                        "defect_type": _extract_defect_type(img_p.name),
                    })

    df = pd.DataFrame(records, columns=["image_id", "path", "category", "true_label", "condition", "defect_type"])
    return df
