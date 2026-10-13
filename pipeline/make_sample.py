"""Create a deterministic 32-image sample from pcb_data_dir_test0 into data/sample."""
import shutil
import random
from pathlib import Path

def main():
    src_dir = Path(r"C:\datasets\robustad\PCB\pcb_data_dir_test0")
    dst_dir = Path("data/sample")

    (dst_dir / "normal").mkdir(parents=True, exist_ok=True)
    (dst_dir / "anomaly").mkdir(parents=True, exist_ok=True)

    rng = random.Random(42)

    # 20 normal images
    normal_files = sorted(list((src_dir / "normal").glob("*.jpg")))
    rng.shuffle(normal_files)
    selected_normals = sorted(normal_files[:20])

    for f in selected_normals:
        shutil.copy2(f, dst_dir / "normal" / f.name)

    # 12 defect images: 4 per defect type
    anomaly_files = sorted(list((src_dir / "anomaly").glob("*.*")))
    by_type = {"Missing Component": [], "Scratch": [], "Soldering Melt": []}
    for f in anomaly_files:
        for t in by_type:
            if t in f.name:
                by_type[t].append(f)
                break

    selected_anomalies = []
    for t, files in by_type.items():
        rng.shuffle(files)
        selected_anomalies.extend(files[:4])

    selected_anomalies = sorted(selected_anomalies)
    for f in selected_anomalies:
        shutil.copy2(f, dst_dir / "anomaly" / f.name)

    print(f"Copied {len(selected_normals)} normal images and {len(selected_anomalies)} defect images to {dst_dir}")

if __name__ == "__main__":
    main()
