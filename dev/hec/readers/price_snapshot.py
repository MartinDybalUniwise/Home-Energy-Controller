"""Project the current quarter from the dated cache without network requests."""

from math import isfinite

from ..core.timeutil import now_local, to_iso
from ..storage.base import read_json
from ..storage.series import numeric


def _price(value):
    value = numeric(value)
    return value if value is not None and isfinite(value) else None


def cached_price_snapshot(config, previous: dict, moment=None) -> dict:
    moment = moment or now_local()
    day = moment.date().isoformat()
    payload = read_json(config.data_dir / f"ote-{day}.json", None)
    payload = payload if isinstance(payload, dict) else {}
    clock = moment.strftime("%H:%M")
    periods = payload.get("periods", []) if payload.get("date") == day else []
    periods = [p for p in periods if isinstance(p, dict)] if isinstance(periods, list) else []
    period = next((p for p in periods if p.get("start", "99:99") <= clock
                   < p.get("end", "00:00")), {})
    result = dict(previous)
    result.update(date=day, period_start=period.get("start"), period_end=period.get("end"),
                  price_valid_at=to_iso(moment),
                  price_valid=_price(period.get("price_total_czk_kwh")) is not None)
    for field in ("price_eur_mwh", "price_czk_kwh", "price_total_czk_kwh"):
        result[field] = _price(period.get(field))
    prices = [_price(p.get("price_total_czk_kwh")) for p in periods]
    prices = [p for p in prices if p is not None]
    result.update(min_today_czk_kwh=min(prices) if prices else None,
                  max_today_czk_kwh=max(prices) if prices else None,
                  avg_today_czk_kwh=round(sum(prices) / len(prices), 4) if prices else None)
    return result
