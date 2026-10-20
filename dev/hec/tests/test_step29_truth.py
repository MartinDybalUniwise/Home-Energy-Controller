"""Regressions for midnight measurements, intervals and cached price validity."""

import json
import threading
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from hec.analysis.heatpump import HeatPumpAnalyser
from hec.analysis.power_quality import consumption_report, meter_quality
from hec.analysis.summaries import Summaries
from hec.controller.metrics import Metrics
from hec.core.app import Application
from hec.readers.price_snapshot import cached_price_snapshot
from hec.readers.shelly import ShellyReader
from hec.tests.test_analysis import make, seed_day, yesterday_start


@pytest.mark.parametrize(('values', 'expected'), [
    ({'power_w': -8}, 'negative'), ({'power_w': 1500, 'l2_v': 0}, 'phase'),
    ({'power_w': None}, 'missing'), ({'power_w': float('inf')}, 'missing'),
    ({'power_w': 0}, 'valid'), ({'power_w': 1500, 'l2_v': 240}, 'valid'),
])
def test_quality_preserves_raw(values, expected):
    before = deepcopy(values)
    assert meter_quality(values) == expected
    assert values == before


def test_negative_day_is_unknown_not_negative_or_zero_energy(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, 'shelly', {'heatpump_power_w': -1500}, count=4)
    seed_day(storage, 'tng', {'heating_on': None, 'outside_temperature': 8}, count=4)
    report = HeatPumpAnalyser(config, storage).analyse_day()
    assert report['energy_kwh'] is None
    assert report['run_hours'] is None
    assert report['heating_share_pct'] is None
    assert report['kwh_per_degree_day'] is None
    assert report['measured'] is False
    assert report['power_quality']['invalid_samples'] == 4
    assert Summaries(config, storage).compute()['heatpump_kwh'] is None
    assert storage.query('shelly')[0]['heatpump_power_w'] == -1500


def test_zero_is_measured_and_intermediate_off_breaks_running_time(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, 'shelly', lambda i: {'heatpump_power_w': [1500, 0, 0, 1500, 0][i]},
             count=5, step=60)
    report = HeatPumpAnalyser(config, storage).analyse_day()
    assert report['run_hours'] == round(2 / 60, 2)
    assert report['power_quality']['covered_seconds'] == 240
    config, empty_storage = make(tmp_path / 'zero')
    seed_day(empty_storage, 'shelly', {'heatpump_power_w': 0}, count=3)
    zero = HeatPumpAnalyser(config, empty_storage).analyse_day()
    assert zero['measured'] is True
    assert zero['energy_kwh'] == zero['run_hours'] == 0


def test_invalid_missing_and_long_gap_do_not_bridge_intervals():
    start = yesterday_start()
    rows = [{'timestamp': (start + timedelta(seconds=s)).isoformat(), 'p': v}
            for s, v in [(0, 1000), (60, None), (120, 1000), (180, -8),
                         (240, 1000), (300, 1000), (360, float('inf')),
                         (420, 1000), (1500, 1000)]]
    report = consumption_report(rows, 'p')
    assert report['covered_seconds'] == 60
    assert report['energy_kwh'] == round(1 / 60, 4)
    assert report['quality'] == 'partial'
    assert report['invalid_samples'] == 1
    assert report['missing_samples'] == 2


def test_annotated_phase_failure_is_excluded_even_with_positive_power():
    start = yesterday_start()
    rows = [{'timestamp': (start + timedelta(minutes=i)).isoformat(),
             'p': 1000, 'q': 'phase'} for i in range(3)]
    assert consumption_report(rows, 'p', 'q')['energy_kwh'] is None


def test_partial_device_failure_is_visible_and_raw_power_retained(tmp_path, monkeypatch):
    config, storage = make(tmp_path, shelly={'enabled': True, 'devices': [
        {'name': 'HP', 'host': 'test.invalid', 'role': 'heatpump_meter'},
        {'name': 'Fridge', 'host': 'test.invalid', 'appliance_type': 'fridge'}]})
    reader = ShellyReader(config, storage)

    def read_device(device):
        if device['name'] == 'Fridge':
            raise TimeoutError('test timeout')
        return {'power_w': -8, 'l2_v': 0}

    monkeypatch.setattr(reader, 'read_device', read_device)
    result = reader.read()
    assert result['heatpump_power_w'] == -8
    assert result['heatpump_quality'] == 'negative'
    assert result['device_status']['fridge']['quality'] == 'offline'
    assert result['device_status']['fridge']['appliance_type'] == 'fridge'


