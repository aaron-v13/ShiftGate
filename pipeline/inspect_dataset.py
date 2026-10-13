"""Inspect RobustAD PCB dataset structure, metadata, and counts."""
import os
import json
from pathlib import Path

def inspect():
    root = Path(r"C:\datasets\robustad\PCB")
    print(f"Dataset root: {root}")
    folders = sorted([f for f in root.iterdir() if f.is_dir()])
    print("Folders found:", [f.name for f in folders])

    for folder in folders:
        print(f"\n--- {folder.name} ---")
        items = list(folder.iterdir())
        files = [x.name for x in items if x.is_file()]
        dirs = [x.name for x in items if x.is_dir()]
        print(f"Files: {files}")
        print(f"Subdirectories: {dirs}")

        # Check for json/jsonl metadata
        for mf in items:
            if mf.suffix in [".json", ".jsonl"]:
                print(f"Reading {mf.name}:")
                try:
                    if mf.suffix == ".json":
                        with open(mf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                print(f"  Keys: {list(data.keys())[:10]}")
                                # Print first few items or summary
                                for k in list(data.keys())[:5]:
                                    print(f"  Sample key {k}: {str(data[k])[:100]}")
                            elif isinstance(data, list):
                                print(f"  Length: {len(data)}, Sample entry: {str(data[0])[:150]}")
                    elif mf.suffix == ".jsonl":
                        with open(mf, "r", encoding="utf-8") as f:
                            lines = [json.loads(line) for idx, line in enumerate(f) if idx < 5]
                        print(f"  Sample jsonl entries (first {len(lines)}):")
                        for line in lines:
                            print(f"    {str(line)[:150]}")
                except Exception as e:
                    print(f"  Error reading {mf.name}: {e}")

        # Count images in subdirectories
        image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
        total_images = 0
        counts_by_dir = {}
        for d in items:
            if d.is_dir():
                imgs = [p for p in d.rglob("*") if p.suffix.lower() in image_extensions]
                counts_by_dir[d.name] = len(imgs)
                total_images += len(imgs)
        if counts_by_dir:
            print(f"Image counts: {counts_by_dir} (Total: {total_images})")
        else:
            top_imgs = [p for p in folder.glob("*") if p.suffix.lower() in image_extensions]
            print(f"Direct images: {len(top_imgs)}")

if __name__ == "__main__":
    inspect()
