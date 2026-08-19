"""Testy predikce. Model musí být vysvětlitelný a nesmí předstírat přesnost."""

from __future__ import annotations

import json
import math
from datetime import timedelta

from hec.controller.predictor import Predictor
from hec.core import config as config_mod
from hec.core import schema
from hec.core.timeutil import now_local, to_iso
from hec.storage.jsonl import JsonlStorage


def make(tmp_path, **sections):
    data = schema.defaults()
    for section, values in sections.items():
        data[section].update(values)
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    return config, JsonlStorage(config.data_dir, config.history_dir)


def seed_summaries(storage, days=30, pv=40.0, irradiation=5.0, house=20.0,
                   heatpump=10.0, degree_days=5.0):
    today = now_local().date()
    for offset in range(1, days + 1):
        day = today - timedelta(days=offset)
        storage.append("summary", {
            "timestamp": to_iso(now_local() - timedelta(days=offset)),
            "source": "summary", "date": day.isoformat(),
            "pv_kwh": pv, "house_kwh": house, "irradiation_kwh_m2": irradiation,
            "heatpump_kwh": heatpump, "degree_days": degree_days,
        })


def write_weather(config, days=3, ghi=300.0, temp=8.0):
    now = now_local()
    hourly = []
    daily = []
    for offset in range(1, days + 1):
        day = (now + timedelta(days=offset)).date()
        for hour in range(6, 18):
            stamp = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=offset)
            hourly.append({"time": to_iso(stamp), "ghi_wm2": ghi, "temp_c": temp,
                           "condition": "clear"})
        daily.append({"date": day.isoformat(), "temp_min_c": temp - 3, "temp_max_c": temp + 3})
    (config.data_dir / "weather.json").write_text(
        json.dumps({"forecast_hourly": hourly, "forecast_daily": daily}), encoding="utf-8")


def write_prices(config, day, cheap_from="02:00"):
    periods = []
    for index in range(96):
        start = f"{index // 4:02d}:{index % 4 * 15:02d}"
        end = f"{(index + 1) // 4 % 24:02d}:{(index + 1) % 4 * 15:02d}"
        cheap_hour = int(cheap_from[:2])
        price = 1.0 if index // 4 in (cheap_hour, cheap_hour + 1) else 5.0
        periods.append({"period": index + 1, "start": start, "end": end,
                        "price_eur_mwh": price * 40, "price_total_czk_kwh": price})
    (config.data_dir / f"ote-{day.isoformat()}.json").write_text(
        json.dumps({"date": day.isoformat(), "eur_czk_rate": 25.0, "periods": periods}),
        encoding="utf-8")


# --- učení ------------------------------------------------------------------

def test_pv_factor_is_learned_from_own_history(tmp_path):
    config, storage = make(tmp_path)
    seed_summaries(storage, days=30, pv=40.0, irradiation=5.0)

    factor, samples = Predictor(config, storage).pv_factor()
    assert factor == 8.0            # 40 kWh na 5 kWh/m2
    assert samples == 30


def test_pv_factor_falls_back_to_installed_power(tmp_path):
    config, storage = make(tmp_path, prediction={"pv_peak_kwp": 12.0})
    factor, samples = Predictor(config, storage).pv_factor()

    assert samples == 0 and factor == 9.0     # 12 kWp × výchozí performance ratio


def test_consumption_uses_matching_day_kind(tmp_path):
    config, storage = make(tmp_path)
    today = now_local().date()
    for offset in range(1, 15):
        day = today - timedelta(days=offset)
        storage.append("summary", {
            "timestamp": to_iso(now_local() - timedelta(days=offset)), "source": "summary",
            "date": day.isoformat(), "house_kwh": 30.0 if day.weekday() >= 5 else 20.0})

    predictor = Predictor(config, storage)
    saturday = next(today + timedelta(days=n) for n in range(1, 8)
                    if (today + timedelta(days=n)).weekday() == 5)
    monday = next(today + timedelta(days=n) for n in range(1, 8)
                  if (today + timedelta(days=n)).weekday() == 0)

    assert predictor.consumption_estimate(saturday)[0] == 30.0
    assert predictor.consumption_estimate(monday)[0] == 20.0


def test_heat_slope_learned_per_degree_day(tmp_path):
    config, storage = make(tmp_path)
    seed_summaries(storage, heatpump=10.0, degree_days=5.0)

    slope, samples = Predictor(config, storage).heat_slope()
    assert slope == 2.0 and samples == 30


def test_confidence_grows_with_learned_days():
    assert Predictor.confidence_for(0) == "low"
    assert Predictor.confidence_for(10) == "medium"
    assert Predictor.confidence_for(30) == "high"


# --- předpověď ---------------------------------------------------------------

def test_forecast_without_weather_is_unavailable(tmp_path):
    config, storage = make(tmp_path)
    result = Predictor(config, storage).forecast()

    assert result["available"] is False
    assert result["reason_key"] == "prediction.not_enough_data"


