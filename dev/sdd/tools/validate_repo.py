#!/usr/bin/env python3
"""Validate repository hygiene for the SDD workflow."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_ROOT = {"data", "logs", "history", "archive", ".env", "connect.json"}
SECRETS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)(password|passwd|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
]


def git_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / rel for rel in result.stdout.splitlines() if rel]


def main() -> int:
    errors: list[str] = []

    tracked_paths = {p.relative_to(ROOT).as_posix() for p in git_tracked_files()}
    for name in FORBIDDEN_ROOT:
        if any(rel.startswith(f"{name}/") or rel == name for rel in tracked_paths):
            errors.append(f"Forbidden tracked path present in Git: {name}")

    for path in git_tracked_files():
        if not path.is_relative_to(ROOT):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRETS:
            if pattern.search(text):
                errors.append(f"Potential secret pattern detected in {path.relative_to(ROOT)}")

    if errors:
        print("Repository hygiene validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository hygiene validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
