"""Testy datového kontraktu forecast/ (dev/step09, fáze A – jen tvar, žádná
predikční logika)."""

from __future__ import annotations

import pytest
from hec.forecast import Forecast


def test_forecast_carries_value_range_confidence_and_model_version():
    forecast = Forecast(value=4.2, range=(3.6, 4.9), confidence="medium",
                        model_version="linear-ratio-v1")
    payload = forecast.to_dict()
    assert payload["value"] == 4.2
    assert payload["range"] == [3.6, 4.9]
    assert payload["confidence"] == "medium"
    assert payload["model_version"] == "linear-ratio-v1"
    assert payload["generated_at"]


def test_forecast_missing_value_is_none_not_a_guess():
    forecast = Forecast(value=None)
    assert forecast.to_dict()["value"] is None
    assert forecast.to_dict()["range"] is None


def test_forecast_rejects_unknown_confidence_level():
    with pytest.raises(ValueError):
        Forecast(value=1.0, confidence="very_sure")
