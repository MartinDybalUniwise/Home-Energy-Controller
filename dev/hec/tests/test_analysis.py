"""Testy analytické vrstvy: bilance, cykly spotřebičů, fáze, tepelné čerpadlo."""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta

from hec.analysis.appliances import ApplianceAnalyser
from hec.analysis.heatpump import HeatPumpAnalyser
from hec.analysis.phases import PhaseAnalyser
from hec.analysis.summaries import Summaries
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


def yesterday_start():
    return datetime.combine(now_local().date() - timedelta(days=1), time.min).astimezone()


def seed_day(storage, source, values, *, step=60, count=1440, start=None):
    base = start or yesterday_start()
    for index in range(count):
        record = {"timestamp": to_iso(base + timedelta(seconds=index * step)), "source": source}
        record.update(values(index) if callable(values) else values)
        storage.append(source, record)


# --- denní bilance ----------------------------------------------------------

def test_summary_integrates_energy_and_shares(tmp_path):
    config, storage = make(tmp_path)
    # Celý den konstantní: 2 kW výroba, 1 kW spotřeba, 1 kW dodávka do sítě.
    seed_day(storage, "goodwe", {"pv_w": 2000, "house_w": 1000, "grid_export_w": 1000,
                                 "grid_import_w": 0})
    summary = Summaries(config, storage).compute()

    assert round(summary["pv_kwh"]) == 48                # 2 kW × 24 h
    assert round(summary["house_kwh"]) == 24
    assert summary["self_consumption_pct"] == 50.0
    assert summary["self_sufficiency_pct"] == 100.0


def test_summary_prices_import_by_quarter(tmp_path):
    config, storage = make(tmp_path)
    day = (now_local().date() - timedelta(days=1)).isoformat()
    periods = [{"period": i + 1, "start": f"{i // 4:02d}:{i % 4 * 15:02d}",
                "end": "23:59", "price_eur_mwh": 100.0, "price_total_czk_kwh": 4.0}
               for i in range(96)]
    (config.data_dir / f"ote-{day}.json").write_text(
        json.dumps({"date": day, "eur_czk_rate": 25.0, "periods": periods}), encoding="utf-8")

    seed_day(storage, "goodwe", {"grid_import_w": 1000, "pv_w": 0, "house_w": 1000})
    summary = Summaries(config, storage).compute()

    # 24 kWh × 4 Kč = 96 Kč (drobná odchylka z okrajů intervalů je v pořádku)
    assert 90 <= summary["cost_czk"] <= 100
    assert summary["priced"] is True


def test_summary_without_prices_does_not_invent_cost(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"grid_import_w": 1000})
    summary = Summaries(config, storage).compute()

    assert summary["cost_czk"] == 0.0 and summary["priced"] is False


def test_recent_keeps_one_entry_per_day(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"pv_w": 1000})
    analyser = Summaries(config, storage)

    analyser.store(analyser.compute())
    analyser.store(analyser.compute())          # přepočet téhož dne
    assert len(analyser.recent(7)) == 1


def test_run_for_missing_skips_days_without_data(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"pv_w": 1000})
    created = Summaries(config, storage).run_for_missing(7)

    assert len(created) == 1                     # jen den, pro který jsou vzorky


# --- cykly spotřebičů --------------------------------------------------------

def build_cycle(start, minutes, watts, step=60):
    return [{"timestamp": to_iso(start + timedelta(seconds=i * step)), "power_w": watts}
            for i in range(minutes)]


def test_detect_finds_cycle_between_idle_periods():
    base = yesterday_start()
    records = ([{"timestamp": to_iso(base), "power_w": 1.0}]
               + build_cycle(base + timedelta(minutes=1), 60, 2000)
               + [{"timestamp": to_iso(base + timedelta(minutes=62)), "power_w": 0.5}])

    cycles = ApplianceAnalyser.detect(records)
    assert len(cycles) == 1
    assert cycles[0]["duration_min"] == 59.0
    assert cycles[0]["peak_w"] == 2000.0
    assert 1.9 < cycles[0]["energy_kwh"] < 2.1


def test_detect_ignores_short_blips():
    base = yesterday_start()
    records = build_cycle(base, 2, 2000) + [{"timestamp": to_iso(base + timedelta(minutes=3)), "power_w": 0}]
    assert ApplianceAnalyser.detect(records) == []


