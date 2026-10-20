"""Incremental, tolerant importer for SDG dBase history files."""

from __future__ import annotations

import hashlib
import re
import struct
import threading
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..core.timeutil import to_iso
from ..readers.base import BaseReader
from ..storage.base import atomic_write_json, read_json
from ..storage.history import merge_history


class SDGHistoryReader(BaseReader):
    name = "sdg_history"

    def __init__(self, config, storage=None):
        super().__init__(config, storage)
        self.log_root_path = str(config.get("goodwe.sdg.log_root_path", "") or "").strip()
        self.checkpoint_path = config.data_dir / "sdg_history_checkpoint.json"
        self._checkpoint = read_json(self.checkpoint_path, {}) or {}
        if self._checkpoint.get('version') != 3:
            self._checkpoint = {'version': 3, 'files': {}}
        self._site_zone = ZoneInfo(config.get('system.timezone', 'Europe/Prague'))
        # Promotic stores trend pm_time in standard (winter) time in this source.
        year = datetime.now(UTC).year
        self._standard_offset = min(datetime(year, month, 1, tzinfo=self._site_zone).utcoffset().total_seconds()
                                    for month in (1, 7))
        self._import_lock = threading.Lock()
        self._path_cache: list[Path] = []
        self._discovered_at = float('-inf')
        self._audited: dict[str, float] = {}
        self._failed_files: dict[str, tuple[list[int], float]] = {}
        self._last_import: dict[str, Any] = {}
        self._terminal_status("initialized")

    def is_enabled(self) -> bool:
        return bool(self.config.get("goodwe.sdg.enabled", False))

    def interval_seconds(self) -> int:
        return int(self.config.get("goodwe.read_interval_seconds", 10))

    def _terminal_status(self, state: str, **details: Any) -> None:
        payload = " ".join(f"{key}={value}" for key, value in details.items())
        self.log.debug('import_status | state=%s %s', state, payload)

    @classmethod
    def candidate_directories(cls, root: Path) -> list[Path]:
        return [
            root / "Data" / "trend" / "min",
            root / "Data" / "trend" / "solar",
            root / "Data" / "Event2",
            root / "Data" / "Alarm",
            root / "Apps" / "SDGeco" / "Data" / "trend" / "min",
            root / "Apps" / "SDGeco" / "Data" / "trend" / "solar",
            root / "Apps" / "SDGeco" / "Data" / "Event2",
            root / "Apps" / "SDGeco" / "Data" / "Alarm",
        ]

    def paths(self) -> list[Path]:
        now = time.monotonic()
        if now - self._discovered_at < 30:
            return self._path_cache
        root = Path(self.log_root_path) if self.log_root_path else Path(".")
        files: list[Path] = []
        for candidate in self.candidate_directories(root):
            if candidate.is_dir():
                files.extend(sorted(path for path in candidate.rglob("*")
                                    if path.is_file() and path.suffix.lower() == ".dbf"))
        self._path_cache = sorted(set(files))
        self._discovered_at = now
        return self._path_cache

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
    def _read_dbf(cls, path: Path, start_offset: int = 0, limit: int | None = None) -> tuple[list[dict[str, Any]], int, int]:
        with path.open("rb") as handle:
            header = handle.read(32)
            if len(header) < 32:
                raise ValueError("DBF header is truncated")
            record_count = struct.unpack_from("<I", header, 4)[0]
            header_length = struct.unpack_from("<H", header, 8)[0]
            record_length = struct.unpack_from("<H", header, 10)[0]
            if header_length < 33 or record_length < 2:
                raise ValueError('Invalid DBF layout')
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
            remaining = max(0, record_count - (offset - header_length) // record_length)
            for _ in range(min(remaining, limit) if limit is not None else remaining):
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
    def _timestamp(row: dict[str, Any], standard_offset: float | None = None) -> str | None:
        def parse_text(text: str) -> str | None:
            normalized = re.sub(r'^(\d{4})\.(\d{2})\.(\d{2})', r'\1-\2-\3', text.strip()).replace(' ', 'T')
            try:
                moment = datetime.fromisoformat(normalized.replace('Z', '+00:00'))
                naive_zone = timezone(timedelta(seconds=standard_offset)) if standard_offset is not None else UTC
                return to_iso(moment if moment.tzinfo else moment.replace(tzinfo=naive_zone))
            except ValueError:
                return None

        pm_time = row.get("pm_time")
        if pm_time is not None:
            text = str(pm_time).strip()
            if text:
                return parse_text(text)

        date_value = row.get("date")
        time_value = row.get("time")
        if date_value is not None and time_value is not None:
            date_text = str(date_value).strip()
            time_text = str(time_value).strip()
            return parse_text(date_text if "T" in date_text else f"{date_text} {time_text}")

        for key in ("timestamp", "datetime", "date_time", "dt"):
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                moment = value if value.tzinfo else value.replace(tzinfo=UTC)
                return to_iso(moment)
            text = str(value).strip()
            if text:
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                return parse_text(text)

        return None

    @classmethod
    def _normalize(cls, row: dict[str, Any], source_file: Path, standard_offset: float | None = None) -> dict[str, Any] | None:
        timestamp = cls._timestamp(row, standard_offset if row.get('pm_time') is not None else None)
        if timestamp is None:
            return None
        values = {key: value for key, value in row.items() if not key.startswith("_")}
        return {
            "timestamp": timestamp,
            "source": cls.name,
            "sdg_file": source_file.name,
            "values": values,
        }

    def import_history(self) -> dict[str, Any]:
        # The existing worker and any explicit retry must never import concurrently.
        with self._import_lock:
            return self._import_history()

    def _import_history(self) -> dict[str, Any]:
        paths = self.paths()
        result = dict(discovered_files=len(paths), valid_rows=0, imported=0, skipped=0,
                      duplicates=0, corrupt_files=0, source_bytes=0, checkpoint_writes=0)
        processed = 0
        now = time.monotonic()
        # A bounded round-robin audit detects edits even with preserved size/mtime.
        audit = min(paths, key=lambda p: self._audited.get(str(p), 0), default=None)
        for path in paths:
            key = str(path)
            try:
                stat = path.stat()
                state = self._checkpoint['files'].get(key, {})
                metadata = [stat.st_size, stat.st_mtime_ns]
                failure = self._failed_files.get(key)
                if failure and failure[0] == metadata and now - failure[1] < 60:
                    continue
                verify = path == audit and now - self._audited.get(key, float('-inf')) >= 60
                if state.get('metadata') == metadata and not verify:
                    continue
                if processed >= 4:
                    continue
                processed += 1
                changed = self._import_file(path, state, result)
                if [path.stat().st_size, path.stat().st_mtime_ns] != metadata:
                    continue  # Source changed during read; safe to retry the committed rows.
                next_state = {'metadata': metadata, 'blocks': changed}
                if next_state != state and self.storage is not None:
                    candidate = {'version': 3, 'files': {**self._checkpoint['files'], key: next_state}}
                    atomic_write_json(self.checkpoint_path, candidate)
                    self._checkpoint = candidate
                    result['checkpoint_writes'] += 1
                self._audited[key] = time.monotonic()
                self._failed_files.pop(key, None)
            except (OSError, ValueError, struct.error) as exc:
                if path.exists():
                    failed_stat = path.stat()
                    self._failed_files[key] = ([failed_stat.st_size, failed_stat.st_mtime_ns], now)
                result['corrupt_files'] += 1
                self.log.warning('import_file_failed | file=%s error=%s', path.name, type(exc).__name__)
        self._last_import = result
        if result['imported'] or result['corrupt_files'] or result['checkpoint_writes']:
            self.log.info('import_summary | imported=%s corrupt=%s', result['imported'], result['corrupt_files'])
        return dict(result)

    def _import_file(self, path: Path, state: dict, result: dict) -> dict:
        blocks = {}
        owners = {}
        records = []
        relative = path.relative_to(Path(self.log_root_path)).as_posix()
        with path.open('rb') as handle:
            header = handle.read(32)
            result['source_bytes'] += len(header)
            if len(header) != 32:
                raise ValueError('Truncated DBF')
            count = struct.unpack_from('<I', header, 4)[0]
            start, width = struct.unpack_from('<HH', header, 8)
            if start < 33 or width < 2:
                raise ValueError('Invalid DBF layout')
            handle.seek(0)
            schema = handle.read(start)[32:]
            layout = hashlib.sha256(schema).hexdigest()
            result['source_bytes'] += start
            for index in range((count + 1023) // 1024):
                offset = start + index * 1024 * width
                handle.seek(offset)
                raw = handle.read(min(1024, count - index * 1024) * width)
                result['source_bytes'] += len(raw)
                if len(raw) % width or len(raw) != min(1024, count - index * 1024) * width:
                    raise ValueError('Incomplete DBF records')
                digest = hashlib.sha256(layout.encode() + raw).hexdigest()
                old = state.get('blocks', {}).get(str(index), {})
                if old.get('hash') == digest:
                    blocks[str(index)] = old
                    continue
                rows, _, _ = self._read_dbf(path, offset, 1024)
                result['source_bytes'] += len(raw) + start
                owner = f'{relative}:{index}'
                days = set()
                owners[owner] = old.get('days', [])
                for row in rows:
                    normalized = self._normalize(row, path, self._standard_offset)
                    if normalized is None:
                        result['skipped'] += 1
                        continue
                    normalized['timestamp'] = datetime.fromisoformat(normalized['timestamp']).astimezone(self._site_zone).isoformat()
                    normalized['sdg_record_id'] = f'{relative}:{row["_offset"]}'
                    normalized['sdg_block'] = owner
                    days.add(normalized['timestamp'][:10])
                    result['valid_rows'] += 1
                    records.append(normalized)
                blocks[str(index)] = {'hash': digest, 'days': sorted(days)}
            for index, old in state.get('blocks', {}).items():
                if index not in blocks:
                    owners[f'{relative}:{index}'] = old.get('days', [])
        if self.storage is not None and owners:
            unique_name = sum(p.name == path.name for p in self.paths()) == 1
            result['imported'] += merge_history(self.storage, self.name, records, owners=owners,
                                                legacy_files={path.name} if unique_name and not state.get('blocks') else set())
        return blocks

    def read(self) -> dict[str, Any]:
        result = self.import_history()
        return {"online": True, "source": self.name, "files": len(self.paths()), **result}

    def history_targets(self, values, sample):
        # Import diagnostics are current status, never a historical measurement.
        return []

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "log_root_path": self.log_root_path,
            "available": bool(self.paths()),
            "checkpoint": str(self.checkpoint_path),
            "last_import": self._last_import,
            "terminal": "SDGHistoryReader active",
        }
