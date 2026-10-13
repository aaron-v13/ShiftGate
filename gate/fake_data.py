"""Generate deterministic fake scores and run metadata for testing and mock mode."""

import json
from pathlib import Path
import numpy as np
import pandas as pd


def generate_fake_data(out_dir: str | Path = "gate", seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Generate fake scores DataFrame and run_meta dictionary and save them."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    run_id = "FAKE-cpu-20261013T120000"
    device = "cpu"
    category = "pcb"
    versions = ["v1_current", "v2_candidate_loose", "v3_candidate_reviewed"]

    rows = []

    # 1. Calibration: 40 normals (20 baseline, 20 shift_a)
    # Target 99th percentile = 0.50 for all three versions
    # We create 40 scores between 0.10 and 0.49 for the first 39, and 0.50 for the 40th.
    rng = np.random.default_rng(seed)

    for i in range(40):
        cond = "baseline" if i < 20 else "shift_a"
        img_id = f"fake_cal_{i:03d}"
        path = f"data/fake/calibration/{cond}/{img_id}.png"

        # Baseline calibration score
        base_cal_score = round(float(0.15 + (0.35 * (i / 39.0))), 4)
        for v in versions:
            # Slight version variance but 40th image is exactly 0.50
            if i == 39:
                score = 0.5000
            else:
                score = round(float(base_cal_score + rng.uniform(-0.01, 0.01)), 4)
                score = min(score, 0.4900)

            rows.append({
                "run_id": run_id,
                "image_id": img_id,
                "path": path,
                "category": category,
                "condition": cond,
                "split": "calibration",
                "true_label": "good",
                "model_version": v,
                "anomaly_score": score,
                "map_path": "",
                "device": device,
            })

    # 2. Validation: 30 good normals (15 baseline, 15 shift_a)
    for i in range(30):
        cond = "baseline" if i < 15 else "shift_a"
        img_id = f"fake_val_good_{i:03d}"
        path = f"data/fake/validation/{cond}/{img_id}.png"

        if cond == "baseline":
            # Baseline normal: all versions pass cleanly (score <= 0.35)
            s_v1 = round(float(0.18 + rng.uniform(0.01, 0.08)), 4)
            s_v2 = round(float(0.17 + rng.uniform(0.01, 0.08)), 4)
            s_v3 = round(float(0.17 + rng.uniform(0.01, 0.08)), 4)
        else:
            # shift_a normal:
            # In v1_current: 6 boards score > 0.50 (e.g. 0.55-0.65 -> False Holds)
            # In v2 and v3: only 1 board scores > 0.50 (e.g. board 20 has 0.58) -> False holds drop from 6 to 1!
            if i < 21:  # images 15, 16, 17, 18, 19, 20 score > 0.50 in v1
                s_v1 = round(float(0.53 + rng.uniform(0.02, 0.10)), 4)
                if i == 20:
                    s_v2 = round(float(0.54 + rng.uniform(0.01, 0.04)), 4)
                    s_v3 = round(float(0.54 + rng.uniform(0.01, 0.04)), 4)
                else:
                    s_v2 = round(float(0.25 + rng.uniform(0.01, 0.08)), 4)
                    s_v3 = round(float(0.25 + rng.uniform(0.01, 0.08)), 4)
            else:
                s_v1 = round(float(0.30 + rng.uniform(0.01, 0.10)), 4)
                s_v2 = round(float(0.25 + rng.uniform(0.01, 0.08)), 4)
                s_v3 = round(float(0.25 + rng.uniform(0.01, 0.08)), 4)

        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "good",
            "model_version": "v1_current",
            "anomaly_score": s_v1,
            "map_path": "",
            "device": device,
        })
        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "good",
            "model_version": "v2_candidate_loose",
            "anomaly_score": s_v2,
            "map_path": "",
            "device": device,
        })
        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "good",
            "model_version": "v3_candidate_reviewed",
            "anomaly_score": s_v3,
            "map_path": "",
            "device": device,
        })

    # 3. Validation: 8 defects (4 baseline, 4 shift_a)
    # Defect index 7 (shift_a) is the contaminant defect that v2 misses!
    for i in range(8):
        cond = "baseline" if i < 4 else "shift_a"
        img_id = f"fake_val_defect_{i:03d}"
        path = f"data/fake/validation/{cond}/{img_id}.png"

        # In v1_current: all defects are caught (score > 0.50, e.g. 0.85)
        s_v1 = round(float(0.82 + rng.uniform(0.02, 0.10)), 4)

        # In v3_candidate_reviewed: all defects are caught (score > 0.50)
        s_v3 = round(float(0.80 + rng.uniform(0.02, 0.10)), 4)

        # In v2_candidate_loose: defect 7 scores under threshold (0.44 <= 0.50), missed!
        if i == 7:
            s_v2 = 0.4400
        else:
            s_v2 = round(float(0.79 + rng.uniform(0.02, 0.10)), 4)

        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "defect",
            "model_version": "v1_current",
            "anomaly_score": s_v1,
            "map_path": f"results/maps/v1_current/{img_id}.png",
            "device": device,
        })
        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "defect",
            "model_version": "v2_candidate_loose",
            "anomaly_score": s_v2,
            "map_path": f"results/maps/v2_candidate_loose/{img_id}.png",
            "device": device,
        })
        rows.append({
            "run_id": run_id,
            "image_id": img_id,
            "path": path,
            "category": category,
            "condition": cond,
            "split": "validation",
            "true_label": "defect",
            "model_version": "v3_candidate_reviewed",
            "anomaly_score": s_v3,
            "map_path": f"results/maps/v3_candidate_reviewed/{img_id}.png",
            "device": device,
        })

    df = pd.DataFrame(rows)

    meta = {
        "run_id": run_id,
        "device": device,
        "gpu_name": None,
        "torch_version": "2.2.0+fake",
        "hip_version": None,
        "seed": seed,
        "n_images": 78,
        "batch_size": 16,
        "image_size": 256,
        "timings_sec": {
            "features": 2.5,
            "bank": 1.2,
            "scoring": 3.8,
        },
        "dataset": {
            "name": "FAKE_PCB",
            "category": category,
            "licence": "CC-BY-4.0",
            "shift_type": "synthetic",
        },
        "notes": "FAKE",
    }

    scores_file = out_path / "FAKE_scores.csv"
    meta_file = out_path / "FAKE_run_meta.json"

    df.to_csv(scores_file, index=False)
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return df, meta


if __name__ == "__main__":
    generate_fake_data()
