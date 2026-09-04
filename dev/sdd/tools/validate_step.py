#!/usr/bin/env python3
"""Validate a step directory against the canonical SDD contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

REQUIRED_FILES = {
    "REQUEST.md",
    "REQUIREMENT.md",
    "PLAN.md",
    "ACCEPTANCE_CRITERIA.md",
    "TRACEABILITY.md",
    "STEP.json",
}
SCHEMA_PATH = ROOT / "dev" / "sdd" / "schema" / "step.schema.json"
VALID_PHASES = {"structural", "ready", "done"}
ID_PATTERN = re.compile(r"\b(?:REQ|AC|E)-[A-Z0-9-]+\b|\bS\d{2}\b")


def _validate_schema(manifest: object) -> list[str]:
    """Validate the stable manifest contract without requiring jsonschema."""
    if not isinstance(manifest, dict):
        return ["STEP.json must contain an object"]
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    missing = [key for key in schema["required"] if key not in manifest]
    if missing:
        errors.append(f"STEP.json missing required fields: {', '.join(missing)}")
    if not isinstance(manifest.get("step"), int) or isinstance(manifest.get("step"), bool) or manifest.get("step", 0) < 1:
        errors.append("STEP.json step must be a positive integer")
    if manifest.get("classification") not in {"SMALL", "LARGE"}:
        errors.append("STEP.json classification is invalid")
    if manifest.get("status") not in {"PLANNED", "IN_PROGRESS", "DONE", "BLOCKED"}:
        errors.append("STEP.json status is invalid")
    if manifest.get("readiness") not in {"YES", "NO"}:
        errors.append("STEP.json readiness is invalid")
    for gate_name in ("gate_a", "gate_b", "gate_c"):
        gate = manifest.get(gate_name)
        if not isinstance(gate, dict):
            errors.append(f"STEP.json {gate_name} must be an object")
            continue
        if gate.get("status") not in {"PENDING", "APPROVED", "NOT_REQUESTED", "NOT_REQUIRED"}:
            errors.append(f"STEP.json {gate_name}.status is invalid")
        if not (gate.get("approved_by") is None or isinstance(gate.get("approved_by"), str)):
            errors.append(f"STEP.json {gate_name}.approved_by must be a string or null")
        if not (gate.get("approved_at") is None or isinstance(gate.get("approved_at"), str)):
            errors.append(f"STEP.json {gate_name}.approved_at must be a string or null")
        if "reason" in gate and not isinstance(gate["reason"], str):
            errors.append(f"STEP.json {gate_name}.reason must be a string")
        if gate.get("status") == "NOT_REQUIRED" and not gate.get("reason", "").strip():
            errors.append(f"STEP.json {gate_name}.reason is required for NOT_REQUIRED")
    for key in ("requirements", "acceptance", "evidence"):
        if not isinstance(manifest.get(key), list) or not all(isinstance(item, str) for item in manifest[key]):
            errors.append(f"STEP.json {key} must be an array of strings")
    return errors


def _table_rows(text: str) -> list[list[str]]:
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.strip().startswith("|") and "---" not in line
    ]
    return rows[1:]


def _traceability_errors(step_dir: Path, *, phase: str, manifest: dict) -> list[str]:
    errors: list[str] = []
    rows = [
        row for row in _table_rows((step_dir / "TRACEABILITY.md").read_text(encoding="utf-8"))
        if row and (row[0].startswith(("REQ-", "AC-")) or re.fullmatch(r"S\d{2}", row[0]))
    ]
    if not rows:
        return [f"Traceability has no data rows in {step_dir.name}"]
    for row in rows:
        minimum_columns = 5 if row[0].startswith("REQ-") else 3 if row[0].startswith("AC-") else 4
        if len(row) < minimum_columns or any(not cell for cell in row[:minimum_columns]):
            errors.append(f"Traceability contains an incomplete row in {step_dir.name}")
            continue
        if phase == "done" and row[-1].upper() != "PASS":
            errors.append(f"Traceability row is not PASS in {step_dir.name}: {row[0]}")
        if row[0].startswith("REQ-"):
            id_cells = [row[0], *re.findall(r"(?:REQ|AC)-[A-Z0-9-]+|S\d{2}", row[1]), *re.findall(r"E-[A-Z0-9-]+", row[3])]
        elif row[0].startswith("AC-"):
            id_cells = [row[0], *re.findall(r"(?:REQ|AC)-[A-Z0-9-]+|S\d{2}|E-[A-Z0-9-]+", row[1])]
        else:
            id_cells = [row[0]]
        for identifier in id_cells:
            if not ID_PATTERN.search(identifier):
                errors.append(f"Traceability row has an invalid ID: {identifier}")
    declared_ids = set(manifest["requirements"] + manifest["acceptance"] + manifest["evidence"])
    referenced_ids = {identifier for row in rows for cell in row for identifier in ID_PATTERN.findall(cell)}
    missing = sorted(identifier for identifier in declared_ids if identifier not in referenced_ids)
    if missing:
        errors.append(f"Manifest IDs missing from traceability: {', '.join(missing)}")
    return errors


def _phase_errors(step_dir: Path, manifest: dict, phase: str) -> list[str]:
    if phase == "structural":
        return []
    errors: list[str] = []
    if manifest["gate_a"]["status"] != "APPROVED":
        errors.append("Gate A is not approved")
    if manifest["readiness"] != "YES":
        errors.append("readiness is not YES")
    if not manifest["requirements"] or not manifest["acceptance"]:
        errors.append("planning ID lists must not be empty")
    errors.extend(_traceability_errors(step_dir, phase=phase, manifest=manifest))
    if phase == "ready":
        return errors
    if manifest["status"] != "DONE":
        errors.append("status is not DONE")
    if manifest["gate_a"]["status"] != "APPROVED":
        errors.append("gate_a is not approved")
    for gate_name in ("gate_b", "gate_c"):
        if manifest[gate_name]["status"] not in {"APPROVED", "NOT_REQUIRED"}:
            errors.append(f"{gate_name} is not approved")
    if any(not item for item in manifest["evidence"]):
        errors.append("evidence contains an empty item")
    acceptance_text = (step_dir / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    for acceptance_id in manifest["acceptance"]:
        acceptance_lines = [line for line in acceptance_text.splitlines() if acceptance_id in line]
        if not acceptance_lines:
            errors.append(f"acceptance criteria is missing {acceptance_id}")
        elif any(re.match(r"^\s*- \[ \]", line) for line in acceptance_lines):
            errors.append(f"acceptance criteria contains unchecked item: {acceptance_id}")
    if re.search(r"\|\s*S\d+\s*\|.*\|\s*(?:PLANNED|IN_PROGRESS|BLOCKED)\s*\|", (step_dir / "PLAN.md").read_text(encoding="utf-8")):
        errors.append("plan contains unfinished steps")
    result = step_dir / "RESULT.md"
    if not result.exists() or "PASS" not in result.read_text(encoding="utf-8"):
        errors.append("RESULT.md has no PASS evidence")
    if manifest["status"] == "BLOCKED":
        errors.append("step is BLOCKED")
    return errors


def validate_step(step_dir: Path, phase: str = "structural") -> list[str]:
    if phase not in VALID_PHASES:
        return [f"Unknown validation phase: {phase}"]
    errors: list[str] = []
    if not step_dir.is_dir():
        return [f"Missing step directory: {step_dir}"]

    missing = sorted(REQUIRED_FILES - {p.name for p in step_dir.iterdir() if p.is_file()})
    if missing:
        errors.append(f"Missing files for {step_dir.name}: {', '.join(missing)}")

    step_json_path = step_dir / "STEP.json"
    if step_json_path.exists():
        try:
            manifest = json.loads(step_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in {step_json_path}: {exc}")
        else:
            errors.extend(_validate_schema(manifest))
            if not errors:
                errors.extend(_phase_errors(step_dir, manifest, phase))

    requirement = step_dir / "REQUIREMENT.md"
    if requirement.exists() and "## Objective" not in requirement.read_text(encoding="utf-8"):
        errors.append(f"Requirement is missing an objective section in {step_dir.name}")

    plan = step_dir / "PLAN.md"
    if plan.exists() and "## Goal" not in plan.read_text(encoding="utf-8"):
        errors.append(f"Plan is missing a goal section in {step_dir.name}")

    return errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=sorted(VALID_PHASES), default="structural")
    parser.add_argument("--step", type=Path)
    args = parser.parse_args()
    candidates = [args.step] if args.step else [
        p for p in (ROOT / "dev").glob("step*") if p.is_dir() and (p / "STEP.json").exists()
    ]
    all_errors: list[str] = []
    for step_dir in sorted(candidates):
        all_errors.extend(validate_step(step_dir, args.phase))

    if all_errors:
        print("Step validation failed:", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(candidates)} step directories successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
