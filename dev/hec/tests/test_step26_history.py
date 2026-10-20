from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from hec.core.model import Sample
from hec.readers.sdg_history_reader import SDGHistoryReader
from hec.storage.jsonl import JsonlStorage
from hec.tools.repair_history import repair
from test_readers_ote_tng import build_tng
from test_step16_goodwe_implementation import enabled_config, write_dbf


@pytest.mark.parametrize('stamp', ['2026-10-24T22:00:01Z', '2026-03-29T00:59:59Z',
                                  '2026-03-29T01:00:00Z', '2026-10-25T00:30:00Z',
                                  '2026-10-25T01:30:00Z'])
def test_tng_measurement_time_and_unknown_settings(tmp_path, tng_connect, stamp):
    reader, cfg, _ = build_tng(tmp_path, tng_connect)
    reader.storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    reader._telemetry_records = reader._telemetry_history([{'time': stamp, 't': 120}], {'boiler_on': True})
    reader._persist({}, Sample(source='tng'))
    row = reader.storage.last('tng')[0]
    assert datetime.fromisoformat(row['timestamp']).timestamp() == datetime.fromisoformat(stamp).timestamp()
    assert row['boiler_on'] is None
    assert row['outside_temperature'] == 12


def test_tng_retry_after_history_before_checkpoint_and_correction(tmp_path, tng_connect):
    reader, cfg, _ = build_tng(tmp_path, tng_connect)
    reader.storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    reader._telemetry_records = reader._telemetry_history([{'time': '2026-10-20T10:00:00Z', 't': 120}], {})
    with patch.object(reader, '_save_state', side_effect=OSError('interrupted')):
        with pytest.raises(OSError):
            reader._persist({}, Sample(source='tng'))
    assert reader.telemetry_state['last_sample_time'] is None
    reader._persist({}, Sample(source='tng'))
    reader._telemetry_records[0]['outside_temperature'] = 15
    reader._persist({}, Sample(source='tng'))
    assert len(reader.storage.last('tng', 10)) == 1
    assert reader.storage.last('tng')[0]['outside_temperature'] == 15


def test_tng_backfill_several_days_and_storage_failure_retry(tmp_path, tng_connect):
    reader, cfg, session = build_tng(tmp_path, tng_connect)
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    reader.storage = storage
    reader.telemetry_state['last_sample_time'] = '2026-10-15T00:00:00Z'
    from conftest import FakeResponse
    session.routes['HeatPumpData'] = FakeResponse(payload={'First': [
        {'time': '2026-10-18T22:00:01Z', 't': 140},
        {'time': '2026-10-16T00:00:01Z', 't': 120},
        {'time': '2026-10-17T00:00:01Z', 't': 130}]})
    with patch.object(storage, 'write_current', side_effect=OSError('disk unavailable')):
        assert not reader.poll().ok
    assert reader.telemetry_state['last_sample_time'] == '2026-10-15T00:00:00Z'
    assert reader.poll().ok
    assert reader.telemetry_state['last_sample_time'] == '2026-10-18T22:00:01Z'
    assert len(storage.last('tng', 10)) == 3
    assert reader.poll().ok
    assert len(storage.last('tng', 10)) == 3


def sdg(tmp_path):
    root = tmp_path / 'sdg/Data/trend/min'
    root.mkdir(parents=True)
    cfg = enabled_config(tmp_path, sdg={'log_root_path': str(tmp_path / 'sdg')})
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    return SDGHistoryReader(cfg, storage), root / 'history.dbf', storage


def test_sdg_checkpoint_after_storage_and_repeat(tmp_path):
    reader, path, storage = sdg(tmp_path)
    write_dbf(path, [('2026-10-18 23:59:59', 100, 'OK'), ('2026-10-20 00:00:01', 200, 'OK')])
    with patch('hec.readers.sdg_history_reader.atomic_write_json', side_effect=OSError('crash')):
        assert reader.import_history()['corrupt_files'] == 1
    assert reader._checkpoint['files'] == {}
    reader = SDGHistoryReader(reader.config, storage)  # process restart after the interrupted checkpoint
    reader.import_history()
    before = reader.checkpoint_path.read_bytes()
    assert reader.import_history()['imported'] == 0
    assert reader.checkpoint_path.read_bytes() == before
    assert len(storage.last('sdg_history', 10)) == 2


def test_sdg_old_correction_preserved_metadata_and_timestamp_move(tmp_path):
    reader, path, storage = sdg(tmp_path)
    write_dbf(path, [('2026-10-18 00:00:00', 100, 'OK')])
    reader.import_history()
    before = path.stat()
    write_dbf(path, [('2026-10-19 00:00:00', 999, 'OK')])
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    reader._audited[str(path)] = float('-inf')
    reader.import_history()
    rows = storage.last('sdg_history', 10)
    assert len(rows) == 1
    assert rows[0]['timestamp'].startswith('2026-10-19')
    assert rows[0]['values']['power'] == 999


