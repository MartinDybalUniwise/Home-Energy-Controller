"""One price projection for readers, plans and API; OTE market cache stays raw."""

from copy import deepcopy
from datetime import date
from math import isfinite

from ..storage.base import read_json


def priced_day(config, payload):
    tariff = config.get("ote.distribution_tariff", {})
    if not tariff.get("enabled") or not payload:
        return payload
    result = deepcopy(payload)
    day = result.get("date", "")
    rate = result.get("eur_czk_rate")
    try:
        date.fromisoformat(day)
        valid = tariff["valid_from"] <= day <= tariff["valid_to"]
        valid = valid and isinstance(rate, (int, float)) and not isinstance(rate, bool) and isfinite(rate)
        windows = tariff["nt_windows"]
        valid = valid and bool(windows)
        for window in windows:
            for key in ("from", "to"):
                value = window[key]
                hour, minute = map(int, value.split(":"))
                if value != f"{hour:02}:{minute:02}" or not (0 <= hour <= 24 and 0 <= minute < 60):
                    raise ValueError("Invalid tariff clock")
                if hour == 24 and (key != "to" or minute):
                    raise ValueError("Invalid midnight boundary")
            if window["from"] >= window["to"]:
                raise ValueError("Tariff windows must be same-day intervals")
        for key in ("nt_czk_kwh", "vt_czk_kwh"):
            value = tariff[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or not 0 <= value <= 20
            ):
                raise ValueError("Invalid distribution price")
    except (KeyError, TypeError, ValueError):
        valid = False
    result["distribution_pricing"] = {
        **tariff,
        "valid": bool(valid),
        "basis": "spot_plus_distribution_configured_fees_vat",
    }
    for row in result.get("periods", []):
        eur = row.get("price_eur_mwh")
        start = row.get("start", "")
        if not valid or isinstance(eur, bool) or not isinstance(eur, (int, float)) or not isfinite(eur):
            row["price_total_czk_kwh"] = None
            row["distribution_tariff"] = "unknown"
            continue
        # Export clocks and OTE period labels are both Europe/Prague wall time.
        nt = any(w["from"] <= start < w["to"] for w in windows)
        distribution = tariff["nt_czk_kwh" if nt else "vt_czk_kwh"]
        spot = eur * rate / 1000
        row.update(
            price_czk_kwh=round(spot, 4),
            distribution_tariff="NT" if nt else "VT",
            distribution_czk_kwh=distribution,
            price_total_czk_kwh=round(
                (spot + distribution + float(config.get("ote.fees_czk_kwh", 0)))
                * (1 + float(config.get("ote.vat_rate", 0))),
                4,
            ),
        )
    return result


def load_priced_day(config, day):
    return priced_day(config, read_json(config.data_dir / f"ote-{day}.json", {}))
