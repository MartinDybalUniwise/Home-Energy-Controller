#!/usr/bin/env python3

import json
from pathlib import Path
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

LAT = 49.8209
LON = 18.2625
TZ = "Europe/Prague"
FORECAST_DAYS = 3

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather():
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "forecast_days": FORECAST_DAYS,
        "current": ",".join([
            "temperature_2m",
            "cloud_cover",
            "precipitation",
            "wind_speed_10m",
            "shortwave_radiation",
            "direct_radiation",
            "diffuse_radiation",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "cloud_cover",
            "precipitation",
            "wind_speed_10m",
            "shortwave_radiation",
            "direct_radiation",
            "diffuse_radiation",
            "sunshine_duration",
        ]),
    }

    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Elektrika/1.0"})

    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.load(response)

    current = data.get("current", {})
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    now = datetime.now(ZoneInfo(TZ))

    rows = []
    for i, ts in enumerate(times):
        row_time = datetime.fromisoformat(ts).replace(tzinfo=ZoneInfo(TZ))
        if row_time < now.replace(minute=0, second=0, microsecond=0):
            continue

        rows.append({
            "time": ts,
            "temp_c": hourly["temperature_2m"][i],
            "cloud_pct": hourly["cloud_cover"][i],
            "precip_mm": hourly["precipitation"][i],
            "wind_kmh": hourly["wind_speed_10m"][i],
            "ghi_wm2": hourly["shortwave_radiation"][i],
            "direct_wm2": hourly["direct_radiation"][i],
            "diffuse_wm2": hourly["diffuse_radiation"][i],
            "sunshine_sec": hourly["sunshine_duration"][i],
        })

    return {
        "source": "open-meteo",
        "location": "Ostrava, CZ",
        "latitude": LAT,
        "longitude": LON,
        "fetched_at": now.isoformat(timespec="seconds"),
        "current": {
            "time": current.get("time"),
            "temp_c": current.get("temperature_2m"),
            "cloud_pct": current.get("cloud_cover"),
            "precip_mm": current.get("precipitation"),
            "wind_kmh": current.get("wind_speed_10m"),
            "ghi_wm2": current.get("shortwave_radiation"),
            "direct_wm2": current.get("direct_radiation"),
            "diffuse_wm2": current.get("diffuse_radiation"),
        },
        "forecast_hourly": rows,
    }


def main():
    output_dir = Path(__file__).resolve().parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "weather.json"

    try:
        data = fetch_weather()
        data["status"] = "ok"
    except Exception as e:
        data = {
            "status": "error",
            "source": "open-meteo",
            "location": "Ostrava, CZ",
            "fetched_at": datetime.now(ZoneInfo(TZ)).isoformat(timespec="seconds"),
            "error": f"{type(e).__name__}: {e}",
        }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
