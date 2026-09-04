#!/usr/bin/env python3
"""Run the repository SDD checks and the safe preview smoke validation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREVIEW = ROOT / "dev" / "sdd" / "tools" / "preview.py"
BASE_URL = os.environ.get("HEC_BASE_URL", "http://127.0.0.1:8181")
PID_FILE = ROOT / "dev" / "sdd" / ".runtime" / "preview.pid"


def run_step(label: str, command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")


def runtime_smoke() -> None:
    def get(path: str) -> dict:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    session = get("/api/session")
    if session != {"required": False, "authorised": True}:
        raise RuntimeError(f"Unexpected session response: {session}")
    status = get("/api/status")
    controller = status.get("controller", {})
    if controller.get("enabled") or controller.get("write_enabled"):
        raise RuntimeError("Preview controller/write flags are not safe")
    config = get("/api/config")["config"]
    if config["tng"]["write_enabled"] or config["goodwe"]["enabled"]:
        raise RuntimeError("Preview device write/read configuration is not safe")
    with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"Preview homepage returned HTTP {response.status}")
    print("Runtime smoke passed")


def preview_running() -> bool:
    try:
        pid = int(PID_FILE.read_text(encoding="ascii"))
        os.kill(pid, 0)
    except (OSError, ValueError, FileNotFoundError):
        return False
    return True


def main() -> int:
    python = sys.executable
    owned_preview = not preview_running()
    try:
        run_step("Ruff", [python, "-m", "ruff", "check", "."])
        run_step("Pytest", [python, "-m", "pytest", "-m", "not e2e"])
        run_step("Step validation", [python, str(ROOT / "dev" / "sdd" / "tools" / "validate_step.py")])
        run_step("Repo hygiene", [python, str(ROOT / "dev" / "sdd" / "tools" / "validate_repo.py")])
        run_step("Start safe preview", [python, str(PREVIEW), "start"])
        runtime_smoke()
    except (RuntimeError, OSError) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if owned_preview:
            subprocess.run([python, str(PREVIEW), "stop"], cwd=ROOT, check=False)
    print("\nSDD VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
