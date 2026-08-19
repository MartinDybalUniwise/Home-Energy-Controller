"""Diagnostický export pro podporu.

Tvrdé pravidlo: **v exportu nikdy nesmí být tajemství.** Konfigurace se
maskuje, logy se filtrují a výsledek se dá poslat e-mailem bez obav.
"""

from __future__ import annotations

import json
import platform
import sys
import zipfile
from pathlib import Path

from .. import __version__
from ..core.secrets import collect_secret_values, redact
from ..core.timeutil import now_local, to_iso

LOG_TAIL_LINES = 2000


def _tail(path: Path, lines: int = LOG_TAIL_LINES) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def _scrub(text: str, secrets: set[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def collect(app) -> dict:
    """Textová část exportu – bez tajemství."""
    return {
        "generated_at": to_iso(now_local()),
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "status": app.status(),
        "config": redact(app.config.data),
        "config_errors": app.config.errors,
        "history_sources": app.storage.sources(),
    }


def export(app, target: Path | None = None) -> Path:
    """Zabalí stav, konfiguraci a poslední logy do jednoho ZIP souboru."""
    target = Path(target) if target else (
        app.config.data_dir / f"hec-diagnostics-{now_local():%Y%m%d-%H%M%S}.zip")
    target.parent.mkdir(parents=True, exist_ok=True)

    secrets = collect_secret_values(app.config.data)
    connect = app.config.root / str(app.config.get("tng.connect_file", "connect.json"))
    if connect.exists():
        try:
            secrets |= collect_secret_values(json.loads(connect.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass

    summary = json.dumps(collect(app), ensure_ascii=False, indent=2)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", _scrub(summary, secrets))
        for log in sorted(app.config.logs_dir.glob("*.log")):
            archive.writestr(f"logs/{log.name}", _scrub(_tail(log), secrets))
    return target
