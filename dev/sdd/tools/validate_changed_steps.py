#!/usr/bin/env python3
"""Validate changed canonical steps at the merge-ready DONE phase."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "dev" / "sdd" / "tools" / "validate_step.py"
STEP_PATH = re.compile(r"^dev/(step\d+)(?:/|$)")


def changed_step_names(paths: list[str]) -> list[str]:
    """Return unique canonical step directory names from changed repository paths."""
    names = {match.group(1) for path in paths if (match := STEP_PATH.match(path))}
    return sorted(names, key=lambda name: int(name[4:]))


def changed_steps(base: str, head: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Unable to inspect the changed files")
    return [ROOT / "dev" / name for name in changed_step_names(result.stdout.splitlines()) if (ROOT / "dev" / name / "STEP.json").is_file()]


def validate_step(step_dir: Path) -> None:
    command = [sys.executable, str(VALIDATOR), "--phase", "done", "--step", str(step_dir)]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base commit SHA")
    parser.add_argument("--head", required=True, help="Head commit SHA")
    args = parser.parse_args()

    try:
        steps = changed_steps(args.base, args.head)
    except RuntimeError as exc:
        print(f"Changed-step validation failed: {exc}", file=sys.stderr)
        return 1

    if not steps:
        print("No changed canonical steps require DONE validation.")
        return 0

    for step_dir in steps:
        print(f"Validating changed step at DONE phase: {step_dir.relative_to(ROOT)}")
        validate_step(step_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
