"""GoodWe FTE reader normalized to the HEC runtime model."""

from __future__ import annotations

from typing import Any

from ..readers.base import BaseReader
from .goodwe_manager import GoodWeManager

FIELD_MAP: dict[str, tuple[str, ...]] = {
    "pv_w": ("ppv", "pv_power"),
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
    "charge_current_limit_a": ("battery_charge_limit",),
    "discharge_current_limit_a": ("battery_discharge_limit",),
    "l1_w": ("active_power_l1", "pgrid", "meter_active_power1"),
    "l2_w": ("active_power_l2", "pgrid2", "meter_active_power2"),
    "l3_w": ("active_power_l3", "pgrid3", "meter_active_power3"),
    "l1_v": ("vgrid", "grid_voltage_l1"),
    "l2_v": ("vgrid2",),
    "l3_v": ("vgrid3",),
    "work_mode": ("work_mode_label",),
    "temperature_c": ("temperature",),
    "inverter_temp_c": ("temperature",),
    "e_day_kwh": ("e_day",),
    "e_load_day_kwh": ("e_load_day",),
    "e_import_day_kwh": ("e_day_imp",),
    "e_export_day_kwh": ("e_day_exp",),
    "l1_a": ("igrid",),
    "l2_a": ("igrid2",),
    "l3_a": ("igrid3",),
    "grid_frequency_hz": ("fgrid",),
    "grid_mode": ("grid_in_out_label",),
}

NORMALIZED_FIELDS = tuple(FIELD_MAP) + (
    "grid_import_w", "grid_export_w", "battery_charge_w", "battery_discharge_w",
    "phase_imbalance_w", "model", "firmware", "work_mode", "control_status",
)


class FTEReader(BaseReader):
    name = "goodwe"

    def __init__(self, config, storage=None, client=None, physical_io=False, test_fake=False):
        self._manager = GoodWeManager(config, storage=storage, client=client,
                                      physical_io=physical_io, test_fake=test_fake)
        super().__init__(config, storage)

    def interval_seconds(self) -> int:
        return int(self.config.get("goodwe.read_interval_seconds", 10))

    @property
    def manager(self) -> GoodWeManager:
        return self._manager

    def read(self) -> dict[str, Any]:
        try:
            raw = self._manager.read_runtime()
            return self.map_values(raw)
        except Exception as exc:  # noqa: BLE001
            values = self._empty_values()
            values.update({"online": False, "source": "goodwe",
                           "error": f"{type(exc).__name__}: {exc}"})
            return values

    def map_values(self, raw: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for target, candidates in FIELD_MAP.items():
            for key in candidates:
                if key in raw and raw[key] is not None:
                    values[target] = raw[key]
                    break
        if "active_power" in raw and raw["active_power"] is not None:
            values["grid_w"] = raw["active_power"]
        if "battery_soc" in raw and raw["battery_soc"] is not None:
            values["battery_soc"] = raw["battery_soc"]
        if isinstance(values.get("grid_w"), (int, float)):
            positive_is_import = bool(self.config.get("goodwe.grid_positive_is_import", True))
            flow = values["grid_w"] if positive_is_import else -values["grid_w"]
            values["grid_import_w"] = max(0.0, flow)
            values["grid_export_w"] = max(0.0, -flow)
        if isinstance(values.get("battery_w"), (int, float)):
            positive_is_charge = bool(self.config.get("goodwe.battery_positive_is_charge", True))
            flow = values["battery_w"] if positive_is_charge else -values["battery_w"]
            values["battery_charge_w"] = max(0.0, flow)
            values["battery_discharge_w"] = max(0.0, -flow)
        phases = [values.get(f"l{i}_w") for i in (1, 2, 3)]
        phase_values = [float(value) for value in phases if isinstance(value, (int, float))]
        if len(phase_values) == 3:
            values["phase_imbalance_w"] = round(max(phase_values) - min(phase_values), 1)
        status = self._manager.status_snapshot()
        values["timestamp"] = status["last_read"]
        values["model"] = status.get("model")
        values["firmware"] = status.get("firmware")
        values["control_status"] = raw.get("work_mode_label")
        for field in NORMALIZED_FIELDS:
            values.setdefault(field, None)
        values["online"] = True
        values["source"] = "goodwe"
        return values

    @staticmethod
    def _empty_values() -> dict[str, Any]:
        values: dict[str, Any] = {field: None for field in NORMALIZED_FIELDS}
        values.update({"timestamp": None, "model": None, "firmware": None,
                       "online": False, "source": "goodwe"})
        return values

    def status_snapshot(self) -> dict[str, Any]:
        base = self._manager.status_snapshot()
        return {
            **base,
            "online": base["connected"],
            "model": base.get("model"),
            "firmware": base.get("firmware"),
            "terminal": "FTEReader active",
        }