def test_sdg_partial_file_does_not_advance_checkpoint(tmp_path):
    reader, path, storage = sdg(tmp_path)
    write_dbf(path, [('2026-10-18 00:00:00', 100, 'OK')])
    original = path.read_bytes()
    path.write_bytes(original[:-5])
    assert reader.import_history()['corrupt_files'] == 1
    assert reader._checkpoint['files'] == {}
    path.write_bytes(original)
    assert reader.import_history()['imported'] == 1
    assert len(storage.last('sdg_history', 10)) == 1


def test_sdg_poll_does_not_store_import_diagnostics_as_measurements(tmp_path):
    reader, path, storage = sdg(tmp_path)
    write_dbf(path, [('2026-10-18 00:00:00', 100, 'OK')])
    assert reader.poll().ok
    assert reader.poll().ok
    rows = storage.last('sdg_history', 10)
    assert len(rows) == 1
    assert 'values' in rows[0]


def test_corrupt_files_cannot_starve_remaining_history(tmp_path):
    reader, path, storage = sdg(tmp_path)
    for name in ('a', 'b', 'c', 'd'):
        (path.parent / f'{name}.dbf').write_bytes(b'broken')
    write_dbf(path, [('2026-10-18 00:00:00', 100, 'OK')])
    assert reader.import_history()['corrupt_files'] == 4
    assert reader.import_history()['imported'] == 1
    assert len(storage.last('sdg_history', 10)) == 1


def test_legacy_source_correction_is_adopted_without_duplicate(tmp_path):
    reader, path, storage = sdg(tmp_path)
    legacy = {'timestamp': '2026-10-18T00:00:00+00:00', 'source': 'sdg_history',
              'sdg_file': path.name, 'values': {'timestamp': '2026-10-18 00:00:00', 'power': 100, 'status': 'OK'}}
    # The old format has no physical row id. A unique source name and timestamp
    # allow authoritative source corrections to replace it during migration.
    storage.append('sdg_history', legacy)
    write_dbf(path, [('2026-10-18 00:00:00', 999, 'OK')])
    reader.import_history()
    rows = storage.last('sdg_history', 10)
    assert len(rows) == 1
    assert rows[0]['values']['power'] == 999


def test_legacy_utc_partition_adoption_crosses_local_midnight(tmp_path):
    reader, path, storage = sdg(tmp_path)
    storage.append('sdg_history', {'timestamp': '2026-10-18T23:30:00+00:00', 'source': 'sdg_history',
                                  'sdg_file': path.name,
                                  'values': {'timestamp': '2026-10-18 23:30:00', 'power': 100, 'status': 'OK'}})
    write_dbf(path, [('2026-10-18 23:30:00', 100, 'OK')])
    reader.import_history()
    rows = storage.last('sdg_history', 10)
    assert len(rows) == 1
    assert rows[0]['timestamp'] == '2026-10-19T01:30:00+02:00'


@pytest.mark.parametrize('stamp', ['2026-10-20T10:00:00Z', '2026-10-20T10:00:00-03:00',
                                  '2026-10-25T02:30:00+02:00', '2026-10-25T02:30:00+01:00'])
def test_sdg_preserves_explicit_zone(stamp):
    result = SDGHistoryReader._timestamp({'pm_time': stamp})
    assert datetime.fromisoformat(result).timestamp() == datetime.fromisoformat(stamp).timestamp()


def test_promotic_standard_time_is_not_daylight_time():
    # pm_time carries winter time all year; UTC instant stays the same at DST.
    assert SDGHistoryReader._timestamp({'pm_time': '2026.10.20 15:36:00'}, 3600) == '2026-10-20T15:36:00+01:00'
    for value in ('2026.03.29 01:30:00', '2026.03.29 02:30:00', '2026.10.25 01:30:00', '2026.10.25 02:30:00'):
        assert SDGHistoryReader._timestamp({'pm_time': value}, 3600).endswith('+01:00')


def test_repair_backup_and_second_run_no_changes(tmp_path):
    import json

    root = tmp_path / 'offline'
    storage = JsonlStorage(root / 'data', root / 'history')
    row = {'timestamp': '2026-10-20T12:00:00+02:00', 'source': 'tng',
           'sample_time': '2026-10-18T22:00:01Z', 'outside_temperature': 11, 'boiler_on': True}
    storage.append('tng', row)
    storage.append('tng', row)
    storage.append('sdg_history', {'timestamp': '2026-10-18T23:30:00+00:00', 'source': 'sdg_history',
                                 'sdg_file': 'solar.dbf', 'values': {'pm_time': '2026.10.18 23:30:00', 'pv': 10}})
    before = repair(root)
    assert before['sources']['tng']['duplicates'] == 1
    report = repair(root, apply=True, backup=tmp_path / 'backup')
    assert report['changed_files']
    manifest = json.loads((tmp_path / 'backup/manifest.json').read_text())
    assert manifest
    assert repair(root)['changed_files'] == []
    assert storage.last('tng')[0]['timestamp'].startswith('2026-10-19T00:00:01')
    assert storage.last('sdg_history')[0]['timestamp'] == '2026-10-19T00:30:00+02:00'
