"""Fail-fast local validation for the isolated Step11 development workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = Path(__file__).resolve().with_name("preview.py")
BASE_URL = os.environ.get("HEC_BASE_URL", "http://127.0.0.1:8181")
PID_FILE = Path(__file__).resolve().with_name(".runtime") / "preview.pid"


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
    print("Runtime smoke passed (safe flags and HTTP health)")


def preview_already_running() -> bool:
    try:
        pid = int(PID_FILE.read_text(encoding="ascii"))
        os.kill(pid, 0)
    except (OSError, ValueError, FileNotFoundError):
        return False
    return True


def main() -> int:
    python = sys.executable
    owned_preview = not preview_already_running()
    try:
        run_step("Ruff", [python, "-m", "ruff", "check", "."])
        run_step("Pytest", [python, "-m", "pytest"])
        run_step("Start safe preview", [python, str(PREVIEW), "start"])
        runtime_smoke()
        e2e_env = os.environ.copy()
        e2e_env["HEC_RUN_E2E"] = "1"
        e2e_env["HEC_BASE_URL"] = BASE_URL
        run_step(
            "Playwright",
            [
                python,
                "-m",
                "pytest",
                "dev/hec/tests/e2e",
                "-o",
                "addopts=",
                "-m",
                "e2e",
                "--screenshot",
                "only-on-failure",
                "--tracing",
                "retain-on-failure",
                "--output",
                "dev/step11/.runtime/playwright",
            ],
            env=e2e_env,
        )
    except (RuntimeError, OSError) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if owned_preview:
            subprocess.run([python, str(PREVIEW), "stop"], cwd=ROOT, check=False)
    print("\nFULL VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
