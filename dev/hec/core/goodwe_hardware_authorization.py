"""Auditable, non-config GoodWe hardware authorization artifact."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..storage.base import atomic_write_json, read_json
from .timeutil import to_iso

ARTIFACT_NAME = "goodwe_hardware_authorization.json"


def artifact_path(config) -> Path:
    return config.data_dir / ARTIFACT_NAME


def load(config) -> dict[str, Any]:
    artifact = read_json(artifact_path(config), {}) or {}
    if artifact.get("status") != "APPROVED":
        return {"status": "NOT_AUTHORIZED", "artifact": str(artifact_path(config))}
    required = ("device_host", "evidence_id", "approved_by", "approved_at")
    if any(not artifact.get(key) for key in required):
        return {"status": "INVALID", "artifact": str(artifact_path(config))}
    return {**artifact, "artifact": str(artifact_path(config))}


def authorize(config, *, device_host: str, evidence_id: str, approved_by: str,
              verification: Callable[[], bool]) -> dict[str, Any]:
    """Create the artifact only after an explicit external S07 verifier succeeds."""
    if not verification():
        raise PermissionError("GoodWe hardware verification did not succeed")
    record = {
        "status": "APPROVED",
        "device_host": device_host,
        "evidence_id": evidence_id,
        "approved_by": approved_by,
        "approved_at": to_iso(datetime.now(UTC)),
        "created_by": "goodwe_hardware_authorization_service",
    }
    atomic_write_json(artifact_path(config), record)
    return {**record, "artifact": str(artifact_path(config))}
