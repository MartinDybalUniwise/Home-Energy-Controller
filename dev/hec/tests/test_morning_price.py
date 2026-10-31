from copy import deepcopy
from datetime import timedelta

from hec.controller.price import build_plan, earliest_quarter
from test_readers_ote_tng import build_tng
from test_tng_price import BASE, DAY, curve


def smaller_morning_peak():
    data = curve()
    for i, period in enumerate(data['periods']):
        period['price_total_czk_kwh'] = (6.7 if i < 28 else 7.8 if i < 36
                                         else 6.9 if i < 64 else 9 if i < 84 else 7)
    return data


def test_expensive_evening_cannot_hide_morning_rise():
    plan = build_plan(smaller_morning_peak(), DAY, {})
    morning = [p for p in plan['phases'] if p['end'] <= 40]
    assert [p['kind'] for p in morning] == ['preheat', 'coast']
    pre, coast = morning
    assert pre['end'] <= coast['start'] <= 28
    assert coast['end'] == 36
    assert coast['end'] - coast['start'] <= 12
    assert pre['end'] - pre['start'] == 8


def test_flat_or_too_small_price_changes_do_not_create_heat_cycles():
    data = curve()
    for i, period in enumerate(data['periods']):
        period['price_total_czk_kwh'] = 7 + (i % 4) * 0.1
    assert not build_plan(data, DAY, {})['phases']


def test_short_valley_does_not_create_overlapping_guards_or_another_preheat():
    data = curve()
    for i, period in enumerate(data['periods']):
        period['price_total_czk_kwh'] = 7.8 if 24 <= i < 28 else 8 if 29 <= i < 32 else 6.7
    phases = build_plan(data, DAY, {})['phases']
    assert [p['kind'] for p in phases] == ['preheat', 'coast']
    assert phases[0]['end'] <= phases[1]['start']
    assert phases[1]['end'] == 32 and phases[1]['end'] - phases[1]['start'] <= 12


def test_almost_equally_cheap_preheat_is_placed_later():
    data = smaller_morning_peak()
    for i in range(12, 28):
        data['periods'][i]['price_total_czk_kwh'] = 6.75
    phases = build_plan(data, DAY, {})['phases']
    pre, coast = phases[:2]
    assert pre['end'] == coast['start']
    assert pre['start'] >= 12  # no needless early-night heating for a 0.05 gap


def test_dhw_and_off_are_not_used_for_preheat_or_coast():
    data = smaller_morning_peak()
    for mode in ('boiler', 'off'):
        assert not build_plan(data, DAY, {'default_mode': mode})['phases']


def test_new_revision_does_not_rewrite_missed_night_into_today(tmp_path, tng_connect):
    _, config, _ = build_tng(tmp_path, tng_connect,
        price_shift={'enabled': True, 'activated_at': '2026-10-29T08:00:00+01:00',
                     'revised_at': DAY + 'T09:10:00+01:00'})
    earliest = earliest_quarter(config, DAY)
    assert earliest == 37
    plan = build_plan(smaller_morning_peak(), DAY, {}, earliest)
    assert all(p['start'] >= earliest for p in plan['phases'])
    assert earliest_quarter(config, '2026-10-31') == 0


def test_higher_absolute_tariff_does_not_hide_material_relative_gap():
    data = smaller_morning_peak()
    scaled = deepcopy(data)
    for period in scaled['periods']:
        period['price_total_czk_kwh'] *= 4
    assert any(p['kind'] == 'coast' and p['end'] <= 40
               for p in build_plan(scaled, DAY, {})['phases'])


def test_midnight_plan_boundary_keeps_tng_scheduler_alive(tmp_path, tng_connect):
    reader, _, _ = build_tng(tmp_path, tng_connect, heating={
        'enabled': True, 'default_temperature': 42, 'schedule': [], 'date_overrides': {
            DAY: {'schedule': [{'from': '22:00', 'to': '24:00', 'temperature': 35}]}}})
    moment = BASE + timedelta(hours=17, minutes=55)
    assert reader._next_boundary_seconds(moment) == 300
    assert reader._next_schedule_target(reader.config.get('tng.heating'), moment) == '00:00->42C'
