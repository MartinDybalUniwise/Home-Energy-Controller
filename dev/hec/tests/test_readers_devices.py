"""Testy převodu odpovědí zařízení na jednotné veličiny."""

from __future__ import annotations

from conftest import FakeResponse, FakeSession
from hec.core import config as config_mod
from hec.core import schema
from hec.readers.goodwe import GoodWeReader
from hec.readers.shelly import ShellyReader
from hec.readers.weather import WeatherReader, condition_from_code


def make_config(tmp_path, **sections):
    data = schema.defaults()
    for section, values in sections.items():
        data[section].update(values)
    return config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)


# --- GoodWe ----------------------------------------------------------------

RUNTIME = {
    "ppv": 4210, "ppv1": 2100, "ppv2": 2110, "house_consumption": 1250,
    "active_power": -850, "pbattery1": 900, "battery_soc": 91, "battery_soh": 99,
    "e_day": 21.4, "e_load_day": 18.2, "e_day_imp": 2.1, "e_day_exp": 5.5,
    "work_mode_label": "Normal", "grid_in_out_label": "Export",
    "vgrid": 236.5, "igrid": 2.1, "pgrid": 500, "pgrid2": 300, "pgrid3": 1400,
}


def test_goodwe_maps_known_fields(tmp_path):
    reader = GoodWeReader(make_config(tmp_path, goodwe={"enabled": True}), connect=object())
    values = reader.map_values(RUNTIME)

    assert values["pv_w"] == 4210
    assert values["house_w"] == 1250
    assert values["battery_soc"] == 91
    assert values["e_export_day_kwh"] == 5.5
    assert values["l3_w"] == 1400


def test_goodwe_derives_flow_direction_from_sign(tmp_path):
    config = make_config(tmp_path, goodwe={"enabled": True})
    reader = GoodWeReader(config, connect=object())

    values = reader.map_values(RUNTIME)
    assert values["grid_import_w"] == 0 and values["grid_export_w"] == 850
    assert values["battery_charge_w"] == 900 and values["battery_discharge_w"] == 0

    # Instalace s opačnou konvencí znaménka se řeší konfigurací, ne úpravou kódu.
    config.data["goodwe"]["grid_positive_is_import"] = False
    assert reader.map_values(RUNTIME)["grid_import_w"] == 850


def test_goodwe_reports_phase_imbalance(tmp_path):
    reader = GoodWeReader(make_config(tmp_path, goodwe={"enabled": True}), connect=object())
    assert reader.map_values(RUNTIME)["phase_imbalance_w"] == 1100


def test_goodwe_tolerates_missing_phase_fields(tmp_path):
    """Firmware bez fázových hodnot nesmí čtení shodit."""
    reader = GoodWeReader(make_config(tmp_path, goodwe={"enabled": True}), connect=object())
    values = reader.map_values({"ppv": 100, "battery_soc": 50})

    assert "l1_w" not in values and "phase_imbalance_w" not in values
    assert values["pv_w"] == 100


# --- Shelly ----------------------------------------------------------------

GEN2_SWITCH = {"switch:0": {"apower": 2100.5, "voltage": 236.1, "current": 8.9,
                            "output": True, "aenergy": {"total": 1084.0}}}
GEN2_EM = {"em:0": {"a_act_power": 1200.0, "b_act_power": 300.0, "c_act_power": 100.0,
                    "total_act_power": 1600.0, "a_voltage": 236.0, "a_current": 5.1},
           "emdata:0": {"total_act": 4200.0}}
GEN1 = {"meters": [{"power": 812.4, "total": 120000}], "relays": [{"ison": True}]}


def test_shelly_gen2_switch():
    values = ShellyReader.parse_gen2(GEN2_SWITCH)
    assert values["power_w"] == 2100.5
    assert values["energy_kwh"] == 1.084          # Wh -> kWh
    assert values["on"] is True


def test_shelly_pro_3em_reads_all_phases():
    values = ShellyReader.parse_gen2(GEN2_EM)
    assert values["l1_w"] == 1200.0 and values["l3_w"] == 100.0
    assert values["power_w"] == 1600.0
    assert values["energy_kwh"] == 4.2


def test_shelly_gen1_converts_watt_minutes():
    values = ShellyReader.parse_gen1(GEN1)
    assert values["power_w"] == 812.4
    assert values["energy_kwh"] == 2.0            # 120000 Wmin = 2 kWh


