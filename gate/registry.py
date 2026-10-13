"""Registry management for active model version, approvals, activations, and rollbacks."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = Path("gate/registry.json")


def _get_registry_file(registry_path: str | Path | None = None) -> Path:
    """Resolve registry path, falling back to default."""
    return Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH


def get_registry(registry_path: str | Path | None = None) -> dict[str, Any]:
    """Read current registry state or return default initial state if file is absent."""
    p = _get_registry_file(registry_path)
    if not p.exists():
        return {
            "active_version": "v1_current",
            "previous_version": None,
            "history": [],
        }
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(registry_data: dict[str, Any], registry_path: str | Path | None = None) -> None:
    """Save registry state to JSON file."""
    p = _get_registry_file(registry_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)


def reset_registry(registry_path: str | Path | None = None) -> dict[str, Any]:
    """Reset registry to initial state with active=v1_current and empty history."""
    data: dict[str, Any] = {
        "active_version": "v1_current",
        "previous_version": None,
        "history": [],
    }
    _save_registry(data, registry_path)
    return data


def record_approval(
    report: dict[str, Any],
    reviewer: str,
    note: str = "",
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Record reviewer approval on gate report and log action into registry without mutating input report."""
    if not reviewer or not reviewer.strip():
        raise ValueError("Reviewer name cannot be empty.")

    now_iso = datetime.now(timezone.utc).isoformat()
    reg = get_registry(registry_path)
    reg["history"].append({
        "ts": now_iso,
        "action": "approve",
        "version": report.get("candidate_version"),
        "reviewer": reviewer.strip(),
        "note": note,
        "report_run_id": report.get("run_id"),
    })
    _save_registry(reg, registry_path)

    new_report = deepcopy(report)
    new_report["approved_by"] = reviewer.strip()
    new_report["approval_note"] = note
    new_report["approved_at"] = now_iso
    return new_report


def activate(report: dict[str, Any], registry_path: str | Path | None = None) -> dict[str, Any]:
    """Activate candidate version if allowed, approved, and matching current active version."""
    if report.get("activation") != "ALLOW":
        raise ValueError(f"Cannot activate candidate when activation is {report.get('activation')}.")

    approved_by = report.get("approved_by")
    if not approved_by or not str(approved_by).strip():
        raise ValueError("Cannot activate candidate without approval.")

    reg = get_registry(registry_path)
    current_active = reg.get("active_version")
    report_current = report.get("current_version")
    if report_current != current_active:
        raise ValueError(
            f"Stale report: report current_version '{report_current}' does not match active '{current_active}'."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    candidate_version = report.get("candidate_version")

    reg["previous_version"] = current_active
    reg["active_version"] = candidate_version
    reg["history"].append({
        "ts": now_iso,
        "action": "activate",
        "version": candidate_version,
        "reviewer": str(approved_by).strip(),
        "note": report.get("approval_note", ""),
        "report_run_id": report.get("run_id"),
    })
    _save_registry(reg, registry_path)
    return reg


def rollback(registry_path: str | Path | None = None) -> dict[str, Any]:
    """Roll back active version to previous version and log rollback."""
    reg = get_registry(registry_path)
    prev = reg.get("previous_version")
    if not prev:
        raise ValueError("Cannot roll back: no previous version recorded in registry.")

    current_active = reg.get("active_version")
    now_iso = datetime.now(timezone.utc).isoformat()

    reg["active_version"] = prev
    reg["previous_version"] = current_active
    reg["history"].append({
        "ts": now_iso,
        "action": "rollback",
        "version": prev,
        "reviewer": None,
        "note": f"Rolled back from {current_active} to {prev}",
        "report_run_id": None,
    })
    _save_registry(reg, registry_path)
    return reg
