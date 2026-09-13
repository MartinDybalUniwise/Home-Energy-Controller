"""Incremental, tolerant importer for SDG dBase history files."""

from __future__ import annotations

import hashlib
import json
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.timeutil import to_iso
from ..readers.base import BaseReader
from ..storage.base import atomic_write_json, read_json


class SDGHistoryReader(BaseReader):
    name = "sdg_history"

    def __init__(self, config, storage=None):
        super().__init__(config, storage)
        self.log_root_path = str(config.get("goodwe.sdg.log_root_path", "") or "").strip()
        self.checkpoint_path = config.data_dir / "sdg_history_checkpoint.json"
        self._checkpoint = read_json(self.checkpoint_path, {}) or {}
        self._last_import: dict[str, Any] = {}
        self._terminal_status("initialized")

    def is_enabled(self) -> bool:
        return bool(self.config.get("goodwe.sdg.enabled", False))

    def interval_seconds(self) -> int:
        return int(self.config.get("goodwe.read_interval_seconds", 10))

    def _terminal_status(self, state: str, **details: Any) -> None:
        payload = " ".join(f"{key}={value}" for key, value in details.items())
        print(f"[SDGHistoryReader] state={state} {payload}".rstrip(), flush=True)

    def paths(self) -> list[Path]:
        root = Path(self.log_root_path) if self.log_root_path else Path(".")
        candidates = [
            root / "Data" / "trend" / "min",
            root / "Data" / "trend" / "solar",
            root / "Data" / "Event2",
            root / "Data" / "Alarm",
        ]
        files: list[Path] = []
        for candidate in candidates:
            if candidate.is_dir():
                files.extend(sorted(path for path in candidate.rglob("*.dbf") if path.is_file()))
        return files

    @staticmethod
    def _decode(value: bytes, field_type: str, decimals: int) -> Any:
        if field_type == "C":
            return value.rstrip(b" \x00").decode("cp1250", errors="replace")
        if field_type in {"N", "F"}:
            text = value.decode("ascii", errors="ignore").strip()
            if not text:
                return None
            number = float(text) if "." in text else int(text)
            return number
        if field_type == "L":
            return value[:1].upper() in {b"Y", b"T", b"1"}
        if field_type == "D":
            text = value.decode("ascii", errors="ignore").strip()
            if len(text) == 8:
                return f"{text[:4]}-{text[4:6]}-{text[6:]}T00:00:00+00:00"
            return None
        return value.hex()

    @classmethod
    def _read_dbf(cls, path: Path, start_offset: int = 0) -> tuple[list[dict[str, Any]], int, int]:
        with path.open("rb") as handle:
            header = handle.read(32)
            if len(header) < 32:
                raise ValueError("DBF header is truncated")
            record_count = struct.unpack_from("<I", header, 4)[0]
            header_length = struct.unpack_from("<H", header, 8)[0]
            record_length = struct.unpack_from("<H", header, 10)[0]
            fields: list[tuple[str, str, int]] = []
            while handle.tell() < header_length - 1:
                descriptor = handle.read(32)
                if len(descriptor) < 32:
                    raise ValueError("DBF field descriptor is truncated")
                if descriptor[0] == 0x0D:
                    break
                name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip().lower()
                fields.append((name, chr(descriptor[11]), descriptor[16]))
            handle.seek(max(header_length, start_offset))
            offset = handle.tell()
            records: list[dict[str, Any]] = []
            for _ in range(record_count):
                raw = handle.read(record_length)
                if len(raw) < record_length:
                    break
                offset += len(raw)
                if raw[:1] == b"*":
                    continue
                row: dict[str, Any] = {}
                cursor = 1
                try:
                    for name, field_type, length in fields:
                        row[name] = cls._decode(raw[cursor:cursor + length], field_type, 0)
                        cursor += length
                except (UnicodeError, ValueError, IndexError):
                    continue
                records.append({"_offset": offset - record_length, **row})
            return records, offset, record_count

    @staticmethod
    def _timestamp(row: dict[str, Any]) -> str | None:
        date_value = row.get("date")
        time_value = row.get("time")
        if date_value is not None and time_value is not None:
            date_text = str(date_value).strip().replace(" ", "T")
            time_text = str(time_value).strip()
            if "T" not in date_text:
                date_text = f"{date_text}T{time_text}"
            return date_text if "+" in date_text else f"{date_text}+00:00"
        for key in ("timestamp", "datetime", "date_time", "time", "date", "dt"):
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                moment = value if value.tzinfo else value.replace(tzinfo=UTC)
                return to_iso(moment)
            text = str(value).strip()
            if text:
                normalized = text.replace(" ", "T")
                if normalized.endswith("Z"):
                    return normalized[:-1] + "+00:00"
                if "+" not in normalized and "-" in normalized[10:]:
                    normalized += "+00:00"
                return normalized
        return None

    @classmethod
    def _normalize(cls, row: dict[str, Any], source_file: Path) -> dict[str, Any] | None:
        timestamp = cls._timestamp(row)
        if timestamp is None:
            return None
        values = {key: value for key, value in row.items() if not key.startswith("_")}
        return {
            "timestamp": timestamp,
            "source": "sdg",
            "sdg_file": source_file.name,
            "values": values,
        }

    def import_history(self) -> dict[str, Any]:
        checkpoint = dict(self._checkpoint)
        imported = 0
        skipped = 0
        corrupt_files = 0
        duplicates = 0
        seen = set(checkpoint.get("records", []))
        file_state = checkpoint.setdefault("files", {})
        for path in self.paths():
            key = str(path.resolve())
            stat = path.stat()
            state = file_state.get(key, {})
            offset = int(state.get("offset", 0)) if int(state.get("size", 0)) <= stat.st_size else 0
            with path.open("rb") as source:
                prefix = source.read(offset)
                prefix_hash = hashlib.sha256(prefix).hexdigest()
            if state.get("prefix_hash") and state.get("prefix_hash") != prefix_hash:
                offset = 0
            try:
                rows, end_offset, _ = self._read_dbf(path, offset)
            except (OSError, ValueError, struct.error):
                corrupt_files += 1
                self._terminal_status("file_failed", file=path.name)
                continue
            records: list[dict[str, Any]] = []
            for row in rows:
                normalized = self._normalize(row, path)
                if normalized is None:
                    skipped += 1
                    continue
                fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True,
                                                        ensure_ascii=False).encode("utf-8")).hexdigest()
                if fingerprint in seen:
                    duplicates += 1
                    continue
                seen.add(fingerprint)
                records.append(normalized)
            if self.storage is not None and records:
                imported += self.storage.append_many("sdg", records)
            with path.open("rb") as source:
                end_prefix_hash = hashlib.sha256(source.read(end_offset)).hexdigest()
            file_state[key] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                               "offset": end_offset, "prefix_hash": end_prefix_hash}
        checkpoint["records"] = sorted(seen)
        atomic_write_json(self.checkpoint_path, checkpoint)
        self._checkpoint = checkpoint
        self._last_import = {"imported": imported, "skipped": skipped,
                             "duplicates": duplicates, "corrupt_files": corrupt_files}
        self._terminal_status("import_ok", **self._last_import)
        return dict(self._last_import)

    def read(self) -> dict[str, Any]:
        result = self.import_history()
        return {"online": True, "source": "sdg", "files": len(self.paths()), **result}

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "log_root_path": self.log_root_path,
            "available": bool(self.paths()),
            "checkpoint": str(self.checkpoint_path),
            "last_import": self._last_import,
            "terminal": "SDGHistoryReader active",
        }