def test_cache_rolls_midnight_and_quarter_without_network_or_snapshot_mutation(tmp_path):
    config, _ = make(tmp_path)
    day = '2026-10-21'
    (config.data_dir / f'ote-{day}.json').write_text(json.dumps({'date': day, 'periods': [
        {'start': '00:00', 'end': '00:15', 'price_total_czk_kwh': 0},
        {'start': '00:15', 'end': '00:30', 'price_total_czk_kwh': -1.2}]}), encoding='utf-8')
    old = {'timestamp': '2026-10-20T23:41:00+02:00', 'date': '2026-10-20',
           'price_total_czk_kwh': 5.685}
    first = cached_price_snapshot(config, old, datetime.fromisoformat(day + 'T00:10:00+02:00'))
    second = cached_price_snapshot(config, old, datetime.fromisoformat(day + 'T00:15:00+02:00'))
    missing = cached_price_snapshot(config, old, datetime.fromisoformat(day + 'T00:30:00+02:00'))
    assert first['date'] == day and first['price_total_czk_kwh'] == 0
    assert first['price_valid'] is True
    assert second['price_total_czk_kwh'] == -1.2
    assert missing['price_total_czk_kwh'] is None and missing['price_valid'] is False
    assert old['date'] == '2026-10-20' and old['price_total_czk_kwh'] == 5.685


def test_old_negative_summary_is_masked_without_history_write(tmp_path):
    config, storage = make(tmp_path)
    record = {'timestamp': yesterday_start().isoformat(), 'date': yesterday_start().date().isoformat(),
              'heatpump_kwh': -6.8442}
    storage.append('summary', record)
    assert Summaries(config, storage).recent(2)[0]['heatpump_kwh'] is None
    assert storage.query('summary')[0]['heatpump_kwh'] == -6.8442


def test_all_offline_keeps_diagnostics_and_error_count_after_success(tmp_path, monkeypatch):
    config, storage = make(tmp_path, shelly={'enabled': True, 'devices': [
        {'name': 'HP', 'host': 'test.invalid', 'role': 'heatpump_meter'}]})
    reader = ShellyReader(config, storage)
    monkeypatch.setattr(reader, 'read_device', lambda device: {'power_w': 1500})
    assert reader.poll().ok is True
    success = reader.status.last_success

    def fail(device):
        raise TimeoutError('unavailable')

    monkeypatch.setattr(reader, 'read_device', fail)
    sample = reader.poll()
    assert sample.ok is False
    assert sample.values['online'] is False
    assert sample.values['heatpump_power_w'] is None
    assert sample.values['heatpump_quality'] == 'offline'
    assert sample.values['device_status']['hp']['quality'] == 'offline'
    assert reader.status.error_count == 1
    assert reader.status.last_success == success
    assert reader.status.state == 'error'


def test_current_projects_price_without_mutating_control_snapshot(tmp_path):
    config, _ = make(tmp_path)
    app = Application.__new__(Application)
    app.config = config
    app._lock = threading.Lock()
    app.snapshot = {'ote': {'timestamp': yesterday_start().isoformat(), 'price_total_czk_kwh': 99}}
    before = deepcopy(app.snapshot)
    current = app.current(include_status=False)
    assert current['sources']['ote']['price_total_czk_kwh'] is None
    assert app.snapshot == before


def test_metric_unknown_heatpump_does_not_turn_into_zero():
    summaries = SimpleNamespace(recent=lambda days: [{'heatpump_kwh': None}])
    assert Metrics({}, None, summaries).totals()['heatpump_kwh'] is None
    summaries.recent = lambda days: [{'heatpump_kwh': 0}]
    assert Metrics({}, None, summaries).totals()['heatpump_kwh'] == 0
