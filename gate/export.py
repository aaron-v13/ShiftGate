"""Audit bundle export functionality."""

import json
from pathlib import Path
import shutil
from typing import Any, Sequence
import pandas as pd
import yaml


def export_bundle(
    report: dict[str, Any],
    out_dir: str | Path,
    extra_files: Sequence[str | Path] | None = None,
) -> str:
    """Export compliance and audit bundle containing report, changed decisions, policy, and hashes."""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # 1. gate_report.json
    report_file = dest / "gate_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # 2. changed_decisions.csv
    changed = report.get("changed_decisions", [])
    df_changed = pd.DataFrame(changed)
    df_changed.to_csv(dest / "changed_decisions.csv", index=False)

    # 3. policy_snapshot.yaml
    policy = report.get("policy", {})
    with open(dest / "policy_snapshot.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(policy, f)

    # 4. hashes.json
    hashes = report.get("hashes", {})
    with open(dest / "hashes.json", "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)

    # 5. extra_files
    if extra_files:
        for extra in extra_files:
            src = Path(extra)
            if src.exists():
                shutil.copy2(src, dest / src.name)

    return str(dest)
