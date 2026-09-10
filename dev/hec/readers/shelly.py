"""Reader zařízení Shelly (generace 1 i 2).

Zásada zadání: **nejdřív měřit, automatizovat až potom.** Tento reader nikdy
nespíná – umí pouze číst. Spínání je samostatná funkce pozdější fáze.
"""

from __future__ import annotations

import requests

from ..core.model import Sample
from .base import BaseReader, slug


class ShellyReader(BaseReader):
    name = "shelly"

    def __init__(self, config, storage=None, session=None):
        self.session = session or requests.Session()
        super().__init__(config, storage)

    def devices(self) -> list[dict]:
        return [d for d in self.config.get("shelly.devices", []) or [] if d.get("enabled", True)]

    def _get(self, url: str) -> dict:
        timeout = int(self.config.get("shelly.request_timeout_seconds", 5))
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    # --- převod odpovědí na jednotné veličiny ------------------------------
    @staticmethod
    def parse_gen2(payload: dict, channel: int = 0) -> dict:
        values: dict = {}
        switch = payload.get(f"switch:{channel}")
        if isinstance(switch, dict):
            values["power_w"] = switch.get("apower")
            values["voltage_v"] = switch.get("voltage")
            values["current_a"] = switch.get("current")
            values["on"] = switch.get("output")
            total = (switch.get("aenergy") or {}).get("total")
            if total is not None:
                values["energy_kwh"] = round(float(total) / 1000.0, 4)

        meter = payload.get(f"em:{channel}")
        if isinstance(meter, dict):
            for phase, key in (("l1", "a"), ("l2", "b"), ("l3", "c")):
                values[f"{phase}_w"] = meter.get(f"{key}_act_power")
                values[f"{phase}_v"] = meter.get(f"{key}_voltage")
                values[f"{phase}_a"] = meter.get(f"{key}_current")
            values["power_w"] = meter.get("total_act_power")

        totals = payload.get(f"emdata:{channel}")
        if isinstance(totals, dict) and totals.get("total_act") is not None:
            values["energy_kwh"] = round(float(totals["total_act"]) / 1000.0, 4)

        pm = payload.get(f"pm1:{channel}")
        if isinstance(pm, dict):
            values.setdefault("power_w", pm.get("apower"))
            values.setdefault("voltage_v", pm.get("voltage"))
        return {k: v for k, v in values.items() if v is not None}

    @staticmethod
    def parse_gen1(payload: dict, channel: int = 0) -> dict:
        values: dict = {}
        meters = payload.get("meters") or []
        if channel < len(meters):
            meter = meters[channel]
            values["power_w"] = meter.get("power")
            if meter.get("total") is not None:
                # Gen1 počítá ve watt-minutách.
                values["energy_kwh"] = round(float(meter["total"]) / 60000.0, 4)

        emeters = payload.get("emeters") or []
        for index, emeter in enumerate(emeters[:3]):
            values[f"l{index + 1}_w"] = emeter.get("power")
            values[f"l{index + 1}_v"] = emeter.get("voltage")
        if emeters:
            values["power_w"] = sum(e.get("power") or 0 for e in emeters[:3])

        relays = payload.get("relays") or []
        if channel < len(relays):
            values["on"] = relays[channel].get("ison")
        return {k: v for k, v in values.items() if v is not None}

    def read_device(self, device: dict) -> dict:
        host = str(device.get("host", "")).strip()
        if not host:
            raise RuntimeError("shelly: zařízení bez adresy")
        base = host if host.startswith("http") else f"http://{host}"
        if int(device.get("generation", 2)) >= 2:
            payload = self._get(f"{base}/rpc/Shelly.GetStatus")
            return self.parse_gen2(payload, int(device.get("channel", 0)))
        payload = self._get(f"{base}/status")
        return self.parse_gen1(payload, int(device.get("channel", 0)))

    def read(self) -> dict:
        devices: dict[str, dict] = {}
        errors: dict[str, str] = {}
        for device in self.devices():
            key = slug(device.get("name") or device.get("host"))
            try:
                values = self.read_device(device)
            except Exception as exc:                          # noqa: BLE001
                # Nedostupná zásuvka nesmí zneplatnit měření ostatních.
                errors[key] = f"{type(exc).__name__}: {exc}"
                continue
            values["role"] = device.get("role", "appliance")
            values["appliance_type"] = device.get("appliance_type", "other")
            values["name"] = device.get("name", key)
            devices[key] = values

        if not devices and errors:
            raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))

        heatpump_devices = [v for v in devices.values() if v.get("role") == "heatpump_meter"]
        total = sum(float(v.get("power_w") or 0) for v in devices.values()
                    if v.get("role") != "heatpump_meter")
        # Bez nakonfigurovaného Pro 3EM na TČ je hodnota "neměřeno", ne "0 W" –
        # jinak by UI hlásilo naměřenou nulu u zařízení, které vůbec nesleduje.
        heatpump = (sum(float(v.get("power_w") or 0) for v in heatpump_devices)
                    if heatpump_devices else None)
        return {
            "devices": devices,
            "errors": errors or None,
            "appliances_power_w": round(total, 1),
            "heatpump_power_w": round(heatpump, 1) if heatpump is not None else None,
        }

    def history_targets(self, values: dict, sample: Sample) -> list[tuple[str, dict]]:
        """Každé zařízení má vlastní řadu – grafy spotřebičů se pak čtou přímo."""
        stamp = sample.to_dict()["timestamp"]
        targets: list[tuple[str, dict]] = [(self.name, {
            "timestamp": stamp,
            "source": self.name,
            "appliances_power_w": values.get("appliances_power_w"),
            "heatpump_power_w": values.get("heatpump_power_w"),
        })]
        for key, device in (values.get("devices") or {}).items():
            record = {"timestamp": stamp, "source": f"shelly_{key}"}
            record.update({k: v for k, v in device.items() if k not in ("name",)})
            targets.append((f"shelly_{key}", record))
        return targets
