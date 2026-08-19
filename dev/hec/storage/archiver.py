"""Archivace historie starší než N dní.

Pravidlo zadání: **lokální soubor se smaže teprve po ověření kopie.** Nedostupný
NAS není chyba k řešení mazáním – archivace se prostě zkusí příště znovu.
"""

from __future__ import annotations

import gzip
import hashlib
import shutil
from datetime import timedelta
from pathlib import Path

from ..core.logging_setup import event, get_logger, warn_event
from ..core.timeutil import now_local


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Archiver:
    def __init__(self, config, storage):
        self.config = config
        self.storage = storage
        self.log = get_logger("archiver")

    @property
    def enabled(self) -> bool:
        return self.config.archive_dir is not None

    def cutoff_day(self) -> str:
        days = int(self.config.get("storage.archive_after_days", 30))
        return (now_local() - timedelta(days=days)).strftime("%Y-%m-%d")

    def candidates(self) -> list[Path]:
        """Denní soubory starší než hranice. Dnešní soubor se nikdy nearchivuje."""
        cutoff = self.cutoff_day()
        history = self.config.history_dir
        if not history.exists():
            return []
        return sorted(path for path in history.glob("*/*.jsonl") if path.stem < cutoff)

    def target_for(self, path: Path) -> Path:
        archive = self.config.archive_dir
        suffix = ".jsonl.gz" if self.config.get("storage.compress_archive", True) else ".jsonl"
        return archive / path.parent.name / f"{path.stem}{suffix}"

    def archive_file(self, path: Path) -> bool:
        """Zkopíruje, ověří a teprve pak smaže. Vrací True při úspěchu."""
        target = self.target_for(path)
        source_bytes = path.read_bytes()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".part")
            if target.suffix == ".gz":
                with gzip.open(temporary, "wb") as handle:
                    handle.write(source_bytes)
            else:
                shutil.copyfile(path, temporary)
            temporary.replace(target)

            written = gzip.decompress(target.read_bytes()) if target.suffix == ".gz" else target.read_bytes()
            if sha256(written) != sha256(source_bytes):
                warn_event(self.log, "archive_verify_failed", file=path.name)
                target.unlink(missing_ok=True)
                return False
        except OSError as exc:
            # Typicky odpojený NAS. Lokální data zůstávají, zkusí se příště.
            warn_event(self.log, "archive_failed", file=path.name, error=type(exc).__name__)
            return False

        path.unlink()
        event(self.log, "archived", file=path.name, source=path.parent.name,
              bytes=len(source_bytes))
        return True

    def run(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "archived": 0, "failed": 0}
        archived = failed = 0
        for path in self.candidates():
            if self.archive_file(path):
                archived += 1
            else:
                failed += 1
        if archived or failed:
            event(self.log, "archive_run", archived=archived, failed=failed)
        return {"enabled": True, "archived": archived, "failed": failed}
