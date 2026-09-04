#!/usr/bin/env python3
"""Create the next numbered HEC step from the SDD templates."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = ROOT / "dev" / "sdd" / "templates"
README = ROOT / "dev" / "README.md"


def next_step_number() -> int:
    existing = [p for p in (ROOT / "dev").glob("step*") if p.is_dir()]
    nums = []
    for folder in existing:
        try:
            nums.append(int(folder.name.replace("step", "")))
        except ValueError:
            continue
    if not nums:
        return 1
    return max(nums) + 1


def create_step(number: int) -> Path:
    target = ROOT / "dev" / f"step{number:02d}"
    if target.exists():
        raise FileExistsError(f"Step directory already exists: {target}")

    target.mkdir(parents=True, exist_ok=False)
    for template in TEMPLATES.glob("*.md"):
        (target / template.name).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    step_json = {
        "step": f"{number:02d}",
        "name": "",
        "status": "PLANNED",
        "classification": "LARGE",
        "gates": {
            "plan_approved": False,
            "human_preview_test": False,
            "pr_approved": False,
        },
        "requirements": [],
        "acceptance": [],
        "evidence": [],
    }
    (target / "STEP.json").write_text(json.dumps(step_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_text = README.read_text(encoding="utf-8")
    marker = "| [`step12/`](step12/) |"
    new_line = f"| [`step{number:02d}/`](step{number:02d}/) | New step placeholder | 📝 plánováno |"
    if marker in readme_text and f"step{number:02d}/" not in readme_text:
        insert_at = readme_text.index(marker) + len(marker)
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
