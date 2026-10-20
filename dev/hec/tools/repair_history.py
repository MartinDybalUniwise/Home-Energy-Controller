"""One-off offline history repair. Stop every writer before --apply.

Only proven TNG sample times/settings, SDG standard-time pm_time and exact
duplicates are repaired. No network/device access; other timestamps are preserved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..analysis.summaries import BASE_TEMPERATURE_C
from ..readers.sdg_history_reader import SDGHistoryReader
from ..storage.history import write_jsonl

SETTINGS = ('boiler_on', 'boiler_set_temperature', 'boiler_sensor', 'boiler_boost',
            'heating_on', 'heating_set_temperature', 'heating_mode', 'equit_curve')
MEASUREMENTS = ('outside_temperature', 'water_output_temperature', 'boiler_temperature', 'room_temperature')


def read_rows(path):
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def repair(root: Path, *, apply: bool = False, backup: Path | None = None, timezone: str = 'Europe/Prague') -> dict:
    with tempfile.TemporaryDirectory(prefix='hec-history-repair-') as staging:
        return _repair(root, apply=apply, backup=backup, timezone=timezone, staging=Path(staging))


def _repair(root: Path, *, apply: bool, backup: Path | None, timezone: str, staging: Path) -> dict:
    history = root / 'history'
    result = {'apply': apply, 'sources': {}, 'changed_files': [], 'unknown': [], 'conflicts': 0}
    plans = {}
    tng = {}
    original_tng = {}
    stats = dict(before=0, after=0, corrected_time=0, cleared_settings=0, duplicates=0)
    for path in sorted((history / 'tng').glob('*.jsonl')):
        rows = list(read_rows(path))
        original_tng[path] = rows
        for old in rows:
            stats['before'] += 1
            row = dict(old)
            stamp = row.get('sample_time')
            try:
                moment = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
                if moment.tzinfo is None:
                    raise ValueError('Unproven naive sample time')
            except ValueError:
                result['unknown'].append({'source': 'tng', 'file': path.name, 'reason': 'invalid sample_time'})
                # Preserve unknown data byte-for-value in its original partition.
                tng[f'unknown:{path.name}:{stats["before"]}'] = (path, row)
                continue
            target = history / 'tng' / f'{moment.astimezone(ZoneInfo(timezone)):%Y-%m-%d}.jsonl'
            row['timestamp'] = moment.astimezone(ZoneInfo(timezone)).isoformat()
            stats['corrected_time'] += int(row['timestamp'] != old.get('timestamp') or target != path)
            stats['cleared_settings'] += int(any(row.get(key) is not None for key in SETTINGS))
            for key in SETTINGS:
                row[key] = None
            key = moment.timestamp()
            if key in tng:
                previous = tng[key][1]
                if any(previous.get(field) != row.get(field) for field in MEASUREMENTS):
                    result['conflicts'] += 1
                    raise ValueError(f'Conflicting TNG measurements require source verification: {stamp}')
                stats['duplicates'] += 1
            tng[key] = (target, row)
    grouped = defaultdict(list)
    for path, row in tng.values():
        grouped[path].append(row)
    for path in set(original_tng) | set(grouped):
        rows = sorted(grouped.get(path, []), key=lambda row: row['timestamp'])
        if rows != original_tng.get(path, []):
            plans[path] = rows
    stats['after'] = len(tng)
    result['sources']['tng'] = stats
    sdg_stats = dict(before=0, after=0, duplicates=0, corrected_time=0, removed_import_status=0)
    site_zone = ZoneInfo(timezone)
    sdg_paths = set((history / 'sdg_history').glob('*.jsonl'))
    # Stage by target day; memory is bounded by one daily file, not all SDG history.
    for path in sorted((history / 'sdg_history').glob('*.jsonl')):
        handles = {}
        for row in read_rows(path):
            sdg_stats['before'] += 1
            if 'values' not in row and all(key in row for key in ('discovered_files', 'valid_rows', 'imported')):
                sdg_stats['removed_import_status'] += 1
                continue
            target_day = path.stem
            values = row.get('values', {})
            if values.get('pm_time') is not None:
                old_stamp = datetime.fromisoformat(row['timestamp'])
                standard = min(datetime(old_stamp.year, month, 1, tzinfo=site_zone).utcoffset().total_seconds()
                               for month in (1, 7))
                stamp = SDGHistoryReader._timestamp(values, standard)
                if stamp is not None:
                    normalized = datetime.fromisoformat(stamp).astimezone(site_zone)
                    corrected = normalized.isoformat()
                    sdg_stats['corrected_time'] += int(corrected != row['timestamp'])
                    row['timestamp'] = corrected
                    target_day = normalized.strftime('%Y-%m-%d')
                else:
                    result['unknown'].append({'source': 'sdg_history', 'file': path.name, 'reason': 'invalid pm_time'})
            if target_day not in handles:
                handles[target_day] = (staging / f'{target_day}.jsonl').open('a', encoding='utf-8')
            handles[target_day].write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
        for handle in handles.values():
            handle.close()
    staged = {}
    for path in staging.glob('*.jsonl'):
        unique = {}
        count = 0
        for row in read_rows(path):
            count += 1
            unique.setdefault(json.dumps(row, sort_keys=True, ensure_ascii=False), row)
        sdg_stats['duplicates'] += count - len(unique)
        sdg_stats['after'] += len(unique)
        write_jsonl(path, sorted(unique.values(), key=lambda row: datetime.fromisoformat(row['timestamp']).timestamp()))
        staged[history / 'sdg_history' / path.name] = path
    sdg_changed = {}
    for path in sdg_paths | set(staged):
        candidate = staged.get(path)
        desired = candidate.read_bytes() if candidate else b''
        if not path.exists() or path.read_bytes() != desired:
            sdg_changed[path] = candidate
    result['sources']['sdg_history'] = sdg_stats
    # Only these summary fields depend on TNG; never recompute energy from a partial copy.
    summary_changes = 0
    affected_days = {path.stem for path in plans}
    for path in sorted((history / 'summary').glob('*.jsonl')):
        old = list(read_rows(path))
        rows = []
        for item in old:
            row = dict(item)
            if row.get('date') in affected_days:
                target = history / 'tng' / f'{row["date"]}.jsonl'
                values = [r.get('outside_temperature') for r in grouped.get(target, [])]
                values = [v for v in values if isinstance(v, (int, float))]
                mean = round(sum(values) / len(values), 1) if values else None
                row['mean_outside_c'] = mean
                row['degree_days'] = round(max(0, BASE_TEMPERATURE_C - mean), 2) if mean is not None else None
            summary_changes += int(row != item)
            rows.append(row)
        if rows != old:
            plans[path] = rows
    result['sources']['summary'] = {'corrected': summary_changes}
    changed_paths = sorted(set(plans) | set(sdg_changed))
    result['changed_files'] = [str(path.relative_to(root)) for path in changed_paths]
    if apply and changed_paths:
        if backup is None or backup.resolve().is_relative_to(root.resolve()):
            raise ValueError('A new backup directory outside the repaired root is required')
        backup.mkdir(parents=True, exist_ok=False)
        manifest = {}
        paths = changed_paths + [p for p in (root / 'data').glob('*') if p.name in
                                 ('tng_runtime_state.json', 'sdg_history_checkpoint.json')]
        for path in paths:
            relative = path.relative_to(root)
            if not path.exists():
                manifest[str(relative)] = None
                continue
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise OSError('Backup verification failed')
            manifest[str(relative)] = digest
        (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        for path, rows in plans.items():
            write_jsonl(path, rows)
        for path, candidate in sdg_changed.items():
            if candidate:
                temporary = path.with_suffix('.jsonl.tmp')
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, temporary)
                temporary.replace(path)
            else:
                write_jsonl(path, [])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--writers-stopped', action='store_true')
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.apply and not args.writers_stopped:
        parser.error('--apply requires --writers-stopped after every writer is stopped')
    report = repair(args.root, apply=args.apply, backup=args.backup)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'changed_files'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
