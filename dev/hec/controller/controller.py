"""Řídicí vrstva.

Pořadí je dané zadáním: **bezpečnost → komfort → optimalizace.** Při zastaralých
datech se optimalizace zastaví (safe mode), poslední bezpečné nastavení zůstane
a příkazy se neopakují. Sběr dat běží dál.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from ..core.logging_setup import event, get_logger, warn_event
from ..core.model import Decision
from ..core.timeutil import now_local, to_iso
from ..storage.base import read_json
from .battery import BatteryPlanner
from .rules import Context, default_rules
from .thermal import ThermalPlanner

CRITICAL_SOURCES = ("goodwe", "tng", "ote")
GOODWE_ACTIONS = {
    "set_export_limit_enabled", "set_export_limit_w", "set_on_grid_soc_limit_pct",
    "start_battery_charge", "start_battery_discharge", "stop_battery_control",
}
GOODWE_BATTERY_ACTIONS = {
    "start_battery_charge", "start_battery_discharge", "stop_battery_control",
}


class Controller:
    source = "controller"
    central_controller = True

    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.storage = app.storage
        self.log = get_logger("controller")
        self.rules = sorted((rule for rule in default_rules(self.config)
                             if rule.action in GOODWE_ACTIONS), key=lambda rule: rule.priority)
        self.thermal = ThermalPlanner()
        self.battery = BatteryPlanner(self.config)
        self.thermal_plan = None
        self._last_thermal_run = None
        self._last_thermal_signature = None
        self.last_decision: Decision | None = None
        self.safe_mode_reason: dict | None = None
        self._lock = threading.RLock()
        self._last_run: datetime | None = None
        self._applied: dict[str, object] = {}

    # --- stav ---------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return bool(self.config.get("controller.enabled", False))

    def max_data_age(self, source: str) -> float:
        """Return the configured freshness limit for one critical source."""
        fallback = float(self.config.get("controller.max_data_age_seconds", 300))
        override = self.config.get(f"controller.max_data_age_by_source.{source}")
        return float(override) if isinstance(override, (int, float)) and override >= 60 else fallback

    def stale_sources(self) -> list[str]:
        """Kritické zdroje, které nedávají čerstvá data."""
        stale = []
        for reader in self.app.readers:
            if reader.name not in CRITICAL_SOURCES or not reader.status.enabled:
                continue
            age = reader.status.age
            snapshot = self.app.snapshot.get(reader.name, {})
            if age is None or age > self.max_data_age(reader.name) or snapshot.get("online") is False:
                stale.append(reader.name)
        return stale

    def state(self) -> dict:
        thermal_limited = (self.thermal_plan or {}).get('phase') in (
            'stale_room', 'stale_energy', 'invalid_prices')
        return {
            "enabled": self.enabled,
            "safe_mode": bool(self.safe_mode_reason) or not self.enabled or thermal_limited,
            "safe_mode_reason": self.safe_mode_reason,
            "write_enabled": self.enabled and bool(self.config.get("tng.write_enabled", False)),
            "rules": [{"name": "unified_thermal", "priority": -1, "enabled": self.enabled}]
                      + [{"name": "battery_economic", "priority": 0, "enabled": self.enabled and bool(
                          self.config.get('controller.optimization.goodwe_control.enabled', False)) and bool(
                          self.config.get('controller.optimization.goodwe_control.economic.enabled', False))}]
                      + [{"name": rule.name, "priority": rule.priority,
                          "enabled": rule.enabled and bool(self.config.get(
                              'controller.optimization.goodwe_control.enabled', False)) and not self.config.get(
                              'controller.optimization.goodwe_control.economic.enabled', False)}
                         for rule in self.rules],
            "last_decision": self.last_decision.to_dict() if self.last_decision else None,
            "last_run": to_iso(max(filter(None, (self._last_run, self._last_thermal_run)), default=None)),
            "planner": "unified",
            "thermal_plan": self.thermal_plan,
            "battery_plan": self.battery.state,
            "tng_write_enabled": self.enabled and bool(self.config.get('tng.write_enabled', False)),
            "goodwe_control_enabled": self.enabled and bool(self.config.get(
                'controller.optimization.goodwe_control.enabled', False)),
        }

    def prepare_tng(self, reader, state, moment):
        """The only production authority for thermal targets; the reader executes."""
        with self._lock:
            if not self.enabled:
                return None
            plan = self.thermal.prepare_tng(reader, state, moment)
            self.thermal_plan = plan
            self._last_thermal_run = moment
            signature = tuple(plan[key] for key in
                              ('mode', 'heating_temperature', 'boiler_temperature', 'room_target', 'phase'))
            if signature != self._last_thermal_signature:
                decision = Decision(rule='unified_thermal', action='plan_tng', value=dict(plan),
                                    reason_key='reason.unified_thermal', timestamp=moment)
                try:
                    self.record(decision)
                except OSError as exc:
                    self.log.warning('decision_audit_failed | error=%s', type(exc).__name__)
                self._last_thermal_signature = signature
            return plan

    # --- rozhodování ---------------------------------------------------------
    def build_context(self) -> Context:
        prices = (read_json(self.config.data_dir / f"ote-{now_local().date().isoformat()}.json")
                  or {}).get("periods", [])
        forecast = {}
        predictor = getattr(self.app, "predictor", None)
        if predictor is not None:
            try:
                forecast = predictor.forecast(days=1)
            except Exception as exc:                      # noqa: BLE001
                self.log.warning("forecast_failed | error=%s", type(exc).__name__)
        return Context(
            now=datetime.now(),
            values=self.app.snapshot,
            prices=prices,
            forecast=forecast,
            comfort=self.config.get("controller.comfort", {}),
            optimization=self.config.get("controller.optimization", {}),
        )

    def decide(self, context: Context) -> list[Decision]:
        """První pravidlo pro danou akci vyhrává – priorita je pořadí v seznamu."""
        decisions: list[Decision] = []
        taken: set[str] = set()
        battery_mode_taken = False
        for rule in self.rules:
            if rule.action not in GOODWE_ACTIONS:
                continue  # retired thermal rules cannot become a competing writer
            if rule.action in taken or (rule.action in GOODWE_BATTERY_ACTIONS and battery_mode_taken):
                continue
            decision = rule(context)
            if decision is None:
                continue
            decisions.append(decision)
            taken.add(rule.action)
            if rule.action in GOODWE_BATTERY_ACTIONS:
                battery_mode_taken = True
        return decisions

    # --- provedení -------------------------------------------------------------
    @staticmethod
    def _goodwe_command_key(decision: Decision) -> tuple:
        """Return only physical target fields, excluding changing reasons/telemetry."""
        params = decision.reason_params
        if decision.action in {"set_export_limit_enabled", "set_export_limit_w",
                               "set_on_grid_soc_limit_pct"}:
            return decision.action, decision.value
        if decision.action in {"start_battery_charge", "start_battery_discharge"}:
            return (
                decision.action,
                decision.value,
                params.get("start_soc_pct"),
                params.get("stop_soc_pct"),
                params.get("valid_from"),
                params.get("valid_to"),
            )
        if decision.action == "stop_battery_control":
            return (decision.action,)
        return decision.action, decision.value

    @staticmethod
    def _goodwe_writer_params(decision: Decision) -> dict:
        params = decision.reason_params
        if decision.action in {"set_export_limit_enabled", "set_export_limit_w",
                               "set_on_grid_soc_limit_pct"}:
            return {"value": decision.value}
        if decision.action in {"start_battery_charge", "start_battery_discharge"}:
            result = {
                key: params[key]
                for key in ("power_pct", "start_soc_pct", "stop_soc_pct", "valid_from", "valid_to")
            }
            if params.get('valid_day'):
                result['valid_day'] = params['valid_day']
            return result
        return {}

    def apply(self, decision: Decision) -> Decision:
        """Zápis jde vždy přes change-gate readeru TNG – ten chrání čerpadlo."""
        if decision.action in GOODWE_ACTIONS:
            if not self.enabled or not self.config.get('controller.optimization.goodwe_control.enabled', False):
                decision.applied = False
                decision.reason_key = 'reason.write_blocked_gate'
                return decision
            writer = getattr(self.app, "goodwe_writer", None)
            if writer is None:
                decision.applied = False
                decision.reason_key = "reason.write_blocked_gate"
                return decision
            command_key = self._goodwe_command_key(decision)
            if decision.rule != 'battery_economic' and self._applied.get("goodwe_command") == command_key:
                decision.applied = False
                decision.reason_key = "reason.no_action_needed"
                return decision
            try:
                method = getattr(writer, decision.action)
                result = method(**self._goodwe_writer_params(decision))
                success = result.get("success", True) if isinstance(result, dict) else True
                decision.applied = bool(success)
                if decision.applied:
                    self._applied["goodwe_command"] = command_key
                else:
                    decision.reason_key = "reason.write_blocked_gate"
            except Exception as exc:
                decision.applied = False
                decision.reason_key = "reason.write_blocked_gate"
                decision.reason_params['write_error'] = type(exc).__name__
            return decision

        decision.applied = False
        decision.reason_key = 'reason.central_controller_required'
        return decision

    def record(self, decision: Decision) -> None:
        self.storage.append(self.source, {**decision.to_dict(), "source": self.source})
        self.last_decision = decision
        event(self.log, "decision", rule=decision.rule, action=decision.action,
              value=decision.value, applied=decision.applied, reason=decision.reason_key)

    def run_once(self) -> dict:
        """Jedno rozhodovací kolo. Nikdy nevyhodí výjimku."""
        with self._lock:
            self._last_run = now_local()
            if not self.enabled:
                self.safe_mode_reason = None
                return {"enabled": False, "decisions": []}

            if not self.config.get('controller.optimization.goodwe_control.enabled', False):
                self.safe_mode_reason = None
                return {"enabled": True, "safe_mode": False, "decisions": []}
            if self.config.get('controller.optimization.goodwe_control.economic.enabled', False):
                try:
                    moment = now_local()
                    payload = read_json(self.config.data_dir / f'ote-{moment.date().isoformat()}.json', {})
                    decisions = self.battery.decide(self.app.snapshot.get('goodwe', {}), payload, moment)
                    for decision in decisions:
                        self.battery.prepare_write(decision)
                        self.apply(decision)
                        self.battery.remember(decision, decision.applied)
                        self.battery.last_result = decision.to_dict()
                        self.battery.state['last_command'] = self.battery.last_result
                        self.record(decision)
                        if decision.action == 'start_battery_charge' and not decision.applied:
                            stop = Decision(rule='battery_economic', action='stop_battery_control', value=None,
                                            reason_key='reason.battery_write_failed', timestamp=moment)
                            self.apply(stop)
                            self.battery.remember(stop, stop.applied)
                            self.record(stop)
                    self.safe_mode_reason = ({'reason_key': 'reason.safe_mode_stale_data',
                                              'reason_params': {'source': 'goodwe/prices'}}
                                             if self.battery.state['phase'] == 'safe_mode' else None)
                    if self.battery.last_result and not self.battery.last_result['applied']:
                        self.safe_mode_reason = {'reason_key': 'reason.battery_write_failed',
                                                 'last_command': self.battery.last_result}
                    return {'enabled': True, 'safe_mode': bool(self.safe_mode_reason),
                            'decisions': [d.to_dict() for d in decisions]}
                except Exception as exc:
                    self.log.error('battery_decision_failed | error=%s', type(exc).__name__)
                    self.safe_mode_reason = {'reason_key': 'reason.battery_error', 'error': type(exc).__name__}
                    if self.battery.memory.get('owned'):
                        try:
                            stop = Decision(rule='battery_economic', action='stop_battery_control', value=None,
                                            reason_key='reason.battery_error', timestamp=now_local())
                            self.apply(stop)
                            self.battery.remember(stop, stop.applied)
                            self.record(stop)
                        except Exception:
                            self.log.error('battery_emergency_stop_failed')
                    return {'enabled': True, 'safe_mode': True, 'decisions': []}
            stale = self.stale_sources()
            if stale:
                # Safe mode: optimalizace stojí, nastavení se nemění, data se sbírají dál.
                self.safe_mode_reason = {
                    "reason_key": "reason.safe_mode_stale_data",
                    "reason_params": {"source": ", ".join(stale),
                                      "age": int(self.max_data_age(stale[0]))},
                }
                warn_event(self.log, "safe_mode", sources=",".join(stale))
                return {"enabled": True, "safe_mode": True, "decisions": []}

            self.safe_mode_reason = None
            try:
                context = self.build_context()
                decisions = [self.apply(decision) for decision in self.decide(context)]
            except Exception as exc:                      # noqa: BLE001
                self.log.error("decision_failed | error=%s: %s", type(exc).__name__, exc)
                return {"enabled": True, "error": str(exc), "decisions": []}

            for decision in decisions:
                self.record(decision)
            return {"enabled": True, "safe_mode": False,
                    "decisions": [decision.to_dict() for decision in decisions]}

    # --- napojení na aplikaci ---------------------------------------------------
    def on_sample(self, sample) -> None:
        """Volá se po každém vzorku; rozhoduje se nejvýš v nastaveném intervalu."""
        if not self.enabled:
            return
        interval = int(self.config.get("controller.decision_interval_seconds", 300))
        if self._last_run is not None and (now_local() - self._last_run) < timedelta(seconds=interval):
            return
        self.run_once()

    def recent(self, days: int = 7) -> list[dict]:
        return self.storage.query(self.source, now_local() - timedelta(days=days), now_local())
