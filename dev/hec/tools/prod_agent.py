"""CLI for the read-only HEC PROD operations agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from hec.agent.operations import OperationsAgent, ProdEvidenceReader
else:
    from ..agent.operations import OperationsAgent, ProdEvidenceReader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hec-prod-agent")
    parser.add_argument("root", help="read-only HEC PROD root")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--greeting", action="store_true")
    action.add_argument("--report", action="store_true")
    action.add_argument("--question")
    args = parser.parse_args(argv)
    agent = OperationsAgent(ProdEvidenceReader(args.root))
    result = agent.greeting() if args.greeting else agent.answer(args.question) if args.question else agent.report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