def test_shelly_unreachable_device_does_not_hide_the_others(tmp_path):
    config = make_config(tmp_path, shelly={"enabled": True, "devices": [
        {"name": "Myčka", "host": "10.0.0.5", "role": "appliance", "generation": 2,
         "channel": 0, "enabled": True},
        {"name": "TČ", "host": "10.0.0.9", "role": "heatpump_meter", "generation": 2,
         "channel": 0, "enabled": True},
    ]})
    session = FakeSession({"10.0.0.5": FakeResponse(payload=GEN2_SWITCH),
                           "10.0.0.9": FakeResponse(payload={}, status_code=500)})
    reader = ShellyReader(config, session=session)

    values = reader.read()
    assert values["devices"]["mycka"]["power_w"] == 2100.5
    assert "tc" in values["errors"]
    assert values["appliances_power_w"] == 2100.5


def test_shelly_history_splits_devices_into_own_series(tmp_path):
    config = make_config(tmp_path, shelly={"enabled": True, "devices": [
        {"name": "Myčka", "host": "10.0.0.5", "role": "appliance", "generation": 2,
         "channel": 0, "enabled": True}]})
    session = FakeSession({"10.0.0.5": FakeResponse(payload=GEN2_SWITCH)})
    reader = ShellyReader(config, session=session)

    sample = reader.poll()
    targets = dict(reader.history_targets(sample.values, sample))
    assert set(targets) == {"shelly", "shelly_mycka"}
    assert targets["shelly_mycka"]["power_w"] == 2100.5


def test_shelly_all_devices_failing_is_a_reader_error(tmp_path):
    config = make_config(tmp_path, shelly={"enabled": True, "devices": [
        {"name": "Myčka", "host": "10.0.0.5", "role": "appliance", "generation": 2,
         "channel": 0, "enabled": True}]})
    session = FakeSession({"10.0.0.5": FakeResponse(payload={}, status_code=500)})
    reader = ShellyReader(config, session=session)

    assert reader.poll().ok is False


# --- počasí ----------------------------------------------------------------

def test_condition_mapping():
    assert condition_from_code(0) == "clear"
    assert condition_from_code(3) == "cloudy"
    assert condition_from_code(95) == "thunderstorm"
    assert condition_from_code(None) == "unknown"


def test_weather_keeps_contract_and_adds_sun_times(tmp_path):
    from hec.core.timeutil import now_local
    hour = now_local().replace(minute=0, second=0, microsecond=0)
    times = [(hour.replace(tzinfo=None)).strftime("%Y-%m-%dT%H:%M")]
    payload = {
        "current": {"time": times[0], "temperature_2m": 17.9, "cloud_cover": 100,
                    "precipitation": 0.0, "wind_speed_10m": 5.7, "weather_code": 3,
                    "shortwave_radiation": 0.0, "direct_radiation": 0.0,
                    "diffuse_radiation": 0.0, "is_day": 1},
        "hourly": {"time": times, "temperature_2m": [18.3], "cloud_cover": [100],
                   "precipitation": [0.0], "wind_speed_10m": [5.1], "weather_code": [61],
                   "shortwave_radiation": [0.0], "direct_radiation": [0.0],
                   "diffuse_radiation": [0.0], "sunshine_duration": [0.0]},
        "daily": {"time": ["2026-08-19"], "sunrise": ["2026-08-19T05:42"],
                  "sunset": ["2026-08-19T20:03"], "temperature_2m_max": [24.0],
                  "temperature_2m_min": [13.0], "precipitation_sum": [0.4],
                  "shortwave_radiation_sum": [18.2], "weather_code": [61]},
    }
    config = make_config(tmp_path, weather={"enabled": True})
    config.ensure_dirs()
    reader = WeatherReader(config, fetch=lambda url: payload)

    values = reader.read()
    assert values["condition"] == "cloudy"
    assert values["sunrise"] == "2026-08-19T05:42"

    import json
    written = json.loads((config.data_dir / "weather.json").read_text(encoding="utf-8"))
    # Formát prototypu je kontrakt – tato pole musí zůstat.
    assert set(written) >= {"source", "location", "latitude", "longitude", "fetched_at",
                            "current", "forecast_hourly"}
    assert set(written["current"]) >= {"time", "temp_c", "cloud_pct", "precip_mm",
                                       "wind_kmh", "ghi_wm2", "direct_wm2", "diffuse_wm2"}
    assert written["forecast_daily"][0]["temp_max_c"] == 24.0
