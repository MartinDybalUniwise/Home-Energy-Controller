"""Rozhraní úložiště.

Readery ani controller nesmí vědět, jestli za tímto rozhraním je JSONL nebo SQL.
Díky tomu je pozdější migrace na SQLite/Timescale záměna jedné třídy.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


class StorageBackend(Protocol):
    def append(self, source: str, record: dict) -> None:
        """Zapíše jeden vzorek do historie."""

    def write_current(self, source: str, record: dict) -> None:
        """Přepíše aktuální stav zdroje."""

    def latest(self, source: str) -> dict | None:
        """Vrátí poslední známý stav zdroje."""

    def query(self, source: str, frm: datetime | None, to: datetime | None) -> Iterable[dict]:
        """Vrátí vzorky v časovém rozsahu, seřazené vzestupně."""


def atomic_write_json(path: Path, payload: Any) -> Path:
    """Zápis přes .tmp + replace. Přerušený zápis nesmí poškodit stávající soubor."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
