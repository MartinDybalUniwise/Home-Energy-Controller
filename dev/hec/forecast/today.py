"""Today's measured PV counter plus the remaining Open-Meteo irradiation."""
from datetime import UTC, datetime, time, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from ..core.timeutil import parse_iso, to_iso


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0 else None


def today_pv(storage, config, weather, factor, band, moment):
    zone = ZoneInfo(config.get('system.timezone', 'Europe/Prague'))
    local = moment.astimezone(zone)
    day_start = datetime.combine(local.date(), time.min, tzinfo=zone)
    day_end = datetime.combine(local.date() + timedelta(days=1), time.min, tzinfo=zone)
    raw = storage.latest('goodwe') or {}
    values = raw.get('values', raw)
    stamp = parse_iso(raw.get('timestamp'))
    measured = number(values.get('e_day_kwh'))
    fetched = parse_iso(weather.get('fetched_at'))
    if (stamp is None or stamp.astimezone(zone).date() != local.date()
            or not 0 <= (moment - stamp).total_seconds() <= 120):
        measured = None
    if fetched is None or not 0 <= (moment - fetched).total_seconds() <= 2700:
        measured = None
    anchor = stamp if measured is not None else moment
    remaining = 0.0
    intervals = []
    seen = set()
    for row in weather.get('forecast_hourly', []):
        end = parse_iso(row.get('time'))
        ghi = number(row.get('ghi_wm2'))
        if end is None or ghi is None:
            continue
        # Open-Meteo shortwave radiation is the mean of the PRECEDING hour.
        end = end.astimezone(UTC)
        start = end - timedelta(hours=1)
        if end in seen:
            continue
        seen.add(end)
        lo = max(start, anchor.astimezone(UTC), day_start.astimezone(UTC))
        hi = min(end, day_end.astimezone(UTC))
        if hi <= lo:
            continue
        intervals.append((lo, hi))
        remaining += ghi / 1000 * (hi - lo).total_seconds() / 3600
    # Missing daytime weather is unknown, not zero. Night gaps are harmless.
    daily = next((r for r in weather.get('forecast_daily', []) if r.get('date') == local.date().isoformat()), {})
    sunrise, sunset = parse_iso(daily.get('sunrise')), parse_iso(daily.get('sunset'))
    covered = sunrise is not None and sunset is not None
    if covered:
        cursor = max(anchor.astimezone(UTC), sunrise.astimezone(UTC))
        finish = sunset.astimezone(UTC)
        for lo, hi in sorted(set(intervals)):
            if hi <= cursor:
                continue
            if lo > cursor and cursor < finish:
                covered = False
                break
            cursor = max(cursor, hi)
        covered = covered and cursor >= finish
    remaining = remaining * factor if covered else None
    total = measured + remaining if measured is not None and remaining is not None else None
    return {
        'pv_kwh': round(total, 1) if total is not None else None,
        'pv_kwh_low': round(measured + remaining * (1 - band), 1) if total is not None else None,
        'pv_kwh_high': round(measured + remaining * (1 + band), 1) if total is not None else None,
        'pv_measured_kwh': measured,
        'pv_remaining_kwh': round(remaining, 2) if remaining is not None else None,
        'measurement_at': to_iso(stamp) if stamp is not None else None,
        'generated_at': to_iso(moment),
        'weather_at': weather.get('fetched_at'),
        'irradiation_kwh_m2': round(remaining / factor, 3) if remaining is not None and factor else None,
        'estimate_kind': 'measured_plus_remaining',
    }