def test_detect_uses_hysteresis_for_standby():
    """Spotřebič v pohotovosti (8 W) cyklus neukončí ani nezaloží."""
    base = yesterday_start()
    records = (build_cycle(base, 30, 2000)
               + build_cycle(base + timedelta(minutes=30), 10, 8.0)
               + build_cycle(base + timedelta(minutes=40), 30, 2000)
               + [{"timestamp": to_iso(base + timedelta(minutes=71)), "power_w": 0}])

    cycles = ApplianceAnalyser.detect(records)
    assert len(cycles) == 1 and cycles[0]["duration_min"] > 60


def test_detect_closes_cycle_on_measurement_gap():
    base = yesterday_start()
    records = build_cycle(base, 20, 2000) + build_cycle(base + timedelta(minutes=45), 20, 2000)
    assert len(ApplianceAnalyser.detect(records)) == 2


def test_profile_reports_typical_cycle():
    base = yesterday_start()
    cycles = ApplianceAnalyser.detect(build_cycle(base, 60, 2000)
                                      + [{"timestamp": to_iso(base + timedelta(minutes=61)), "power_w": 0}])
    profile = ApplianceAnalyser({}, None).profile(cycles)
    assert profile["count"] == 1 and profile["peak_w"] == 2000.0


def test_run_stores_new_cycles_only(tmp_path):
    config, storage = make(tmp_path, shelly={"enabled": True, "devices": [
        {"name": "Myčka", "host": "10.0.0.5", "role": "appliance", "generation": 2,
         "channel": 0, "enabled": True}]})
    base = now_local() - timedelta(hours=3)
    for record in (build_cycle(base, 60, 2000)
                   + [{"timestamp": to_iso(base + timedelta(minutes=61)), "power_w": 0}]):
        storage.append("shelly_mycka", {**record, "source": "shelly_mycka"})

    analyser = ApplianceAnalyser(config, storage)
    assert len(analyser.run(2)) == 1
    assert analyser.run(2) == []                 # podruhé už nic nového


# --- fáze --------------------------------------------------------------------

def test_phase_analysis_reports_missing_data(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"pv_w": 1000}, count=10, start=now_local() - timedelta(hours=1))
    result = PhaseAnalyser(config, storage).analyse()

    assert result["available"] is False
    assert result["reason_key"] == "analysis.phases_unavailable"


def test_phase_analysis_recommends_rebalancing(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"l1_w": 5200, "l2_w": 800, "l3_w": 700},
             count=60, start=now_local() - timedelta(hours=1))
    result = PhaseAnalyser(config, storage).analyse()

    assert result["available"] is True
    assert result["recommendations"][0]["reason_key"] == "analysis.phase_imbalance"
    assert result["recommendations"][0]["reason_params"]["high"] == "L1"


def test_balanced_phases_produce_no_recommendation(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"l1_w": 1200, "l2_w": 1100, "l3_w": 1000},
             count=60, start=now_local() - timedelta(hours=1))
    assert PhaseAnalyser(config, storage).analyse()["recommendations"] == []


# --- tepelné čerpadlo ---------------------------------------------------------

def test_heatpump_analysis_reports_measurable_values_only(tmp_path):
    config, storage = make(tmp_path)
    seed_day(storage, "shelly", {"heatpump_power_w": 1500})
    seed_day(storage, "tng", {"outside_temperature": 8.0, "heating_on": True}, step=300, count=288)

    result = HeatPumpAnalyser(config, storage).analyse_day()
    assert round(result["energy_kwh"]) == 36            # 1,5 kW × 24 h
    assert result["degree_days"] == 10.0                # 18 °C − 8 °C
    assert result["kwh_per_degree_day"] == round(result["energy_kwh"] / 10.0, 3)
    # Topný faktor se nepočítá – bez měření tepla by to bylo vymyšlené číslo.
    assert "cop" not in result


def test_heatpump_analysis_without_meter_says_so(tmp_path):
    config, storage = make(tmp_path)
    result = HeatPumpAnalyser(config, storage).analyse_day()
    assert result["measured"] is False and result["energy_kwh"] == 0.0


# --- údržba -------------------------------------------------------------------

def test_maintenance_runs_all_steps_and_survives_a_failing_one(tmp_path, monkeypatch):
    from hec.core.maintenance import Maintenance
    config, storage = make(tmp_path)
    seed_day(storage, "goodwe", {"pv_w": 1000})
    maintenance = Maintenance(config, storage)
    monkeypatch.setattr(maintenance.appliances, "run",
                        lambda days=1: (_ for _ in ()).throw(RuntimeError("rozbité")))

    result = maintenance.run_once()
    assert result["summaries"] >= 1          # bilance se spočítala i přes chybu jiného kroku
    assert result["archive"]["enabled"] is False
