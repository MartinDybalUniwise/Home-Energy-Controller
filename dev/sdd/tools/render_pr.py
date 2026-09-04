#!/usr/bin/env python3
"""Render a pull-request body from Step13 evidence files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "dev" / "sdd" / ".runtime"


def render(step_dir: Path, output: Path) -> None:
    manifest = json.loads((step_dir / "STEP.json").read_text(encoding="utf-8"))
    validation = json.loads((RUNTIME / "validation.json").read_text(encoding="utf-8"))
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
    parser.add_argument("--step", type=Path, default=ROOT / "dev" / "step13")
    parser.add_argument("--output", type=Path, default=RUNTIME / "pr_body.md")
    args = parser.parse_args()
    render(args.step, args.output)
    print(f"Rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