def test_forecast_produces_range_not_a_single_number(tmp_path):
    config, storage = make(tmp_path)
    seed_summaries(storage, days=30, pv=40.0, irradiation=5.0)
    write_weather(config, ghi=250.0)

    result = Predictor(config, storage).forecast()
    day = result["days"][0]

    # 12 hodin × 250 W/m2 = 3 kWh/m2; × naučený faktor 8 = 24 kWh
    assert day["pv_kwh"] == 24.0
    assert day["pv_kwh_low"] < day["pv_kwh"] < day["pv_kwh_high"]
    assert day["confidence"] == "high"


def test_low_confidence_widens_the_range(tmp_path):
    config, storage = make(tmp_path)
    write_weather(config)

    day = Predictor(config, storage).forecast()["days"][0]
    span = (day["pv_kwh_high"] - day["pv_kwh_low"]) / day["pv_kwh"]
    assert day["confidence"] == "low" and round(span, 2) == 0.70


def test_forecast_includes_heat_demand_and_balance(tmp_path):
    config, storage = make(tmp_path)
    seed_summaries(storage, pv=40.0, irradiation=5.0, house=20.0, heatpump=10.0, degree_days=5.0)
    write_weather(config, ghi=100.0, temp=8.0)          # 12 × 0,1 = 1,2 kWh/m2

    day = Predictor(config, storage).forecast()["days"][0]
    assert day["pv_kwh"] == 9.6
    assert day["heat_kwh"] == 20.0                      # 2 kWh/denostupeň × 10
    assert day["grid_balance_kwh"] == round(20.0 + 20.0 - 9.6, 1)


def test_cost_is_none_without_known_prices(tmp_path):
    config, storage = make(tmp_path)
    write_weather(config)

    day = Predictor(config, storage).forecast()["days"][0]
    assert day["cost_czk"] is None and day["prices_known"] is False


def test_forecast_reports_unknown_consumption_honestly(tmp_path):
    """Bez naučené spotřeby se neukazuje 0 kWh, ale neznámo (nalezeno na ostrém
    provozu: čerstvá instalace zobrazovala 'Expected consumption: 0.0 kWh',
    jako by šlo o reálnou predikci nulové spotřeby)."""
    config, storage = make(tmp_path)
    write_weather(config, ghi=250.0)

    day = Predictor(config, storage).forecast()["days"][0]
    assert day["pv_kwh"] > 0                    # výroba se predikovat dá
    assert day["consumption_kwh"] is None
    assert day["grid_balance_kwh"] is None
    assert day["cost_czk"] is None
    assert day["battery_soc_min_pct"] is None


def test_cost_estimate_never_shows_negative_zero(tmp_path):
    """round(-31.6 * 0.0, 1) je v Pythonu -0.0; v UI by se zobrazilo '-0 Kč'."""
    config, storage = make(tmp_path)
    predictor = Predictor(config, storage)

    cost = predictor._estimate_cost(-31.6, [{"price_total_czk_kwh": 5.0}])
    assert cost == 0.0
    assert math.copysign(1.0, cost) == 1.0


def test_cheapest_window_is_found(tmp_path):
    config, storage = make(tmp_path)
    write_weather(config)
    tomorrow = now_local().date() + timedelta(days=1)
    write_prices(config, tomorrow, cheap_from="02:00")

    day = Predictor(config, storage).forecast()["days"][0]
    assert day["best_appliance_window"].startswith("02:00")
    # Okno pro ohřev vody se hledá jen v denní době, kde levná hodina není.
    assert day["best_dhw_window"] is not None
    assert not day["best_dhw_window"].startswith("02:00")


def test_soc_simulation_stays_within_bounds(tmp_path):
    config, storage = make(tmp_path, prediction={"battery_capacity_kwh": 10.0})
    storage.write_current("goodwe", {"battery_soc": 50})
    predictor = Predictor(config, storage)

    assert predictor._simulate_soc(100.0, 0.0) == 100.0
    assert predictor._simulate_soc(0.0, 100.0) == 10.0


def test_soc_is_not_reported_without_known_capacity(tmp_path):
    config, storage = make(tmp_path, prediction={"battery_capacity_kwh": 0.0})
    assert Predictor(config, storage)._simulate_soc(10.0, 5.0) is None


# --- zpětné vyhodnocení -------------------------------------------------------

def test_accuracy_compares_stored_forecast_with_reality(tmp_path):
    config, storage = make(tmp_path)
    today = now_local().date()
    for offset in range(1, 6):
        day = (today - timedelta(days=offset)).isoformat()
        storage.append("summary", {"timestamp": to_iso(now_local() - timedelta(days=offset)),
                                   "source": "summary", "date": day, "pv_kwh": 20.0})
        storage.append("prediction", {"timestamp": to_iso(now_local() - timedelta(days=offset + 1)),
                                      "source": "prediction", "date": day, "pv_kwh": 25.0})

    accuracy = Predictor(config, storage).accuracy()
    assert accuracy["samples"] == 5
    assert accuracy["pv_mape_pct"] == 25.0            # |20 − 25| / 20


def test_accuracy_is_none_without_pairs(tmp_path):
    config, storage = make(tmp_path)
    assert Predictor(config, storage).accuracy() is None
