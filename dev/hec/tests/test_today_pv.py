from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from hec.core.config import Config
from hec.forecast.today import today_pv
from hec.readers.tng import effective_schedule, scheduled_value

ZONE = ZoneInfo('Europe/Prague')
NOW = datetime(2026, 10, 28, 12, 30, tzinfo=ZONE)


class Storage:
    def __init__(self, measured=5, stamp=NOW):
        self.record = {'timestamp':stamp.isoformat(), 'e_day_kwh':measured}

    def latest(self, source):
        assert source == 'goodwe'
        return self.record


def weather():
    return {'fetched_at':NOW.isoformat(), 'forecast_daily':[
        {'date':'2026-10-28','sunrise':'2026-10-28T08:00:00+01:00','sunset':'2026-10-28T16:00:00+01:00'}],
        'forecast_hourly':[{'time':NOW.replace(hour=h, minute=0).isoformat(),'ghi_wm2':1000 if h in (12,13,14) else 0} for h in range(8,24)]}


def forecast(storage=None, data=None, moment=NOW):
    return today_pv(storage or Storage(), Config({}), data or weather(), 10, .35, moment)


def test_partial_hour_does_not_double_count_measured_energy():
    result = forecast()
    assert result['pv_measured_kwh'] == 5
    assert result['pv_remaining_kwh'] == 15
    assert result['pv_kwh'] == 20
    assert result['pv_kwh_low'] >= 5


@pytest.mark.parametrize('storage', [Storage(None),Storage(-1),Storage(True),Storage(float('nan')),
                                   Storage(stamp=NOW-timedelta(days=1)),Storage(stamp=NOW-timedelta(minutes=3))])
def test_invalid_or_stale_counter_never_becomes_zero(storage):
    assert forecast(storage)['pv_kwh'] is None


def test_valid_zero_counter_is_retained():
    result = forecast(Storage(0))
    assert result['pv_measured_kwh'] == 0 and result['pv_kwh'] == 15


def test_missing_daylight_forecast_is_unknown():
    data = weather()
    data['forecast_hourly'] = [r for r in data['forecast_hourly'] if 'T14:' not in r['time']]
    assert forecast(data=data)['pv_kwh'] is None


def test_duplicate_weather_interval_not_added_twice():
    data = weather()
    data['forecast_hourly'].append(data['forecast_hourly'][6])
    assert forecast(data=data)['pv_kwh'] == 20


def test_after_sunset_total_equals_measured():
    moment = NOW.replace(hour=20)
    data = weather()
    data['fetched_at'] = moment.isoformat()
    result = forecast(Storage(25,moment),data,moment)
    assert result['pv_kwh'] == 25 and result['pv_remaining_kwh'] == 0


def test_stale_weather_not_used():
    data = weather()
    data['fetched_at'] = (NOW-timedelta(hours=1)).isoformat()
    assert forecast(data=data)['pv_kwh'] is None


def test_date_override_expires_without_replacing_normal_schedule():
    section = {'default_temperature':42,'schedule':[{'from':'12:00','to':'13:00','temperature':45}],
               'date_overrides':{'2026-10-28':{'default_temperature':38,'schedule':[]}}}
    assert scheduled_value(section,NOW) == 38
    assert scheduled_value(section,NOW+timedelta(days=1)) == 45
    assert effective_schedule(section,NOW)['schedule'] == []
    assert section['default_temperature'] == 42


@pytest.mark.parametrize('date', ['2026-03-29', '2026-10-25'])
def test_partial_hour_on_clock_change_days(date):
    moment = datetime.fromisoformat(date).replace(hour=12, minute=30, tzinfo=ZONE)
    data = weather()
    data['fetched_at'] = moment.isoformat()
    data['forecast_daily'] = [{'date':date,
        'sunrise':moment.replace(hour=8,minute=0).isoformat(),
        'sunset':moment.replace(hour=16,minute=0).isoformat()}]
    data['forecast_hourly'] = [{'time':moment.replace(hour=h,minute=0).isoformat(),
                              'ghi_wm2':1000 if h in (12,13,14) else 0} for h in range(8,24)]
    assert forecast(Storage(5,moment),data,moment)['pv_kwh'] == 20
