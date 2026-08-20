"""Fáze B (dev/step09/EXTENSION_PLAN.md) – tenká obálka nad
`controller/predictor.py`. `Predictor.forecast()` počítá medián spotřeby, ale
vrací ho bez intervalu/jistoty (na rozdíl od výroby) – dopočítá se tu ze
stejné tabulky pásem (`CONFIDENCE_BANDS`), kterou `Predictor` používá pro
výrobu, aby oba kanály měly srovnatelně širokou nejistotu při stejném počtu
naučených dnů.
"""

from __future__ import annotations

from ..controller.predictor import CONFIDENCE_BANDS, Predictor
from ..core.timeutil import now_local, parse_iso
from . import Forecast

MODEL_VERSION = "predictor-median-v1"


def forecast_household_consumption(day: dict, generated_at: str | None = None) -> Forecast:
    """Predikce spotřeby domu pro jeden den z `Predictor.forecast()['days'][i]`."""
    value = day.get("consumption_kwh")
    samples = (day.get("learned_days") or {}).get("consumption", 0)
    confidence = Predictor.confidence_for(samples) if value is not None else "low"
    range_ = None
    if value is not None:
        band = CONFIDENCE_BANDS[confidence]
        range_ = (round(value * (1 - band), 2), round(value * (1 + band), 2))
    return Forecast(
        value=value,
        range=range_,
        confidence=confidence,
        model_version=MODEL_VERSION,
        generated_at=parse_iso(generated_at) or now_local(),
    )
