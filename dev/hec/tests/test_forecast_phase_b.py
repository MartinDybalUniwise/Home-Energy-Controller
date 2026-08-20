"""Testy fáze B (dev/step09): tenké obálky nad Predictorem a jejich zapojení
do /api/prediction vedle stávajících polí."""

from __future__ import annotations

from hec.forecast.household_consumption_forecast import forecast_household_consumption
from hec.forecast.pv_forecast import forecast_pv
from hec.web import api


def test_forecast_pv_wraps_the_predictor_day_dict():
    day = {"pv_kwh": 4.2, "pv_kwh_low": 3.7, "pv_kwh_high": 4.7, "confidence": "medium"}
    forecast = forecast_pv(day, "2026-08-19T13:00:00+02:00")

    assert forecast.value == 4.2
    assert forecast.range == (3.7, 4.7)
    assert forecast.confidence == "medium"
    assert forecast.model_version


def test_forecast_pv_missing_value_stays_none_not_zero():
    forecast = forecast_pv({"pv_kwh": None})
    assert forecast.value is None and forecast.range is None


def test_forecast_household_consumption_derives_confidence_from_sample_count():
    day = {"consumption_kwh": 12.0, "learned_days": {"consumption": 25}}
    forecast = forecast_household_consumption(day)

    assert forecast.value == 12.0
    assert forecast.confidence == "high"          # >= MIN_DAYS_HIGH (21) v Predictoru
    assert forecast.range[0] < 12.0 < forecast.range[1]


def test_forecast_household_consumption_without_history_is_honest():
    forecast = forecast_household_consumption({"consumption_kwh": None, "learned_days": {}})
    assert forecast.value is None and forecast.range is None and forecast.confidence == "low"


class FakePredictor:
    def forecast(self):
        return {
            "available": True,
            "generated_at": "2026-08-19T13:00:00+02:00",
            "days": [
                {"date": "2026-08-20", "pv_kwh": 5.0, "pv_kwh_low": 4.4, "pv_kwh_high": 5.6,
                 "confidence": "high", "consumption_kwh": 10.0,
                 "learned_days": {"pv": 25, "consumption": 25, "heat": 0}},
            ],
        }


class FakeApp:
    predictor = FakePredictor()


def test_prediction_api_adds_the_new_shape_next_to_the_old_fields():
    status, payload = api.prediction(FakeApp())
    day = payload["days"][0]

    # Staré ploché pole zůstává beze změny – zpětná kompatibilita.
    assert day["pv_kwh"] == 5.0
    # Nové sjednocené pole vedle něj.
    assert day["forecast_pv"]["value"] == 5.0
    assert day["forecast_pv"]["confidence"] == "high"
    assert day["forecast_consumption"]["value"] == 10.0
    assert status == 200
