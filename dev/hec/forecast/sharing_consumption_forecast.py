"""Fáze D (dev/step09/EXTENSION_PLAN.md) – odhad sdílené energie.

Stejný přístup jako `controller/predictor.py` (`pv_factor`, `heat_slope`):
medián poměru z vlastní historie, žádné strojové učení. Vstupem jsou už
naimportované měsíční souhrny (`sharing_reader.py`, fáze C, proud
"sharing_settlement") a očekávaná výroba z `pv_forecast` – tahle funkce
sama nečte ani soubory, ani síť.
"""

from __future__ import annotations

from statistics import median

from ..core.timeutil import now_local, parse_iso
from . import Forecast

MODEL_VERSION = "sharing-ratio-v1"
# Sdílení se učí z měsíčních vyúčtování, ne denních vzorků jako Predictor –
# práh jistoty je proto v měsících, ne ve dnech.
MIN_MONTHS_MEDIUM = 2
MIN_MONTHS_HIGH = 6
CONFIDENCE_BANDS = {"high": 0.15, "medium": 0.25, "low": 0.40}


def confidence_for(months: int) -> str:
    if months >= MIN_MONTHS_HIGH:
        return "high"
    if months >= MIN_MONTHS_MEDIUM:
        return "medium"
    return "low"


def sharing_ratio(settlements: list[dict]) -> tuple[float | None, int]:
    """Medián poměru sdíleno/celková dodávka do sítě z uzavřených měsíců.

    Bez uzavřeného měsíce s nenulovou dodávkou vrací None, ne 0.0 – nulový
    poměr by v UI vypadal jako naučené "nikdy nesdílíme", ne jako chybějící
    data.
    """
    ratios = [settlement["shared_kwh"] / settlement["delivered_kwh"]
              for settlement in settlements
              if settlement.get("delivered_kwh") and settlement.get("shared_kwh") is not None
              and settlement["delivered_kwh"] > 0]
    if not ratios:
        return None, 0
    return round(median(ratios), 4), len(ratios)


def forecast_shared_energy(settlements: list[dict], expected_production_kwh: float | None,
                           generated_at: str | None = None) -> Forecast:
    """Odhad sdílené energie za nadcházející období = naučený poměr ×
    očekávaná výroba (z `pv_forecast.forecast_pv`). Chybí-li historie nebo
    očekávaná výroba, vrací se přiznaná neznalost, ne odhad od oka."""
    ratio, months = sharing_ratio(settlements)
    when = parse_iso(generated_at) or now_local()
    if ratio is None or expected_production_kwh is None:
        return Forecast(value=None, confidence="low", model_version=MODEL_VERSION, generated_at=when)

    confidence = confidence_for(months)
    band = CONFIDENCE_BANDS[confidence]
    value = round(ratio * expected_production_kwh, 2)
    return Forecast(
        value=value,
        range=(round(value * (1 - band), 2), round(value * (1 + band), 2)),
        confidence=confidence,
        model_version=MODEL_VERSION,
        generated_at=when,
    )
