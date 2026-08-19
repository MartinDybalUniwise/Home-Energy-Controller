"""Pravidla řízení.

Každé pravidlo je deklarativní: má povolení, prioritu, podmínku, akci, limity
a **důvod jako překladový klíč** – nikdy hotovou větu, jinak by po přepnutí do
angličtiny nešla přečíst historie rozhodnutí.

Bezpečnost a komfort mají vždy přednost před optimalizací (kap. 8 zadání).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

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
    soc = context.battery_soc
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


def default_rules(config) -> list[Rule]:
    """Startovní sada. Pořadí = priorita; nižší číslo rozhoduje dřív."""
    aggressiveness = str(config.get("controller.optimization.aggressiveness", "medium"))
    return [
        Rule("dhw_pv_surplus", 10, "set_dhw", dhw_pv_surplus),
        Rule("dhw_price_high", 20, "set_dhw", dhw_price_high),
        Rule("heating_preheat_cheap", 30, "set_heating", heating_preheat_cheap,
             enabled=aggressiveness in ("medium", "high")),
    ]
