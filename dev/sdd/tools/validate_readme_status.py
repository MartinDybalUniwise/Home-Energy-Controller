#!/usr/bin/env python3
"""Check canonical step statuses in dev/README.md against STEP.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "dev" / "README.md"
ROW_PATTERN = re.compile(r"^\|.*\[`(step\d+)/`\].*$", re.MULTILINE)
STATUS_PATTERN = re.compile(r"<!--\s*status:\s*(PLANNED|IN_PROGRESS|DONE|BLOCKED)\s*-->")


def validate() -> list[str]:
    rows = {match.group(1): match.group(0) for match in ROW_PATTERN.finditer(README.read_text(encoding="utf-8"))}
    errors: list[str] = []
    for step_dir in sorted((ROOT / "dev").glob("step*")):
        manifest_path = step_dir / "STEP.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        step_name = step_dir.name
        row = rows.get(step_name)
        if row is None:
            errors.append(f"README is missing canonical row for {step_name}")
            continue
        status = STATUS_PATTERN.search(row)
        if status is None:
            errors.append(f"README row has no machine-readable status for {step_name}")
        elif status.group(1) != manifest["status"]:
            errors.append(f"README status disagrees for {step_name}: {status.group(1)} != {manifest['status']}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("README status validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("README canonical step statuses are synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
