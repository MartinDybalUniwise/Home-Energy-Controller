"""Pravidla řízení.

Každé pravidlo je deklarativní: má povolení, prioritu, podmínku, akci, limity
a **důvod jako překladový klíč** – nikdy hotovou větu, jinak by po přepnutí do
angličtiny nešla přečíst historie rozhodnutí.

Bezpečnost a komfort mají vždy přednost před optimalizací (kap. 8 zadání).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isfinite

from ..core.model import Decision
from ..core.timeutil import in_window


@dataclass
class Context:
    """Vstupy jednoho rozhodovacího kola."""

    now: object
    values: dict = field(default_factory=dict)      # snapshot zdrojů
    prices: list = field(default_factory=list)      # dnešní periody OTE
    forecast: dict = field(default_factory=dict)
    comfort: dict = field(default_factory=dict)
    optimization: dict = field(default_factory=dict)

    def source(self, name: str) -> dict:
        value = self.values.get(name)
        return value if isinstance(value, dict) else {}

    def number(self, source: str, key: str) -> float | None:
        value = self.source(source).get(key)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    # --- odvozené veličiny --------------------------------------------------
    @property
    def pv_surplus_kw(self) -> float | None:
        """Přebytek = výroba − spotřeba domu. Bez měření se nedopočítává."""
        pv = self.number("goodwe", "pv_w")
        house = self.number("goodwe", "house_w")
        if pv is None or house is None:
            return None
        return round((pv - house) / 1000.0, 2)

    @property
    def battery_soc(self) -> float | None:
        return self.number("goodwe", "battery_soc")

    @property
    def valid_battery_soc(self) -> float | None:
        value = self.battery_soc
        return value if value is not None and isfinite(value) and 0 <= value <= 100 else None

    @property
    def price(self) -> float | None:
        return (self.number("ote", "price_total_czk_kwh")
                or self.number("ote", "price_czk_kwh"))

    def price_quantile(self, fraction: float) -> float | None:
        prices = sorted(p.get("price_total_czk_kwh") for p in self.prices
                        if p.get("price_total_czk_kwh") is not None)
        if not prices:
            return None
        index = min(len(prices) - 1, max(0, int(round(fraction * (len(prices) - 1)))))
        return prices[index]

    @property
    def in_quiet_hours(self) -> bool:
        start = self.comfort.get("quiet_hours_from")
        end = self.comfort.get("quiet_hours_to")
        return bool(start and end and in_window(self.now, start, end))

    @property
    def dhw_temperature(self) -> float | None:
        return self.number("tng", "boiler_temperature")

    @property
    def dhw_setpoint(self) -> float | None:
        return self.number("tng", "boiler_set_temperature")

    @property
    def goodwe_control(self) -> dict:
        value = self.optimization.get("goodwe_control", {})
        return value if isinstance(value, dict) else {}

    @property
    def current_time(self) -> str:
        return self.now.strftime("%H:%M")


@dataclass
class Rule:
    name: str
    priority: int
    action: str
    evaluate: Callable[[Context], Decision | None]
    enabled: bool = True

    def __call__(self, context: Context) -> Decision | None:
        if not self.enabled:
            return None
        return self.evaluate(context)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# --- jednotlivá pravidla ----------------------------------------------------

def dhw_pv_surplus(context: Context) -> Decision | None:
    """Přebytek výroby + nabitá baterie + levná elektřina → ohřát vodu víc."""
    surplus = context.pv_surplus_kw
    soc = context.valid_battery_soc
    price = context.price
    if surplus is None or soc is None:
        return None

    threshold = float(context.optimization.get("pv_surplus_kw", 2.0))
    soc_min = float(context.optimization.get("battery_soc_min_pct", 60.0))
    if surplus < threshold or soc < soc_min:
        return None

    cheap = context.price_quantile(float(context.optimization.get("cheap_price_percentile", 0.25)))
    if price is not None and cheap is not None and price > cheap:
        return None

    target = clamp(float(context.comfort.get("dhw_max_c", 52.0)),
                   float(context.comfort.get("dhw_min_c", 45.0)),
                   float(context.comfort.get("dhw_max_c", 52.0)))
    return Decision(
        rule="dhw_pv_surplus", action="set_dhw", value=target,
        reason_key="reason.pv_surplus_high_soc",
        reason_params={"pv_kw": surplus, "soc": round(soc), "price": price},
    )


def dhw_price_high(context: Context) -> Decision | None:
    """Drahá elektřina bez přebytku → stáhnout ohřev na komfortní minimum."""
    price = context.price
    if price is None:
        return None
    expensive = context.price_quantile(
        float(context.optimization.get("expensive_price_percentile", 0.75)))
    if expensive is None or price < expensive:
        return None
    surplus = context.pv_surplus_kw
    if surplus is not None and surplus > 0.5:
        return None

    target = float(context.comfort.get("dhw_min_c", 45.0))
    return Decision(
        rule="dhw_price_high", action="set_dhw", value=target,
        reason_key="reason.price_high_use_inertia",
        reason_params={"price": price},
    )


def heating_preheat_cheap(context: Context) -> Decision | None:
    """Levné okno a chladno → mírné předtopení v mezích komfortu."""
    price = context.price
    outside = context.number("tng", "outside_temperature")
    if price is None or outside is None or outside > 12.0:
        return None
    cheap = context.price_quantile(float(context.optimization.get("cheap_price_percentile", 0.25)))
    if cheap is None or price > cheap:
        return None
    if context.in_quiet_hours:
        return None

    current = context.number("tng", "heating_set_temperature")
    if current is None:
        return None
    preheat = float(context.comfort.get("max_preheat_k", 1.5))
    target = round(current + preheat, 1)
    return Decision(
        rule="heating_preheat_cheap", action="set_heating", value=target,
        reason_key="reason.cheap_window_preheat",
        reason_params={"until": "", "price": price},
    )


def goodwe_charge_cheap(context: Context) -> Decision | None:
    """Charge below the cheap-price threshold while the SOC is below target."""
    control = context.goodwe_control
    if not control.get("enabled", False):
        return None
    soc = context.valid_battery_soc
    price = context.price
    cheap = context.price_quantile(float(context.optimization.get("cheap_price_percentile", 0.25)))
    if soc is None or price is None or cheap is None:
        return None
    start_soc = int(control.get("charge_start_soc_pct", 20))
    stop_soc = int(control.get("charge_stop_soc_pct", 80))
    active = context.source("goodwe").get("operation_mode") in {"ECO_CHARGE", "charge"}
    if (soc >= stop_soc if active else soc >= start_soc) or price > cheap:
        return None
    return Decision(
        rule="goodwe_charge_cheap", action="start_battery_charge",
        value=int(control.get("charge_power_pct", 50)),
        reason_key="reason.goodwe_charge_cheap",
        reason_params={
            "power_pct": int(control.get("charge_power_pct", 50)),
            "start_soc_pct": start_soc, "stop_soc_pct": stop_soc,
            "valid_from": "00:00", "valid_to": "23:59", "price": price,
        },
    )


def goodwe_enable_export_limit(context: Context) -> Decision | None:
    """Enable export limiting when configured and export is measured."""
    control = context.goodwe_control
    if not control.get("enabled", False) or not control.get("export_limit_enabled", False):
        return None
    if context.valid_battery_soc is None:
        return None
    export_w = context.number("goodwe", "grid_export_w")
    if export_w is None or export_w <= 0:
        return None
    if context.source("goodwe").get("export_limit_enabled") is True:
        return None
    return Decision(
        rule="goodwe_enable_export_limit", action="set_export_limit_enabled", value=True,
        reason_key="reason.goodwe_export_limit_enabled",
        reason_params={"export_w": round(export_w)},
    )


def goodwe_set_export_limit(context: Context) -> Decision | None:
    """Apply the configured export ceiling after export limiting is enabled."""
    control = context.goodwe_control
    if not control.get("enabled", False) or not control.get("export_limit_enabled", False):
        return None
    if context.valid_battery_soc is None:
        return None
    export_w = context.number("goodwe", "grid_export_w")
    if export_w is None or export_w <= 0:
        return None
    target = int(control.get("export_limit_w", 0))
    current = context.number("goodwe", "export_limit_w")
    if current is not None and current == target:
        return None
    return Decision(
        rule="goodwe_set_export_limit", action="set_export_limit_w", value=target,
        reason_key="reason.goodwe_export_limit_set",
        reason_params={"export_w": round(export_w), "limit_w": target},
    )


def goodwe_set_on_grid_soc_limit(context: Context) -> Decision | None:
    """Set the configured grid-charge SOC ceiling when explicitly enabled."""
    control = context.goodwe_control
    if not control.get("enabled", False) or not control.get("on_grid_soc_limit_enabled", False):
        return None
    if context.valid_battery_soc is None:
        return None
    target = int(control.get("on_grid_soc_limit_pct", 80))
    current = context.number("goodwe", "on_grid_soc_limit_pct")
    if current is not None and current == target:
        return None
    return Decision(
        rule="goodwe_set_on_grid_soc_limit", action="set_on_grid_soc_limit_pct", value=target,
        reason_key="reason.goodwe_on_grid_soc_limit",
        reason_params={"limit_pct": target},
    )


def goodwe_discharge_expensive(context: Context) -> Decision | None:
    """Discharge above the expensive-price threshold when SOC permits it."""
    control = context.goodwe_control
    if not control.get("enabled", False):
        return None
    soc = context.valid_battery_soc
    price = context.price
    expensive = context.price_quantile(
        float(context.optimization.get("expensive_price_percentile", 0.75)))
    if soc is None or price is None or expensive is None:
        return None
    start_soc = int(control.get("discharge_start_soc_pct", 80))
    stop_soc = int(control.get("discharge_stop_soc_pct", 20))
    active = context.source("goodwe").get("operation_mode") in {"ECO_DISCHARGE", "discharge"}
    if (soc <= stop_soc if active else soc <= start_soc) or price < expensive:
        return None
    return Decision(
        rule="goodwe_discharge_expensive", action="start_battery_discharge",
        value=int(control.get("discharge_power_pct", 30)),
        reason_key="reason.goodwe_discharge_expensive",
        reason_params={
            "power_pct": int(control.get("discharge_power_pct", 30)),
            "start_soc_pct": start_soc, "stop_soc_pct": stop_soc,
            "valid_from": "00:00", "valid_to": "23:59", "price": price,
        },
    )


def goodwe_stop_when_neutral(context: Context) -> Decision | None:
    """Stop an active battery mode when neither economic condition applies."""
    control = context.goodwe_control
    if not control.get("enabled", False):
        return None
    if context.valid_battery_soc is None:
        return None
    mode = context.source("goodwe").get("operation_mode")
    if mode not in {"ECO_CHARGE", "ECO_DISCHARGE", "charge", "discharge"}:
        return None
    if goodwe_charge_cheap(context) is not None or goodwe_discharge_expensive(context) is not None:
        return None
    return Decision(
        rule="goodwe_stop_when_neutral", action="stop_battery_control", value=None,
        reason_key="reason.goodwe_stop_neutral",
    )


PRIORITY_ALIASES = {
    "goodwe_enable_export_limit": "grid_export",
    "goodwe_set_export_limit": "grid_export",
    "goodwe_set_on_grid_soc_limit": "battery_charge",
    "goodwe_charge_cheap": "battery_charge",
    "goodwe_discharge_expensive": "battery_discharge",
    "goodwe_stop_when_neutral": "battery_control",
    "dhw_pv_surplus": "dhw",
    "dhw_price_high": "dhw",
    "heating_preheat_cheap": "thermal_storage",
}


def configured_priority(config, rule_name: str, fallback: int) -> int:
    """Resolve a rule priority from config, retaining legacy category names."""
    configured = config.get("controller.optimization.priorities", [])
    if not isinstance(configured, list):
        return fallback
    candidates = (rule_name, PRIORITY_ALIASES.get(rule_name))
    for index, name in enumerate(configured):
        if name in candidates:
            return index
    return len(configured) + fallback


def default_rules(config) -> list[Rule]:
    """Startovní sada; priority jsou konfigurovatelné, nižší číslo rozhoduje dřív."""
    aggressiveness = str(config.get("controller.optimization.aggressiveness", "medium"))
    return [
           Rule("goodwe_enable_export_limit", configured_priority(config, "goodwe_enable_export_limit", 0), "set_export_limit_enabled",
               goodwe_enable_export_limit),
           Rule("goodwe_set_export_limit", configured_priority(config, "goodwe_set_export_limit", 1), "set_export_limit_w", goodwe_set_export_limit),
           Rule("goodwe_set_on_grid_soc_limit", configured_priority(config, "goodwe_set_on_grid_soc_limit", 2), "set_on_grid_soc_limit_pct",
               goodwe_set_on_grid_soc_limit),
           Rule("goodwe_charge_cheap", configured_priority(config, "goodwe_charge_cheap", 3), "start_battery_charge", goodwe_charge_cheap),
           Rule("goodwe_discharge_expensive", configured_priority(config, "goodwe_discharge_expensive", 4), "start_battery_discharge",
               goodwe_discharge_expensive),
           Rule("goodwe_stop_when_neutral", configured_priority(config, "goodwe_stop_when_neutral", 5), "stop_battery_control",
               goodwe_stop_when_neutral),
        Rule("dhw_pv_surplus", configured_priority(config, "dhw_pv_surplus", 6), "set_dhw", dhw_pv_surplus),
        Rule("dhw_price_high", configured_priority(config, "dhw_price_high", 7), "set_dhw", dhw_price_high),
        Rule("heating_preheat_cheap", configured_priority(config, "heating_preheat_cheap", 8), "set_heating", heating_preheat_cheap,
             enabled=aggressiveness in ("medium", "high")),
    ]
