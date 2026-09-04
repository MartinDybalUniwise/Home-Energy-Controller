#!/usr/bin/env python3
"""Validate a step directory against the mandatory SDD structure."""

from __future__ import annotations

import json
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


def validate_step(step_dir: Path) -> list[str]:
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
            for key in ("step", "status", "classification"):
                if key not in manifest:
                    errors.append(f"STEP.json missing {key!r} in {step_dir.name}")
            if manifest.get("status") not in {"PLANNED", "IN_PROGRESS", "DONE", "BLOCKED"}:
                errors.append(f"STEP.json status is invalid in {step_dir.name}")

    requirement = step_dir / "REQUIREMENT.md"
    if requirement.exists() and "## Objective" not in requirement.read_text(encoding="utf-8"):
        errors.append(f"Requirement is missing an objective section in {step_dir.name}")

    plan = step_dir / "PLAN.md"
    if plan.exists() and "## Goal" not in plan.read_text(encoding="utf-8"):
        errors.append(f"Plan is missing a goal section in {step_dir.name}")

    acceptance = step_dir / "ACCEPTANCE_CRITERIA.md"
    if acceptance.exists() and "- [ ]" not in acceptance.read_text(encoding="utf-8"):
        errors.append(f"Acceptance criteria file is incomplete in {step_dir.name}")

    return errors


def main() -> int:
    candidates = [
        p for p in (ROOT / "dev").glob("step*") if p.is_dir() and (p / "STEP.json").exists()
    ]
    all_errors: list[str] = []
    for step_dir in sorted(candidates):
        all_errors.extend(validate_step(step_dir))

    if all_errors:
        print("Step validation failed:", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(candidates)} step directories successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
