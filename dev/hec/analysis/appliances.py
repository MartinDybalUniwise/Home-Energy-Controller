"""Detekce cyklů spotřebičů z výkonového profilu Shelly.

Cíl zadání: rozpoznat začátek, konec, trvání, energii a špičku. Detekce je
záměrně jednoduchá a vysvětlitelná – práh s hysterezí a minimální délkou.
Nic se nespíná, jen měří.
"""

from __future__ import annotations

from datetime import timedelta

from ..core.logging_setup import get_logger
from ..core.timeutil import now_local, parse_iso, to_iso
from ..storage.series import integrate_kwh

DEFAULT_ON_W = 15.0          # nad tímto výkonem považujeme spotřebič za běžící
DEFAULT_OFF_W = 5.0          # pod tímto za vypnutý (hystereze proti blikání)
MIN_MINUTES = 3.0
MAX_GAP_MINUTES = 10.0       # delší mezera v datech cyklus ukončí


class ApplianceAnalyser:
    source = "appliance_cycles"

    def __init__(self, config, storage):
        self.config = config
        self.storage = storage
        self.log = get_logger("appliances")

    def devices(self) -> list[dict]:
        return [d for d in self.config.get("shelly.devices", []) or []
                if d.get("enabled", True) and d.get("role", "appliance") == "appliance"]

    @staticmethod
    def detect(records: list[dict], *, on_w: float = DEFAULT_ON_W, off_w: float = DEFAULT_OFF_W,
               min_minutes: float = MIN_MINUTES, field: str = "power_w") -> list[dict]:
        """Najde cykly v jedné časové řadě."""
        cycles: list[dict] = []
        current: list[dict] = []
        previous_time = None

        def close() -> None:
            if len(current) < 2:
                current.clear()
                return
            start = parse_iso(current[0]["timestamp"])
            end = parse_iso(current[-1]["timestamp"])
            minutes = (end - start).total_seconds() / 60.0
            if minutes < min_minutes:
                current.clear()
                return
            powers = [float(r[field]) for r in current if r.get(field) is not None]
            cycles.append({
                "started": to_iso(start),
                "ended": to_iso(end),
                "duration_min": round(minutes, 1),
                "energy_kwh": integrate_kwh(current, field, max_gap_seconds=int(MAX_GAP_MINUTES * 60)),
                "peak_w": round(max(powers), 1) if powers else None,
                "mean_w": round(sum(powers) / len(powers), 1) if powers else None,
            })
            current.clear()

        for record in records:
            stamp = parse_iso(record.get("timestamp"))
            value = record.get(field)
            if stamp is None or value is None:
                continue
            value = float(value)

            if previous_time is not None and (stamp - previous_time).total_seconds() > MAX_GAP_MINUTES * 60:
                # Výpadek měření: cyklus se uzavře, nedopočítává se přes díru.
                close()
            previous_time = stamp

            if current:
                if value <= off_w:
                    close()
                else:
                    current.append(record)
            elif value >= on_w:
                current.append(record)

        close()
        return cycles

    def analyse_device(self, key: str, days: int = 1) -> list[dict]:
        start = now_local() - timedelta(days=days)
        records = self.storage.query(f"shelly_{key}", start, now_local())
        return self.detect(records)

    def profile(self, cycles: list[dict]) -> dict:
        """Typický cyklus – medián trvání a energie. Podklad pro plánování."""
        if not cycles:
            return {}
        durations = sorted(cycle["duration_min"] for cycle in cycles)
        energies = sorted(cycle["energy_kwh"] for cycle in cycles)
        middle = len(cycles) // 2
        return {
            "count": len(cycles),
            "typical_duration_min": durations[middle],
            "typical_energy_kwh": energies[middle],
            "peak_w": max(cycle["peak_w"] or 0 for cycle in cycles),
        }

    def run(self, days: int = 1) -> list[dict]:
        """Uloží nově dokončené cykly. Rozběhnutý cyklus se ukládá až po dojetí."""
        from ..readers.base import slug
        known = {(entry["device"], entry["started"]) for entry in self.recent(days + 1)}
        stored: list[dict] = []
        for device in self.devices():
            key = slug(device.get("name") or device.get("host"))
            for cycle in self.analyse_device(key, days):
                if (key, cycle["started"]) in known:
                    continue
                record = {"timestamp": cycle["ended"], "source": self.source,
                          "device": key, "name": device.get("name", key), **cycle}
                self.storage.append(self.source, record)
                stored.append(record)
        return stored

    def recent(self, days: int = 7) -> list[dict]:
        start = now_local() - timedelta(days=days)
        return self.storage.query(self.source, start, now_local() + timedelta(minutes=1))
