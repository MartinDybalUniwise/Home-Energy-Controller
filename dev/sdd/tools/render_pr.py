#!/usr/bin/env python3
"""Render a pull-request body from a completed step and current evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "dev" / "sdd" / ".runtime"
VALIDATOR = ROOT / "dev" / "sdd" / "tools" / "validate_step.py"


def _require_current_validation(step_dir: Path, validation: dict) -> None:
    if validation.get("status") != "PASS":
        raise ValueError("Validation evidence is not PASS")
    if validation.get("git_sha") != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip():
        raise ValueError("Validation evidence is stale")
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--phase", "done", "--step", str(step_dir)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ValueError("Step is not valid at DONE phase")


def render(step_dir: Path, output: Path) -> None:
    manifest = json.loads((step_dir / "STEP.json").read_text(encoding="utf-8"))
    validation = json.loads((RUNTIME / "validation.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "DONE":
        raise ValueError("Refusing to render an incomplete step")
    _require_current_validation(step_dir, validation)
    traceability = (step_dir / "TRACEABILITY.md").read_text(encoding="utf-8").strip()
    result = (step_dir / "RESULT.md").read_text(encoding="utf-8").strip()
    body = "\n".join([
        f"# Step {manifest['step']} validation evidence",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Classification: `{manifest['classification']}`",
        f"- Validation: `{validation['status']}` ({validation['counts']['passed']}/{validation['counts']['total']} checks passed)",
        "",
        "## Traceability",
        "",
        traceability,
        "",
        "## Result",
        "",
        result,
    ]) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(body, encoding="utf-8")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=RUNTIME / "pr_body.md")
    args = parser.parse_args()
    render(args.step, args.output)
    print(f"Rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
