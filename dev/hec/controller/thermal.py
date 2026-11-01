"""Single resolver for space heating, DHW, room comfort and economic targets.

The TNG adapter owns device acknowledgement/state persistence, never policy.
"""

from ..core.timeutil import to_iso
from .comfort import evaluate_comfort
from .price import evaluate_shift, refresh_plans
from .response import observe_response, planning_preheat_quarters, preheat_quarters
from .schedules import scheduled_operation, scheduled_value


class ThermalPlanner:
    def prepare_tng(self, reader, state, moment):
        config = reader.config
        heatpump = state.get("heatpump") or {}
        settings = state.get("settings") or {}
        heating = config.get("tng.heating", {})
        thermostat = config.get("tng.thermostat", {})
        boiler = config.get("tng.boiler", {})
        try:
            observe_response(config, state, moment)
            plans = refresh_plans(config, moment)
        except Exception as exc:  # storage failure must not disable comfort protection
            reader.log.warning("price_plan_failed | error=%s", type(exc).__name__)
            plans = []
        for plan in plans:
            reader._command_audit(
                {"timestamp": to_iso(moment), "source": "tng_commands", "phase": "price_plan_saved", **plan},
                publish=False,
            )
        mode = scheduled_operation(config.get("tng.operation", {}), moment)
        observed = evaluate_comfort(
            reader.comfort_state, heatpump, moment, settings.get("heating_on") is True
        )
        if observed != reader.comfort_state:
            was_active = bool(reader.comfort_state.get("active"))
            reader.comfort_state = observed
            reader._save_state()
            if was_active != bool(observed.get("active")):
                reader._command_audit(
                    {
                        "timestamp": to_iso(moment),
                        "source": "tng_commands",
                        "phase": "comfort_guard",
                        "active": bool(observed.get("active")),
                        "room_temperature": heatpump.get("room_temperature"),
                    },
                    publish=False,
                )
        comfort = bool(observed.get("active")) and bool(heating.get("enabled"))
        if comfort and mode == "boiler":
            mode = "heating"
        shift, saved = evaluate_shift(
            config,
            heatpump,
            moment,
            reader.price_shift_state,
            comfort,
            mode,
            reader.storage.latest("goodwe") if reader.storage else None,
        )
        if saved != reader.price_shift_state:
            reader.price_shift_state = saved
            reader._save_state()
        if shift != reader.price_shift_status:
            reader.price_shift_status = shift
            if shift is not None:
                reader._command_audit(
                    {
                        "timestamp": to_iso(moment),
                        "source": "tng_commands",
                        "phase": "price_shift",
                        "effective": shift,
                    },
                    publish=False,
                )
        water = shift["heating_temperature"] if shift else scheduled_value(heating, moment)
        room = shift["room_target"] if shift else scheduled_value(thermostat, moment)
        if comfort and mode == "heating":
            water = 42
            if room is not None:
                room = max(21.5, room)
        return {
            "mode": mode,
            "heating_temperature": water,
            "boiler_temperature": scheduled_value(boiler, moment),
            "room_target": room,
            "phase": (shift or {}).get("phase", "comfort_guard" if comfort else "schedule"),
            "planned_at": to_iso(moment),
            "required_preheat_minutes": planning_preheat_quarters(config, moment.date().isoformat(), moment) * 15,
            "response_required_preheat_minutes": preheat_quarters(config, moment) * 15,
            "room_ready_for_coast": isinstance(heatpump.get("room_temperature"), (int, float))
            and heatpump["room_temperature"] >= 21.5,
        }
