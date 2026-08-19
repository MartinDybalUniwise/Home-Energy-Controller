"""Regresní testy weather_reader.py – formát data/weather.json je kontrakt."""

from __future__ import annotations

import io
import json
from datetime import timedelta

import weather_reader as legacy


class FakeUrlopen:
    def __init__(self, payload):
        self.payload = payload
        self.requested_url = None

    def __call__(self, request, timeout=None):
        self.requested_url = request.full_url
        return io.BytesIO(json.dumps(self.payload).encode("utf-8"))


def build_payload():
    from zoneinfo import ZoneInfo
    now = legacy.datetime.now(ZoneInfo(legacy.TZ)).replace(minute=0, second=0, microsecond=0)
    times = [(now + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M") for offset in (-2, 0, 1)]
    return {
        "current": {"time": times[1], "temperature_2m": 17.9, "cloud_cover": 100,
                    "precipitation": 0.0, "wind_speed_10m": 5.7, "shortwave_radiation": 0.0,
                    "direct_radiation": 0.0, "diffuse_radiation": 0.0},
        "hourly": {"time": times, "temperature_2m": [18.3, 17.9, 17.6],
                   "cloud_cover": [100, 100, 95], "precipitation": [0.0, 0.0, 0.1],
                   "wind_speed_10m": [5.1, 5.7, 6.9], "shortwave_radiation": [0.0, 0.0, 0.0],
                   "direct_radiation": [0.0, 0.0, 0.0], "diffuse_radiation": [0.0, 0.0, 0.0],
                   "sunshine_duration": [0.0, 0.0, 0.0]},
    }


def test_fetch_weather_keeps_documented_shape(monkeypatch):
    fake = FakeUrlopen(build_payload())
    monkeypatch.setattr(legacy.urllib.request, "urlopen",
                        lambda request, timeout=None: fake(request, timeout))

    data = legacy.fetch_weather()

    assert data["source"] == "open-meteo"
    assert set(data["current"]) == {"time", "temp_c", "cloud_pct", "precip_mm", "wind_kmh",
                                    "ghi_wm2", "direct_wm2", "diffuse_wm2"}
    assert data["current"]["temp_c"] == 17.9
    assert data["latitude"] == legacy.LAT and data["longitude"] == legacy.LON
    # Hodiny starší než aktuální se zahazují – předpověď má začínat teď.
    assert len(data["forecast_hourly"]) == 2
    assert "sunshine_sec" in data["forecast_hourly"][0]


def test_main_writes_error_status_instead_of_crashing(tmp_path, monkeypatch):
    """Výpadek Open-Meteo nesmí shodit proces – zapíše se status error."""
    monkeypatch.setattr(legacy, "__file__", str(tmp_path / "weather_reader.py"))
    monkeypatch.setattr(legacy.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("network down")))

    legacy.main()

    data = json.loads((tmp_path / "data" / "weather.json").read_text(encoding="utf-8"))
    assert data["status"] == "error"
    assert "network down" in data["error"]
