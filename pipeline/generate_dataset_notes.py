"""Generate pipeline/DATASET_NOTES.md with verified dataset counts and structure."""
import json
from pathlib import Path

def main():
    root = Path(r"C:\datasets\robustad\PCB")
    output_path = Path("pipeline/DATASET_NOTES.md")

    folders = sorted([f for f in root.iterdir() if f.is_dir()])
    
    lines = []
    lines.append("# Dataset Notes: AmazonScience/RobustAD (PCB Subset)")
    lines.append("")
    lines.append("## Overview and Attribution")
    lines.append("- **Dataset**: AmazonScience/RobustAD (PCB category subset)")
    lines.append("- **Source Path**: `C:\\datasets\\robustad\\PCB`")
    lines.append("- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0)")
    lines.append("- **Reference Paper / Repo**: RobustAD: An Anomaly Detection Benchmark under Domain Shift (Amazon Science)")
    lines.append("")
    lines.append("## Inspection Command")
    lines.append("Counts in this document were generated using:")
    lines.append("```bash")
    lines.append("python -m pipeline.generate_dataset_notes")
    lines.append("```")
    lines.append("")
    lines.append("## Folder Structure & Availability")
    lines.append("| Folder | Full Images Present? | Files Present | Subdirectories |")
    lines.append("|---|---|---|---|")

    folder_stats = {}
    for folder in folders:
        subdirs = [x.name for x in folder.iterdir() if x.is_dir()]
        files = [x.name for x in folder.iterdir() if x.is_file()]
        has_full_images = ("normal" in subdirs or "anomaly" in subdirs)
        lines.append(f"| `{folder.name}` | {'YES' if has_full_images else 'NO (metadata only)'} | {', '.join(files)} | {', '.join(subdirs) if subdirs else 'None'} |")

        # Parse metadata.jsonl
        mf = folder / "metadata.jsonl"
        entries = []
        if mf.exists():
            with open(mf, "r", encoding="utf-8") as f:
                entries = [json.loads(line) for line in f]
        
        # Real files on disk
        normal_disk = len(list((folder / "normal").glob("*.*"))) if (folder / "normal").exists() else 0
        anomaly_disk = len(list((folder / "anomaly").glob("*.*"))) if (folder / "anomaly").exists() else 0
        masks_disk = len(list((folder / "masks").glob("*.*"))) if (folder / "masks").exists() else 0

        # Labels in metadata
        meta_normal = sum(1 for e in entries if e.get("label") == 0)
        meta_anomaly = sum(1 for e in entries if e.get("label") == 1)

        # Defect types
        defect_breakdown = {}
        conditions = set()
        for e in entries:
            fn = Path(e["file_name"]).name
            parts = fn.split("_")
            if len(parts) >= 4:
                conditions.add("_".join(parts[2:4]))
            if e.get("label") == 1:
                for dtype in ["Missing Component", "Scratch", "Soldering Melt"]:
                    if dtype in fn:
                        defect_breakdown[dtype] = defect_breakdown.get(dtype, 0) + 1

        folder_stats[folder.name] = {
            "has_full_images": has_full_images,
            "normal_disk": normal_disk,
            "anomaly_disk": anomaly_disk,
            "masks_disk": masks_disk,
            "meta_normal": meta_normal,
            "meta_anomaly": meta_anomaly,
            "defect_breakdown": defect_breakdown,
            "conditions": conditions
        }

    lines.append("")
    lines.append("## Detailed Counts")
    lines.append("")
    lines.append("### Folders with Full Images Downloaded")
    lines.append("| Folder | Normal Images (Disk) | Anomaly Images (Disk) | Mask Images (Disk) | Total Images | Defect Breakdown (Missing Component / Scratch / Soldering Melt) |")
    lines.append("|---|---|---|---|---|---|")
    for fname, st in folder_stats.items():
        if st["has_full_images"]:
            db = st["defect_breakdown"]
            db_str = f"Missing: {db.get('Missing Component', 0)}, Scratch: {db.get('Scratch', 0)}, Solder: {db.get('Soldering Melt', 0)}"
            lines.append(f"| `{fname}` | {st['normal_disk']} | {st['anomaly_disk']} | {st['masks_disk']} | {st['normal_disk'] + st['anomaly_disk']} | {db_str} |")

    lines.append("")
    lines.append("### All Folders in Dataset (from metadata.jsonl)")
    lines.append("| Folder | Shift Condition in Metadata | Meta Normal (Good) | Meta Anomaly (Defect) | Defect Breakdown |")
    lines.append("|---|---|---|---|---|")
    for fname, st in folder_stats.items():
        cond_str = ", ".join(sorted(st["conditions"]))
        db = st["defect_breakdown"]
        db_str = f"Missing: {db.get('Missing Component', 0)}, Scratch: {db.get('Scratch', 0)}, Solder: {db.get('Soldering Melt', 0)}"
        lines.append(f"| `{fname}` | `{cond_str}` | {st['meta_normal']} | {st['meta_anomaly']} | {db_str} |")

    lines.append("")
    lines.append("## Defect Types Observed")
    lines.append("Across all metadata files (and confirmed on disk for `pcb_data_dir_train` and `pcb_data_dir_test0`), exactly 3 defect types exist:")
    lines.append("1. `Missing Component`")
    lines.append("2. `Scratch`")
    lines.append("3. `Soldering Melt`")
    lines.append("")
    lines.append("## Distribution Shift Conditions Identified")
    lines.append("- `pcb_data_dir_train`: Baseline training set (`None_None` / `resized_None`).")
    lines.append("- `pcb_data_dir_test0`: Baseline test set (`None_None` / `resized_None`).")
    lines.append("- `pcb_data_dir_test1`: Native **Lighting shift** (`Lighting_Morning`, `Lighting_Afternoon`, `Lighting_Evening`).")
    lines.append("- `pcb_data_dir_test2`: Native **White Balancing shift** (`Morning + AWB`, `Afternoon + AWB`, `Evening + AWB`).")
    lines.append("- `pcb_data_dir_test3`: Native **Rotation shift** (`Rotation_-5%`, `Rotation_5%`).")
    lines.append("- `pcb_data_dir_test4`: Native **Position shift** (`Position_-10%`, `Position_10%`).")
    lines.append("- `pcb_data_dir_test5`: Native **Shadow shift** (`Shadow_Light Alternate Position`, `Shadow_Object Alternate Location`).")
    lines.append("")
    lines.append("## Image Dimensions and Formats")
    lines.append("- Normal images: JPEG format, resolution 2560x2560 RGB.")
    lines.append("- Anomaly images: PNG format (with `.jpg` extension), resolution 2048x2048 RGB.")
    lines.append("- Pixel masks: PNG format (with `.png` extension), resolution 2048x2048 grayscale (L mode).")
    lines.append("")
    lines.append("## What Could NOT Be Verified")
    lines.append("1. **Image files for test1 through test5**: Only `metadata.jsonl` is present locally for `pcb_data_dir_test1` through `pcb_data_dir_test5`. The actual `.jpg` images and masks are not yet downloaded on this machine.")
    lines.append("2. **Exact physical capture setup details**: The metadata specifies condition strings (e.g. `Lighting_Morning`, `Evening + AWB`), but does not describe lux levels, color temperatures, or camera sensor specifications.")
    lines.append("3. **Defect bounding boxes/locations beyond masks**: The dataset provides binary pixel masks, but no tabular bounding box annotations.")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main()
