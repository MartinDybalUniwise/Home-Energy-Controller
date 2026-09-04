#!/usr/bin/env python3
"""Create the next numbered HEC step from the SDD templates."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = ROOT / "dev" / "sdd" / "templates"
README = ROOT / "dev" / "README.md"


def next_step_number() -> int:
    nums = [int(match.group(1)) for match in (re.match(r"step(\d+)$", p.name) for p in (ROOT / "dev").glob("step*")) if match]
    if not nums:
        return 1
    return max(nums) + 1


def create_step(number: int) -> Path:
    target = ROOT / "dev" / f"step{number:02d}"
    if target.exists():
        raise FileExistsError(f"Step directory already exists: {target}")

    readme_text = README.read_text(encoding="utf-8")
    if f"step{number:02d}/" in readme_text:
        raise ValueError(f"README already references step{number:02d}")
    rows = list(re.finditer(r"^\|.*step\d+.*\|.*$", readme_text, re.MULTILINE))
    if not rows:
        raise ValueError("README has no step table rows")

    target.mkdir(parents=True, exist_ok=False)
    for template in TEMPLATES.glob("*.md"):
        (target / template.name).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    step_json = {
        "step": number,
        "classification": "LARGE",
        "status": "PLANNED",
        "gate_a": {
            "status": "PENDING",
            "approved_by": None,
            "approved_at": None,
        },
        "gate_b": {
            "status": "NOT_REQUESTED",
            "approved_by": None,
            "approved_at": None,
        },
        "gate_c": {
            "status": "NOT_REQUESTED",
            "approved_by": None,
            "approved_at": None,
        },
        "readiness": "NO",
        "requested_by": "repository owner / maintainer",
        "source": "",
        "branch": None,
        "pr": None,
        "notes": "",
        "requirements": [],
        "acceptance": [],
        "evidence": [],
    }
    (target / "STEP.json").write_text(json.dumps(step_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    new_line = f"| [`step{number:02d}/`](step{number:02d}/) | New step placeholder | 📝 plánováno |"
    insert_at = rows[-1].end()
    readme_text = readme_text[:insert_at] + "\n" + new_line + readme_text[insert_at:]
    README.write_text(readme_text, encoding="utf-8")
    return target


def main() -> int:
    number = next_step_number()
    step_dir = create_step(number)
    print(f"Created {step_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
