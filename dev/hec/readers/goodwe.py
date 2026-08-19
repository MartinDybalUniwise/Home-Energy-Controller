"""Reader měniče GoodWe.

Knihovna `goodwe` je volitelná závislost – bez ní reader hlásí chybu a ostatní
zdroje běží dál. Fázové veličiny se u některých firmwarů nevystavují, proto se
každý klíč hledá mezi několika kandidáty a chybějící se prostě nezapíše.
"""

from __future__ import annotations

import asyncio

from .base import BaseReader

# cílový název -> kandidáti na klíč v datech knihovny goodwe
FIELD_MAP: dict[str, tuple[str, ...]] = {
    "pv_w": ("ppv",),
    "pv1_w": ("ppv1",),
    "pv2_w": ("ppv2",),
    "house_w": ("house_consumption",),
    "grid_w": ("active_power", "meter_active_power_total"),
    "battery_w": ("pbattery1", "battery_power"),
    "battery_soc": ("battery_soc",),
    "battery_soh": ("battery_soh",),
    "battery_v": ("vbattery1",),
    "battery_a": ("ibattery1",),
    "battery_temp_c": ("battery_temperature",),
    "battery_charge_limit_a": ("battery_charge_limit",),
    "battery_discharge_limit_a": ("battery_discharge_limit",),
    "e_day_kwh": ("e_day",),
    "e_load_day_kwh": ("e_load_day",),
    "e_import_day_kwh": ("e_day_imp",),
    "e_export_day_kwh": ("e_day_exp",),
    "l1_w": ("active_power_l1", "pgrid", "meter_active_power1"),
    "l2_w": ("active_power_l2", "pgrid2", "meter_active_power2"),
    "l3_w": ("active_power_l3", "pgrid3", "meter_active_power3"),
    "l1_v": ("vgrid", "grid_voltage_l1"),
    "l2_v": ("vgrid2",),
    "l3_v": ("vgrid3",),
    "l1_a": ("igrid",),
    "l2_a": ("igrid2",),
    "l3_a": ("igrid3",),
    "grid_frequency_hz": ("fgrid",),
    "work_mode": ("work_mode_label",),
    "grid_mode": ("grid_in_out_label",),
    "inverter_temp_c": ("temperature",),
}


class GoodWeReader(BaseReader):
    name = "goodwe"

    def __init__(self, config, storage=None, connect=None):
        self._connect = connect       # injektovatelné kvůli testům
        super().__init__(config, storage)

    def _host(self) -> str:
        host = str(self.config.get("goodwe.host", "") or "").strip()
        if not host:
            raise RuntimeError("goodwe.host není nastaven")
        return host

    async def _read_async(self) -> dict:
        connect = self._connect
        if connect is None:
            try:
                import goodwe
            except ImportError as exc:                       # pragma: no cover
                raise RuntimeError("knihovna 'goodwe' není nainstalována") from exc
            connect = goodwe.connect
        inverter = await connect(
            host=self._host(),
            family=self.config.get("goodwe.family") or None,
            timeout=int(self.config.get("goodwe.timeout", 2)),
            retries=int(self.config.get("goodwe.retries", 3)),
        )
        return await inverter.read_runtime_data()

    def read(self) -> dict:
        raw = asyncio.run(self._read_async())
        return self.map_values(raw)

    def map_values(self, raw: dict) -> dict:
        values: dict = {}
        for target, candidates in FIELD_MAP.items():
            for key in candidates:
                if key in raw and raw[key] is not None:
                    values[target] = raw[key]
                    break

        grid = values.get("grid_w")
        if isinstance(grid, (int, float)):
            # Znaménko se u instalací liší, proto je směr konfigurovatelný.
            positive_is_import = bool(self.config.get("goodwe.grid_positive_is_import", True))
            flow = grid if positive_is_import else -grid
            values["grid_import_w"] = max(0.0, flow)
            values["grid_export_w"] = max(0.0, -flow)

        battery = values.get("battery_w")
        if isinstance(battery, (int, float)):
            positive_is_charge = bool(self.config.get("goodwe.battery_positive_is_charge", True))
            flow = battery if positive_is_charge else -battery
            values["battery_charge_w"] = max(0.0, flow)
            values["battery_discharge_w"] = max(0.0, -flow)

        phases = [values.get(f"l{i}_w") for i in (1, 2, 3)]
        if all(isinstance(p, (int, float)) for p in phases):
            values["phase_imbalance_w"] = round(max(phases) - min(phases), 1)
        return values
