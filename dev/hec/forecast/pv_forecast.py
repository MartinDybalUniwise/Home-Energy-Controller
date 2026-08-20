"""Fáze B (dev/step09/EXTENSION_PLAN.md) – tenká obálka nad
`controller/predictor.py`, ne nová predikční logika. `Predictor.forecast()`
už denní odhad výroby počítá i s intervalem a jistotou; tady se jen převádí
do jednotného tvaru `Forecast`.
"""

from __future__ import annotations

from ..core.timeutil import now_local, parse_iso
from . import Forecast

MODEL_VERSION = "predictor-linear-ratio-v1"


def forecast_pv(day: dict, generated_at: str | None = None) -> Forecast:
    """Predikce výroby FVE pro jeden den z `Predictor.forecast()['days'][i]`."""
    value = day.get("pv_kwh")
    range_ = (day["pv_kwh_low"], day["pv_kwh_high"]) if value is not None else None
    return Forecast(
        value=value,
        range=range_,
        confidence=day.get("confidence", "low"),
        model_version=MODEL_VERSION,
        generated_at=parse_iso(generated_at) or now_local(),
    )
