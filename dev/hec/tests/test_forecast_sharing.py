"""Testy fáze D (dev/step09): odhad sdílené energie z historie vyúčtování."""

from __future__ import annotations

from hec.forecast.sharing_consumption_forecast import (
    confidence_for,
    forecast_shared_energy,
    sharing_ratio,
)

SETTLEMENTS = [
    {"delivered_kwh": 800.0, "shared_kwh": 160.0},   # 20 %
    {"delivered_kwh": 900.0, "shared_kwh": 180.0},   # 20 %
    {"delivered_kwh": 700.0, "shared_kwh": 105.0},   # 15 %
]


def test_sharing_ratio_is_the_median_of_closed_months():
    ratio, months = sharing_ratio(SETTLEMENTS)
    assert ratio == 0.2
    assert months == 3


def test_sharing_ratio_ignores_months_without_delivery():
    ratio, months = sharing_ratio([{"delivered_kwh": 0, "shared_kwh": 0}, *SETTLEMENTS])
    assert months == 3          # měsíc s nulovou dodávkou se do poměru nepočítá


def test_sharing_ratio_without_history_is_honest():
    assert sharing_ratio([]) == (None, 0)


def test_confidence_scales_with_months_not_days():
    assert confidence_for(0) == "low"
    assert confidence_for(2) == "medium"
    assert confidence_for(6) == "high"


def test_forecast_shared_energy_combines_ratio_with_expected_production():
    forecast = forecast_shared_energy(SETTLEMENTS, expected_production_kwh=500.0)
    assert forecast.value == 100.0                      # 0.2 * 500
    assert forecast.confidence == "medium"               # 3 měsíce >= MIN_MONTHS_MEDIUM
    assert forecast.range[0] < 100.0 < forecast.range[1]


def test_forecast_shared_energy_without_history_returns_none_not_a_guess():
    forecast = forecast_shared_energy([], expected_production_kwh=500.0)
    assert forecast.value is None and forecast.confidence == "low"


def test_forecast_shared_energy_without_expected_production_returns_none():
    forecast = forecast_shared_energy(SETTLEMENTS, expected_production_kwh=None)
    assert forecast.value is None
