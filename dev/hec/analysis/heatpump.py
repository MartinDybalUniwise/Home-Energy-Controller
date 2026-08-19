"""Analýza tepelného čerpadla: příkon vs. stav TNG vs. venkovní teplota.

Vědomě se **nepočítá topný faktor** – bez měření tepelného výkonu by to bylo
vymyšlené číslo. Počítá se to, co je měřitelné: spotřeba, doba běhu a měrná
spotřeba na denostupeň.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from ..core.timeutil import now_local, parse_iso
from ..storage.series import integrate_kwh, numeric

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

        energy = integrate_kwh(power_records, "heatpump_power_w")
        running = [r for r in power_records
                   if (numeric(r.get("heatpump_power_w")) or 0) >= RUNNING_W]
        run_hours = self._running_hours(running)

        outside = [numeric(r.get("outside_temperature")) for r in tng_records]
        outside = [value for value in outside if value is not None]
        mean_outside = round(sum(outside) / len(outside), 1) if outside else None
        degree_days = round(max(0.0, BASE_TEMPERATURE_C - mean_outside), 2) if mean_outside is not None else None

        heating_samples = [r for r in tng_records if r.get("heating_on")]
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
            "kwh_per_degree_day": round(energy / degree_days, 3) if degree_days else None,
            "heating_share_pct": round(len(heating_samples) / len(tng_records) * 100, 1) if tng_records else None,
            "boiler_min_c": min(boiler_temps) if boiler_temps else None,
            "boiler_max_c": max(boiler_temps) if boiler_temps else None,
            "measured": bool(power_records) and energy > 0,
        }

    @staticmethod
    def _running_hours(records: list[dict], max_gap_seconds: int = 900) -> float:
        """Doba běhu ze vzorků nad prahem; mezera v datech se nezapočítává."""
        total = 0.0
        previous = None
        for record in records:
            stamp = parse_iso(record.get("timestamp"))
            if stamp is None:
                continue
            if previous is not None:
                gap = (stamp - previous).total_seconds()
                if 0 < gap <= max_gap_seconds:
                    total += gap
            previous = stamp
        return round(total / 3600.0, 2)
