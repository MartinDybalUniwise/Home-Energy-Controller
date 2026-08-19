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
from .rules import Context, clamp, default_rules

CRITICAL_SOURCES = ("goodwe", "tng")


class Controller:
    source = "controller"

    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.storage = app.storage
        self.log = get_logger("controller")
        self.rules = sorted(default_rules(self.config), key=lambda rule: rule.priority)
        self.last_decision: Decision | None = None
        self.safe_mode_reason: dict | None = None
        self._lock = threading.Lock()
        self._last_run: datetime | None = None
        self._applied: dict[str, float] = {}

    # --- stav ---------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return bool(self.config.get("controller.enabled", False))

    def stale_sources(self) -> list[str]:
        """Kritické zdroje, které nedávají čerstvá data."""
        limit = float(self.config.get("controller.max_data_age_seconds", 300))
        stale = []
        for reader in self.app.readers:
            if reader.name not in CRITICAL_SOURCES or not reader.status.enabled:
                continue
            age = reader.status.age
            if age is None or age > limit:
                stale.append(reader.name)
        return stale

    def state(self) -> dict:
        return {
            "enabled": self.enabled,
            "safe_mode": bool(self.safe_mode_reason) or not self.enabled,
            "safe_mode_reason": self.safe_mode_reason,
            "write_enabled": bool(self.config.get("tng.write_enabled", False)),
            "rules": [{"name": rule.name, "priority": rule.priority, "enabled": rule.enabled}
                      for rule in self.rules],
            "last_decision": self.last_decision.to_dict() if self.last_decision else None,
            "last_run": to_iso(self._last_run),
        }

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
        for rule in self.rules:
            if rule.action in taken:
                continue
            decision = rule(context)
            if decision is None:
                continue
            self._enforce_limits(decision, context)
            decisions.append(decision)
            taken.add(rule.action)
        return decisions

    def _enforce_limits(self, decision: Decision, context: Context) -> None:
        """Komfortní meze jsou absolutní – pravidlo je nesmí překročit."""
        comfort = context.comfort
        if decision.action == "set_dhw":
            decision.value = clamp(float(decision.value),
                                   float(comfort.get("dhw_min_c", 45.0)),
                                   float(comfort.get("dhw_max_c", 52.0)))
        elif decision.action == "set_heating":
            current = context.number("tng", "heating_set_temperature") or decision.value
            maximum = current + float(comfort.get("max_preheat_k", 1.5))
            decision.value = round(min(float(decision.value), maximum), 1)

    # --- provedení -------------------------------------------------------------
    def apply(self, decision: Decision) -> Decision:
        """Zápis jde vždy přes change-gate readeru TNG – ten chrání čerpadlo."""
        reader = self.app.reader("tng")
        if reader is None or not self.config.get("tng.write_enabled", False):
            decision.applied = False
            return decision
        if self._applied.get(decision.action) == decision.value:
            decision.applied = False
            decision.reason_key = "reason.no_action_needed"
            return decision

        if decision.action == "set_dhw":
            state = {"settings": {
                "boiler_set_temperature": (self.app.snapshot.get("tng") or {}).get("boiler_set_temperature"),
                "last_settings_not_confirmed": (self.app.snapshot.get("tng") or {}).get("pending_change"),
            }}
            applied, reason = reader.request_boiler_temperature(float(decision.value), state)
            decision.applied = applied
            if not applied:
                decision.reason_key = ("reason.no_action_needed" if reason == "already_set"
                                       else "reason.write_blocked_gate")
            else:
                self._applied[decision.action] = decision.value
        else:
            # Zásah do topení zatím jen doporučujeme – zápis topné křivky
            # potřebuje ověření na reálném hardwaru.
            decision.applied = False
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

            stale = self.stale_sources()
            if stale:
                # Safe mode: optimalizace stojí, nastavení se nemění, data se sbírají dál.
                self.safe_mode_reason = {
                    "reason_key": "reason.safe_mode_stale_data",
                    "reason_params": {"source": ", ".join(stale),
                                      "age": int(self.config.get("controller.max_data_age_seconds", 300))},
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
