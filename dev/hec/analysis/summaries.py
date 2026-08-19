"""Denní energetická bilance.

Počítá se z uložené historie, ne z běhových proměnných – po restartu i po
zpětné opravě dat vyjde stejné číslo.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..core.logging_setup import get_logger
from ..core.timeutil import now_local, to_iso
from ..storage.base import read_json
from ..storage.series import downsample, integrate_kwh

QUARTER = 900


class Summaries:
    source = "summary"

    def __init__(self, config, storage):
        self.config = config
        self.storage = storage
        self.log = get_logger("summaries")

    # --- ceny ---------------------------------------------------------------
    def _price_table(self, day: date) -> dict[str, float]:
        """Mapa `HH:MM` → konečná cena za kWh pro daný den."""
        payload = read_json(self.config.data_dir / f"ote-{day.isoformat()}.json")
        table: dict[str, float] = {}
        for period in (payload or {}).get("periods", []):
            price = period.get("price_total_czk_kwh")
            if price is None and period.get("price_eur_mwh") is not None:
                price = period["price_eur_mwh"] * float(payload.get("eur_czk_rate", 25.0)) / 1000.0
            if price is not None:
                table[period["start"]] = float(price)
        return table

    @staticmethod
    def _quarter_key(stamp: str) -> str:
        moment = datetime.fromisoformat(stamp)
        return f"{moment.hour:02d}:{moment.minute // 15 * 15:02d}"

    def _cost(self, records: list[dict], field: str, prices: dict[str, float]) -> float:
        """Náklad z čtvrthodinových košů. Bez ceníku se nic nedopočítává."""
        if not prices:
            return 0.0
        total = 0.0
        for row in downsample(records, [field], QUARTER, how="mean"):
            watts = row.get(field)
            price = prices.get(self._quarter_key(row["timestamp"]))
            if watts is None or price is None:
                continue
            total += watts * 0.25 / 1000.0 * price
        return round(total, 2)

    # --- výpočet ------------------------------------------------------------
    def compute(self, day: date | None = None) -> dict:
        day = day or (now_local().date() - timedelta(days=1))
        start = datetime.combine(day, time.min).astimezone()
        end = start + timedelta(days=1)

        goodwe = self.storage.query("goodwe", start, end, end_exclusive=True)
        shelly = self.storage.query("shelly", start, end, end_exclusive=True)
        prices = self._price_table(day)

        pv = integrate_kwh(goodwe, "pv_w")
        house = integrate_kwh(goodwe, "house_w")
        grid_import = integrate_kwh(goodwe, "grid_import_w")
        grid_export = integrate_kwh(goodwe, "grid_export_w")
        charge = integrate_kwh(goodwe, "battery_charge_w")
        discharge = integrate_kwh(goodwe, "battery_discharge_w")
        heatpump = integrate_kwh(shelly, "heatpump_power_w")
        appliances = integrate_kwh(shelly, "appliances_power_w")

        cost = self._cost(goodwe, "grid_import_w", prices)
        export_price = float(self.config.get("ote.export_price_czk_kwh", 0.0))
        revenue = round(grid_export * export_price, 2)

        return {
            "timestamp": to_iso(start),
            "source": self.source,
            "date": day.isoformat(),
            "samples": len(goodwe),
            "pv_kwh": pv,
            "house_kwh": house,
            "grid_import_kwh": grid_import,
            "grid_export_kwh": grid_export,
            "battery_charge_kwh": charge,
            "battery_discharge_kwh": discharge,
            "heatpump_kwh": heatpump,
            "appliances_kwh": appliances,
            # Kolik z vlastní výroby zůstalo doma.
            "self_consumption_pct": round((pv - grid_export) / pv * 100, 1) if pv > 0 else None,
            # Kolik ze spotřeby domu pokryla vlastní výroba a baterie.
            "self_sufficiency_pct": round((house - grid_import) / house * 100, 1) if house > 0 else None,
            "cost_czk": cost,
            "revenue_czk": revenue,
            "balance_czk": round(revenue - cost, 2),
            "priced": bool(prices),
        }

    def store(self, summary: dict) -> None:
        self.storage.append(self.source, summary)

    def run_for_missing(self, days: int = 7) -> list[dict]:
        """Dopočítá chybějící dny – po výpadku systému historie nezůstane bez bilance."""
        known = {entry["date"] for entry in self.recent(days + 1)}
        created = []
        today = now_local().date()
        for offset in range(1, days + 1):
            day = today - timedelta(days=offset)
            if day.isoformat() in known:
                continue
            summary = self.compute(day)
            if summary["samples"]:
                self.store(summary)
                created.append(summary)
        return created

    def recent(self, days: int = 30) -> list[dict]:
        """Poslední bilance, jedna na den (opakovaný výpočet přepisuje starší)."""
        start = now_local() - timedelta(days=days + 1)
        by_date: dict[str, dict] = {}
        for entry in self.storage.query(self.source, start, now_local() + timedelta(days=1)):
            if entry.get("date"):
                by_date[entry["date"]] = entry
        return [by_date[key] for key in sorted(by_date)]
