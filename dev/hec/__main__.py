"""Vstupní bod: `python -m hec` (Windows i Linux stejně)."""

from __future__ import annotations

import argparse
import json
import sys

from .core.app import Application


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hec", description="Home Energy Controller")
    parser.add_argument("--config", help="cesta ke konfiguraci")
    parser.add_argument("--once", action="store_true", help="jedno kolo čtení a konec")
    parser.add_argument("--status", action="store_true", help="vypíše stav jako JSON")
    parser.add_argument("--no-web", action="store_true", help="jen sběr dat, bez webu")
    args = parser.parse_args(argv)

    app = Application(config_path=args.config)

    if args.status:
        print(json.dumps(app.status(), ensure_ascii=False, indent=2))
        return 0

    if args.once:
        samples = app.run_once()
        print(json.dumps({s.source: s.to_dict() for s in samples}, ensure_ascii=False, indent=2))
        return 0 if all(s.ok for s in samples) else 1

    app.start()
    if args.no_web:
        app.scheduler.run_forever()
        return 0

    try:
        from .web.server import serve
    except ImportError:
        app.scheduler.run_forever()
        return 0
    return serve(app)


if __name__ == "__main__":
    sys.exit(main())
