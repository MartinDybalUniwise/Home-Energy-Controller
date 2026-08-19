"""Reader počasí (Open-Meteo).

Zachovává formát `data/weather.json` z prototypu a doplňuje východ/západ slunce
a kód počasí – bez nich nelze vybrat ikonu ani dynamické pozadí v UI.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import timedelta

from ..core.timeutil import now_local, parse_iso, to_iso
from ..storage.base import atomic_write_json
from .base import BaseReader

BASE_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_FIELDS = ["temperature_2m", "relative_humidity_2m", "apparent_temperature",
                  "cloud_cover", "precipitation", "wind_speed_10m", "wind_direction_10m",
                  "weather_code", "shortwave_radiation", "direct_radiation", "diffuse_radiation",
                  "is_day"]
HOURLY_FIELDS = ["temperature_2m", "cloud_cover", "precipitation", "wind_speed_10m",
                 "weather_code", "shortwave_radiation", "direct_radiation", "diffuse_radiation",
                 "sunshine_duration"]
DAILY_FIELDS = ["sunrise", "sunset", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "shortwave_radiation_sum", "weather_code"]

# Zjednodušené skupiny WMO kódů pro volbu ikony a pozadí.
CONDITIONS = [
    ((0,), "clear"), ((1, 2), "partly_cloudy"), ((3,), "cloudy"),
    ((45, 48), "fog"), ((51, 53, 55, 56, 57), "drizzle"),
    ((61, 63, 65, 66, 67, 80, 81, 82), "rain"),
    ((71, 73, 75, 77, 85, 86), "snow"), ((95, 96, 99), "thunderstorm"),
]


def condition_from_code(code) -> str:
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "unknown"
    for codes, name in CONDITIONS:
        if code in codes:
            return name
    return "unknown"


class WeatherReader(BaseReader):
    name = "weather"

    def __init__(self, config, storage=None, fetch=None):
        self._fetch = fetch                  # injektovatelné kvůli testům
        super().__init__(config, storage)

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.weather_minutes", 15)) * 60

    def _request(self, url: str) -> dict:
        if self._fetch is not None:
            return self._fetch(url)
        request = urllib.request.Request(url, headers={"User-Agent": "HomeEnergyController/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:   # noqa: S310
            return json.load(response)

    def build_url(self) -> str:
        params = {
            "latitude": self.config.get("system.latitude"),
            "longitude": self.config.get("system.longitude"),
            "timezone": self.config.get("system.timezone", "Europe/Prague"),
            "forecast_days": max(2, int(self.config.get("weather.forecast_days", 3))),
            "current": ",".join(CURRENT_FIELDS),
            "hourly": ",".join(HOURLY_FIELDS),
            "daily": ",".join(DAILY_FIELDS),
        }
        return BASE_URL + "?" + urllib.parse.urlencode(params)

    def read(self) -> dict:
        payload = self._request(self.build_url())
        data = self.map_payload(payload)
        atomic_write_json(self.config.data_dir / "weather.json", data)
        current = data["current"]
        return {
            "temp_c": current.get("temp_c"),
            "cloud_pct": current.get("cloud_pct"),
            "precip_mm": current.get("precip_mm"),
            "wind_kmh": current.get("wind_kmh"),
            "ghi_wm2": current.get("ghi_wm2"),
            "condition": current.get("condition"),
            "is_day": current.get("is_day"),
            "sunrise": data.get("sunrise"),
            "sunset": data.get("sunset"),
            "forecast_hours": len(data.get("forecast_hourly", [])),
        }

    def map_payload(self, payload: dict) -> dict:
        current = payload.get("current", {})
        hourly = payload.get("hourly", {})
        daily = payload.get("daily", {})
        times = hourly.get("time", [])
        now = now_local()
        hour_start = now.replace(minute=0, second=0, microsecond=0)

        def column(name, index, source=hourly):
            values = source.get(name)
            if not isinstance(values, list) or index >= len(values):
                return None
            return values[index]

        rows = []
        for index, stamp in enumerate(times):
            moment = parse_iso(stamp)
            if moment is None or moment < hour_start - timedelta(minutes=1):
                continue
            rows.append({
                "time": stamp,
                "temp_c": column("temperature_2m", index),
                "cloud_pct": column("cloud_cover", index),
                "precip_mm": column("precipitation", index),
                "wind_kmh": column("wind_speed_10m", index),
                "ghi_wm2": column("shortwave_radiation", index),
                "direct_wm2": column("direct_radiation", index),
                "diffuse_wm2": column("diffuse_radiation", index),
                "sunshine_sec": column("sunshine_duration", index),
                "condition": condition_from_code(column("weather_code", index)),
            })

        days = []
        for index, day in enumerate(daily.get("time", []) or []):
            days.append({
                "date": day,
                "sunrise": column("sunrise", index, daily),
                "sunset": column("sunset", index, daily),
                "temp_min_c": column("temperature_2m_min", index, daily),
                "temp_max_c": column("temperature_2m_max", index, daily),
                "precip_sum_mm": column("precipitation_sum", index, daily),
                "radiation_sum_mj": column("shortwave_radiation_sum", index, daily),
                "condition": condition_from_code(column("weather_code", index, daily)),
            })

        return {
            "source": "open-meteo",
            "status": "ok",
            "location": self.config.get("weather.location_name", ""),
            "latitude": self.config.get("system.latitude"),
            "longitude": self.config.get("system.longitude"),
            "fetched_at": to_iso(now),
            "sunrise": days[0]["sunrise"] if days else None,
            "sunset": days[0]["sunset"] if days else None,
            "current": {
                "time": current.get("time"),
                "temp_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "cloud_pct": current.get("cloud_cover"),
                "precip_mm": current.get("precipitation"),
                "wind_kmh": current.get("wind_speed_10m"),
                "wind_deg": current.get("wind_direction_10m"),
                "ghi_wm2": current.get("shortwave_radiation"),
                "direct_wm2": current.get("direct_radiation"),
                "diffuse_wm2": current.get("diffuse_radiation"),
                "is_day": bool(current.get("is_day", 1)),
                "condition": condition_from_code(current.get("weather_code")),
            },
            "forecast_hourly": rows,
            "forecast_daily": days,
        }
