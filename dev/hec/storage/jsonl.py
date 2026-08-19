"""JSONL úložiště: jeden JSON objekt na řádek, denní soubor na zdroj.

    history/goodwe/2026-08-19.jsonl
    data/current_goodwe.json

Append-only formát je odolný proti pádu procesu, dá se číst po řádcích a
nepotřebuje databázový server.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta
from pathlib import Path

from ..core.timeutil import day_key, now_local, parse_iso
from .base import atomic_write_json, read_json


class JsonlStorage:
    def __init__(self, data_dir: str | Path, history_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.history_dir = Path(history_dir)

    # --- zápis -------------------------------------------------------------
    def _day_file(self, source: str, when: datetime | None = None) -> Path:
        return self.history_dir / source / f"{day_key(when)}.jsonl"

    def append(self, source: str, record: dict) -> Path:
        """Přidá vzorek do denního souboru podle jeho vlastní časové značky."""
        when = parse_iso(record.get("timestamp")) or now_local()
        path = self._day_file(source, when)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        return path

    def append_many(self, source: str, records: Iterable[dict]) -> int:
        count = 0
        for record in records:
            self.append(source, record)
            count += 1
        return count

    def write_current(self, source: str, record: dict) -> Path:
        return atomic_write_json(self.data_dir / f"current_{source}.json", record)

    # --- čtení -------------------------------------------------------------
    def latest(self, source: str) -> dict | None:
        return read_json(self.data_dir / f"current_{source}.json")

    def sources(self) -> list[str]:
        if not self.history_dir.exists():
            return []
        return sorted(p.name for p in self.history_dir.iterdir() if p.is_dir())

    def days(self, source: str) -> list[str]:
        directory = self.history_dir / source
        if not directory.exists():
            return []
        return sorted(p.stem for p in directory.glob("*.jsonl"))

    def _iter_file(self, path: Path) -> Iterator[dict]:
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        # Poškozený řádek (např. po výpadku napájení) přeskočíme,
                        # zbytek historie musí zůstat čitelný.
                        continue
        except FileNotFoundError:
            return

    def query(self, source: str, frm: datetime | None = None, to: datetime | None = None,
              *, limit: int | None = None) -> list[dict]:
        """Vzorky v rozsahu, seřazené vzestupně. Otevírá jen dotčené denní soubory."""
        directory = self.history_dir / source
        if not directory.exists():
            return []

        wanted_days = None
        if frm is not None and to is not None:
            wanted_days = set()
            cursor = frm
            while cursor.date() <= to.date():
                wanted_days.add(day_key(cursor))
                cursor += timedelta(days=1)

        out: list[dict] = []
        for path in sorted(directory.glob("*.jsonl")):
            if wanted_days is not None and path.stem not in wanted_days:
                continue
            for record in self._iter_file(path):
                stamp = parse_iso(record.get("timestamp"))
                if stamp is None:
                    continue
                if frm is not None and stamp < frm:
                    continue
                if to is not None and stamp > to:
                    continue
                out.append(record)
        out.sort(key=lambda r: r.get("timestamp") or "")
        if limit is not None and len(out) > limit:
            out = out[-limit:]
        return out

    def last(self, source: str, count: int = 1) -> list[dict]:
        """Posledních N vzorků – čte pozpátku po denních souborech."""
        out: list[dict] = []
        for path in sorted((self.history_dir / source).glob("*.jsonl"), reverse=True):
            records = list(self._iter_file(path))
            out = records + out
            if len(out) >= count:
                break
        return out[-count:]
