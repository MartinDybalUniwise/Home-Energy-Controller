"""Regression: ET inverter AC output must never be labelled grid export."""
from copy import deepcopy
from datetime import date
from threading import RLock
from types import SimpleNamespace

import pytest
from hec.analysis.summaries import Summaries
from hec.core.app import Application
from hec.core.config import Config
from hec.core.goodwe_energy import SEMANTICS, energy_values, project_energy
from hec.core.schema import defaults
from hec.readers.fte_reader import FTEReader
from hec.readers.goodwe import GoodWeReader
from hec.storage.jsonl import JsonlStorage
from hec.storage.series import downsample, record_values

RAW = {'e_day_exp': 7.9, 'e_day_imp': 0.0, 'e_load_day': 7.9,
       'meter_e_total_exp': 5668.75, 'meter_e_total_imp': 22359.87,
       'meter_comm_status': 1, 'active_power': 11, 'pbattery1': 1632}


@pytest.mark.parametrize('adapter', [GoodWeReader, FTEReader])
def test_real_et_sensor_domains_are_separate(tmp_path, adapter):
    config = Config(defaults(), path=tmp_path / 'config.json', root=tmp_path)
    values = adapter(config).map_values(RAW)
    assert values['e_export_day_kwh'] is None
    assert values['e_import_day_kwh'] is None
    assert values['inverter_ac_export_day_kwh'] == 7.9
    assert values['inverter_ac_import_day_kwh'] == 0.0
    assert values['grid_export_total_kwh'] == 5668.75
    assert values['grid_import_total_kwh'] == 22359.87
    assert values['energy_counter_semantics'] == SEMANTICS
    assert values['grid_import_w'] == 11
    assert values['battery_charge_w'] == 1632


@pytest.mark.parametrize('invalid', [None, True, False, -1, float('nan'), float('inf'), '7.9'])
def test_invalid_counters_never_become_zero_or_valid_energy(invalid):
    mapped = energy_values({'e_day_exp': invalid, 'meter_e_total_exp': invalid})
    assert mapped['inverter_ac_export_day_kwh'] is None
    assert mapped['grid_export_total_kwh'] is None


def test_measured_zero_and_unavailable_meter():
    assert energy_values({'meter_e_total_exp': 0})['grid_export_total_kwh'] == 0
    assert energy_values({})['grid_export_total_kwh'] is None
    assert energy_values({**RAW, 'meter_comm_status': 0})['grid_export_total_kwh'] is None


@pytest.mark.parametrize('nested', [True, False])
def test_legacy_flat_and_nested_values_project_without_mutation(nested):
    values = {'e_export_day_kwh': 7.9, 'e_import_day_kwh': 0, 'e_load_day_kwh': 7.9}
    raw = {'source': 'goodwe', 'values': values} if nested else values
    original = deepcopy(raw)
    projected = project_energy(raw)
    mapped = projected['values'] if nested else projected
    assert mapped['e_export_day_kwh'] is None
    assert mapped['e_import_day_kwh'] is None
    assert mapped['inverter_ac_export_day_kwh'] == 7.9
    assert mapped['inverter_ac_import_day_kwh'] == 0
    assert raw == original
    assert project_energy(projected) == projected


def test_current_masks_legacy_snapshot_without_touching_controller_input():
    raw = {'timestamp': '2026-10-22T08:00:00+02:00', 'e_export_day_kwh': 7.6}
    app = SimpleNamespace(_lock=RLock(), snapshot={'goodwe': raw})
    payload = Application.current(app, include_status=False)
    assert payload['sources']['goodwe']['e_export_day_kwh'] is None
    assert app.snapshot['goodwe']['e_export_day_kwh'] == 7.6


def test_history_masks_before_aggregation_without_rewriting(tmp_path):
    storage = JsonlStorage(tmp_path / 'data', tmp_path / 'history')
    path = storage.append('goodwe', {'timestamp': '2026-10-22T08:00:00+02:00',
                                     'e_export_day_kwh': 7.9, 'grid_export_w': 10})
    before = path.read_bytes()
    rows = storage.query('goodwe')
    assert rows[0]['e_export_day_kwh'] is None
    buckets = downsample(rows, ['e_export_day_kwh', 'grid_export_w'], 900)
    assert 'e_export_day_kwh' not in buckets[0]
    assert buckets[0]['grid_export_w'] == 10
    assert path.read_bytes() == before


def test_mixed_legacy_shape_cannot_bypass_projection():
    raw = {'e_export_day_kwh': 7.9, 'values': {'house_w': 400}}
    before = deepcopy(raw)
    projected = project_energy(raw)
    assert projected['e_export_day_kwh'] is None
    assert record_values(projected)['e_export_day_kwh'] is None
    assert record_values(projected)['inverter_ac_export_day_kwh'] == 7.9
    assert record_values(projected)['house_w'] == 400
    assert raw == before


def test_daily_summary_uses_grid_power_not_inverter_ac_energy(tmp_path):
    config = Config(defaults(), path=tmp_path / 'config.json', root=tmp_path)
    storage = JsonlStorage(config.data_dir, config.history_dir)
    for minute in ['00', '15', '30']:
        storage.append('goodwe', {'timestamp': f'2026-10-21T00:{minute}:00+02:00',
                                  'e_export_day_kwh': 7.9, 'e_import_day_kwh': 999,
                                  'grid_export_w': 20, 'grid_import_w': 10})
    report = Summaries(config, storage).compute(date(2026, 10, 21))
    assert report['grid_export_kwh'] == 0.01
    assert report['grid_import_kwh'] == 0.005
