"""Idempotent history batches; only importer-owned records are replaced."""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from ..core.timeutil import parse_iso
from .backup_tracking import HistoryChanges


def fingerprint(value) -> bytes:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode('utf-8')).digest()


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.jsonl.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def merge_history(storage, source: str, records: list[dict], *, owners: dict[str, list[str]] | None = None,
                  legacy_files: set[str] | None = None) -> int:
    """Upsert TNG by instant, or replace complete SDG blocks (including deletes).

    Previous block days permit timestamp corrections across day boundaries.
    A retry after any interrupted day replacement produces the same files.
    """
    incoming = defaultdict(dict)
    for record in records:
        stamp = parse_iso(record['timestamp'])
        if stamp is None:
            raise ValueError('History requires a measurement timestamp')
        identity = record.get('sdg_record_id') or stamp.timestamp()
        incoming[stamp.strftime('%Y-%m-%d')][identity] = record
    days = set(incoming)
    # The previous importer partitioned explicit UTC timestamps by UTC day.
    # Only initial adoption needs the neighbouring partitions; routine imports do not.
    if legacy_files:
        days.update((date.fromisoformat(day) + timedelta(days=offset)).isoformat()
                    for day in list(days) for offset in (-1, 1))
    if owners:
        days.update(day for previous in owners.values() for day in previous)
    all_records = [row for batch in incoming.values() for row in batch.values()]

    def source_key(row):
        return row.get('sdg_file'), parse_iso(row['timestamp']).timestamp()

    legacy = {(*source_key(row), fingerprint(row.get('values'))) for row in all_records} if owners is not None else set()
    unique = Counter(source_key(row) for row in all_records) if owners is not None else Counter()
    changed = 0
    with storage._history_lock:
        for day in sorted(days):
            prior = set()
            path = storage.history_dir / source / f'{day}.jsonl'
            old = list(storage._iter_file(path))
            current = incoming.get(day, {})
            if owners is None:
                merged = {}
                for row in old:
                    stamp = parse_iso(row.get('timestamp'))
                    key = stamp.timestamp() if stamp else json.dumps(row, sort_keys=True)
                    merged[key] = row
                merged.update(current)
                result = list(merged.values())
            else:
                result = [row for row in old if row.get('sdg_block') not in owners]
                # An exact row, or an unambiguous file/instant, identifies legacy data.
                result = [row for row in result if row.get('sdg_record_id') or
                          not ((*source_key(row), fingerprint(row.get('values')))
                               in legacy or (row.get('sdg_file') in (legacy_files or set()) and
                                             unique[source_key(row)] == 1))]
                result.extend(current.values())
            result.sort(key=lambda row: (parse_iso(row['timestamp']).timestamp(), row.get('sdg_record_id', '')))
            if old != result:
                HistoryChanges(storage.history_dir).mark(path)
                write_jsonl(path, result)
                prior = {fingerprint(row) for row in old}
                changed += sum(fingerprint(row) not in prior for row in current.values())
            # Release the preceding day before parsing the next one during a backfill.
            del old, result, prior
    return changed
