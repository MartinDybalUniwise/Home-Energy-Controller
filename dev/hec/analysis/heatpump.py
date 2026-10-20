"""Analýza tepelného čerpadla: příkon vs. stav TNG vs. venkovní teplota.

Vědomě se **nepočítá topný faktor** – bez měření tepelného výkonu by to bylo
vymyšlené číslo. Počítá se to, co je měřitelné: spotřeba, doba běhu a měrná
spotřeba na denostupeň.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from ..core.timeutil import now_local
from ..storage.series import numeric
from .power_quality import consumption_report

RUNNING_W = 200.0             # nad tímto příkonem považujeme čerpadlo za běžící
BASE_TEMPERATURE_C = 18.0     # referenční teplota pro denostupně


class HeatPumpAnalyser:
    def __init__(self, config, storage):
        self.config = config
        self.storage = storage

    def analyse_day(self, day=None) -> dict:
        day = day or (now_local().date() - timedelta(days=1))
        start = datetime.combine(day, time.min).astimezone()
        end = start + timedelta(days=1)

        power_records = self.storage.query("shelly", start, end, end_exclusive=True)
        tng_records = self.storage.query("tng", start, end, end_exclusive=True)

        meter = consumption_report(power_records, "heatpump_power_w", "heatpump_quality")
        meter["coverage_pct"] = round(meter["covered_seconds"] / (end - start).total_seconds() * 100, 1)
        if meter["quality"] == "valid" and meter["coverage_pct"] < 95:
            meter["quality"] = "partial"
        energy = meter["energy_kwh"]
        run_hours = meter["run_hours"]

        outside = [numeric(r.get("outside_temperature")) for r in tng_records]
        outside = [value for value in outside if value is not None]
        mean_outside = round(sum(outside) / len(outside), 1) if outside else None
        degree_days = round(max(0.0, BASE_TEMPERATURE_C - mean_outside), 2) if mean_outside is not None else None

        heating_known = [r for r in tng_records if isinstance(r.get("heating_on"), bool)]
        heating_samples = [r for r in heating_known if r["heating_on"]]
        boiler_temps = [numeric(r.get("boiler_temperature")) for r in tng_records]
        boiler_temps = [value for value in boiler_temps if value is not None]

        return {
            "date": day.isoformat(),
            "energy_kwh": energy,
            "run_hours": run_hours,
            "mean_power_w": round(energy * 1000 / run_hours, 1) if run_hours else None,
            "mean_outside_c": mean_outside,
            "degree_days": degree_days,
            # Měrná spotřeba: kolik kWh spotřebuje čerpadlo na jeden denostupeň.
            "kwh_per_degree_day": round(energy / degree_days, 3) if degree_days and energy is not None else None,
            "heating_share_pct": round(len(heating_samples) / len(heating_known) * 100, 1) if heating_known else None,
            "boiler_min_c": min(boiler_temps) if boiler_temps else None,
            "boiler_max_c": max(boiler_temps) if boiler_temps else None,
            "measured": energy is not None,
            "power_quality": meter,
            "heating_known_samples": len(heating_known),
        }
