#!/usr/bin/env python3
"""Run the safe preview in either mock or LAN read-only mode."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "dev" / "sdd" / ".runtime"
CONFIG = ROOT / "dev" / "sdd" / "config" / "preview.mock.json"
PID_FILE = RUNTIME / "preview.pid"
LOG_FILE = RUNTIME / "preview.log"
URL = "http://127.0.0.1:8181"

sys.path.insert(0, str(ROOT / "dev"))


def _running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _healthcheck(timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/api/session", timeout=1) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    return False


def _check_safety() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    config = data
    if config.get("controller", {}).get("enabled") is True:
        raise RuntimeError("controller.enabled must remain false")
    if config.get("tng", {}).get("write_enabled") is True:
        raise RuntimeError("tng.write_enabled must remain false")
    if config.get("goodwe", {}).get("enabled") is True:
        raise RuntimeError("goodwe.enabled must remain false in preview")


def start() -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    _check_safety()
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="ascii"))
        except ValueError:
            pid = 0
        if pid and _running(pid):
            print(f"Preview is already running at {URL} (pid {pid})")
            return 0
        PID_FILE.unlink(missing_ok=True)

    command = [sys.executable, str(ROOT / "dev" / "run.py"), "--config", str(CONFIG)]
    with LOG_FILE.open("ab") as output:
        options = {
            "cwd": str(ROOT),
            "stdin": subprocess.DEVNULL,
            "stdout": output,
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        process = subprocess.Popen(command, **options)
    PID_FILE.write_text(str(process.pid), encoding="ascii")
    if _healthcheck():
        print(f"Development preview is ready at {URL}")
        return 0
    print(f"Development preview failed to start; inspect {LOG_FILE}", file=sys.stderr)
    stop()
    return 1


def stop() -> int:
    if not PID_FILE.exists():
        print("Development preview is not running")
        return 0
    try:
        pid = int(PID_FILE.read_text(encoding="ascii"))
    except ValueError:
        pid = 0
    PID_FILE.unlink(missing_ok=True)
    if not pid or not _running(pid):
        print("Development preview is not running")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and _running(pid):
        time.sleep(0.2)
    if _running(pid):
        kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
        try:
            os.kill(pid, kill_signal)
        except OSError:
            pass
    print("Development preview stopped")
    return 0


def run() -> int:
    from hec.__main__ import main

    return main(["--config", str(CONFIG)])


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "run"
    if action == "start":
        return start()
    if action == "stop":
        return stop()
    if action == "run":
        return run()
    print("Usage: preview.py [start|stop|run|mock|lan]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
