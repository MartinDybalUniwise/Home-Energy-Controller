"""Testy readerů OTE a TNG – cenové přepočty a ochrana zápisu do čerpadla."""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import patch

from conftest import FakeResponse, FakeSession
from hec.core import config as config_mod
from hec.core import schema
from hec.readers.ote import OteReader, extract_periods
from hec.readers.tng import TngReader, scheduled_value

OTE_PAGE = """
<table>
  <tr><th>Časový interval</th><th>15min cena (EUR/MWh)</th></tr>
  <tr><td>00:00 - 00:15</td><td>100,00</td></tr>
  <tr><td>00:15 - 00:30</td><td>200,00</td></tr>
  <tr><td>00:30 - 23:59</td><td>-20,00</td></tr>
</table>
"""
CNB_TEXT = "19.08.2026 #160\nzemě|měna|množství|kód|kurz\nEMU|euro|1|EUR|25,065\nUSA|dolar|1|USD|22,100\n"

THERMOSTAT_HTML = '<script>var d = {"LastSettingsNotConfirmed": false, "DayTemperature": 23};</script>'
INSTALLATIONS_HTML = """
<script>HeatPump = {"Settings":{"BoilerSet":{"Boiler":true,"Sensor":true,"Boost":false},
"BoilerTemp":{"ShortValue":51,"FloatValue":51.0},"HeatSet":{"Heat":false,"HeatingMode":0},
"HeatTemp_Const":{"FloatValue":42.0},"EquitCurve":2},"LastSettingsNotConfirmed":false,
"AdvancedSettingsNotConfirmed":false}; CurrentHeatPumpHash = "HASH";</script>
"""
TELEMETRY = {"First": [{"time": "2026-08-19T10:51:23Z", "t": 234, "tw": 309, "tb": 514, "tt": 249}]}


def make_config(tmp_path, **sections):
    data = schema.defaults()
    for section, values in sections.items():
        data[section].update(values)
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    return config


# --- OTE -------------------------------------------------------------------

def test_extract_periods_numbers_them_from_one():
    periods = extract_periods(OTE_PAGE)
    assert [p["period"] for p in periods] == [1, 2, 3]
    assert periods[2]["price_eur_mwh"] == -20.0


def test_price_conversion_includes_distribution_fees_and_vat(tmp_path):
    config = make_config(tmp_path, ote={"distribution_czk_kwh": 1.5, "fees_czk_kwh": 0.5,
                                        "vat_rate": 0.21})
    reader = OteReader(config, session=FakeSession({}))

    spot, total = reader.price_czk_kwh(100.0, 25.0)
    assert spot == 2.5                                   # 100 EUR/MWh * 25 / 1000
    assert total == round((2.5 + 1.5 + 0.5) * 1.21, 4)


def test_cnb_rate_is_parsed_and_cached(tmp_path):
    config = make_config(tmp_path)
    session = FakeSession({"cnb.cz": FakeResponse(CNB_TEXT)})
    reader = OteReader(config, session=session)

    assert reader.eur_czk_rate() == 25.065
    # Druhé volání už na ČNB nechodí – kurz se drží v data/current_fx.json.
    session.routes.clear()
    assert reader.eur_czk_rate() == 25.065


def test_cnb_failure_falls_back_to_configured_rate(tmp_path):
    config = make_config(tmp_path, ote={"eur_czk_rate": 24.5})
    reader = OteReader(config, session=FakeSession({"cnb.cz": FakeResponse("", status_code=503)}))

    assert reader.eur_czk_rate() == 24.5


def test_read_writes_day_file_in_the_documented_shape(tmp_path):
    config = make_config(tmp_path, ote={"fetch_rate_from_cnb": False, "eur_czk_rate": 25.0,
                                        "vat_rate": 0.0})
    reader = OteReader(config, session=FakeSession({"ote-cr.cz": FakeResponse(OTE_PAGE)}))

    values = reader.read()

    files = sorted(config.data_dir.glob("ote-*.json"))
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert set(payload) >= {"date", "market", "resolution", "currency", "source", "fetched_at",
                            "period_count", "min_price_eur_mwh", "max_price_eur_mwh",
                            "avg_price_eur_mwh", "periods"}
    assert payload["periods"][0]["price_czk_kwh"] == 2.5
    assert values["price_total_czk_kwh"] is not None


def test_read_does_not_refetch_a_day_that_is_already_cached_on_disk(tmp_path):
    """Jednou zveřejněná cena se nemění – opakované čtení nemá zatěžovat OTE."""
    config = make_config(tmp_path, ote={"fetch_rate_from_cnb": False, "eur_czk_rate": 25.0,
                                        "vat_rate": 0.0})
    session = FakeSession({"ote-cr.cz": FakeResponse(OTE_PAGE)})
    reader = OteReader(config, session=session)

    reader.read()
    session.routes.clear()                                # žádný další požadavek nesmí projít

    reader.read()                                         # nespadne, i když network zmizel


def test_ote_schedule_next_wakes_near_the_publish_window_when_tomorrow_is_missing(tmp_path):
    """D+1 se zveřejňuje po uzávěrce aukce ve 12:00 (kolem 13:00-13:30) –
    dokud zítřejší den nemáme, probudit se blízko tohoto okna dává smysl
    místo čekání na celý (několikahodinový) polling interval."""
    config = make_config(tmp_path)
    reader = OteReader(config, session=FakeSession({}))

    # Blíž k oknu než k celému (výchozímu 4h) intervalu, aby hranice vyhrála.
    moment = datetime(2026, 8, 19, 12, 0)
    boundary = reader._next_publish_boundary_seconds(moment)
    assert boundary == 3600 + 15 * 60                      # 13:15 je za 1h15m

    monotonic_now = 1000.0
    with patch("hec.readers.ote.now_local", return_value=moment):
        reader.schedule_next(monotonic_now)
    assert reader._next_at == monotonic_now + boundary


def test_ote_schedule_next_ignores_publish_window_once_tomorrow_is_cached(tmp_path):
    config = make_config(tmp_path)
    reader = OteReader(config, session=FakeSession({}))
    reader.save_day({"date": "2026-08-20",
                     "periods": [{"period": 1, "start": "00:00", "end": "00:15",
                                 "price_eur_mwh": 80.0, "price_czk_kwh": 2.0,
                                 "price_total_czk_kwh": 2.0}]})

    moment = datetime(2026, 8, 19, 9, 0)
    with patch("hec.readers.ote.now_local", return_value=moment):
        reader.schedule_next(1000.0)
    assert reader._next_at == 1000.0 + reader.backoff_seconds()


def test_ote_cache_ignores_a_file_written_by_the_legacy_prototype_reader(tmp_path):
    """data/ote-*.json je sdílený formát se zmrazeným ote_reader.py v kořeni,
    který CZK ceny nedopočítává – takový soubor nesmí projít jako platná cache,
    jinak by na něm read() spadl na chybějícím price_total_czk_kwh."""
    config = make_config(tmp_path, ote={"fetch_rate_from_cnb": False, "eur_czk_rate": 25.0,
                                        "vat_rate": 0.0})
    legacy_payload = {"date": "2026-08-19", "market": "OTE day-ahead market",
                      "resolution": "PT15M", "currency": "EUR/MWh", "source": "legacy",
                      "fetched_at": "2026-08-19T10:00:00+02:00", "period_count": 1,
                      "min_price_eur_mwh": 100.0, "max_price_eur_mwh": 100.0,
                      "avg_price_eur_mwh": 100.0,
                      "periods": [{"period": 1, "start": "00:00", "end": "00:15",
                                  "price_eur_mwh": 100.0}]}          # bez CZK polí
    (config.data_dir / "ote-2026-08-19.json").write_text(json.dumps(legacy_payload), encoding="utf-8")
    session = FakeSession({"ote-cr.cz": FakeResponse(OTE_PAGE)})
    reader = OteReader(config, session=session)

    payload = reader.load_or_fetch_day(date(2026, 8, 19))

    assert payload["periods"][0]["price_total_czk_kwh"] is not None
    assert any(method == "GET" for method, _ in session.calls)   # skutečně došlo k re-fetchi


# --- TNG -------------------------------------------------------------------

def build_tng(tmp_path, tng_connect, **overrides):
    config = make_config(tmp_path, tng={"enabled": True, **overrides})
    session = FakeSession({
        "MyThermostat": FakeResponse(THERMOSTAT_HTML),
        "MyInstallations": FakeResponse(INSTALLATIONS_HTML),
        "HeatPumpData": FakeResponse(payload=TELEMETRY),
        "Pages/Login": FakeResponse("<html></html>"),
        "api/HeatPumpInsertBasicSettings": FakeResponse("", status_code=204),
    })
    return TngReader(config, session=session, connect=tng_connect), config, session


def test_tng_reader_matches_prototype_parsing(tmp_path, tng_connect):
    reader, _, _ = build_tng(tmp_path, tng_connect)

    values = reader.read()
    assert values["boiler_set_temperature"] == 51.0
    assert values["outside_temperature"] == 23.4          # desetiny stupně
    assert values["room_temperature"] == 24.9
    assert values["heating_on"] is False


def test_tng_history_contains_one_record_per_telemetry_sample(tmp_path, tng_connect):
    reader, _, _ = build_tng(tmp_path, tng_connect)
    sample = reader.poll()

    targets = reader.history_targets(sample.values, sample)
    assert len(targets) == 1
    assert targets[0][1]["sample_time"] == "2026-08-19T10:51:23Z"
    assert targets[0][1]["boiler_temperature"] == 51.4


def test_tng_telemetry_cursor_prevents_duplicates(tmp_path, tng_connect):
    reader, _, _ = build_tng(tmp_path, tng_connect)
    reader.read()
    reader.read()

    assert reader._telemetry_records == []
    assert reader.telemetry_state["last_sample_time"] == "2026-08-19T10:51:23Z"


def test_tng_write_is_disabled_by_default(tmp_path, tng_connect):
    """Bez výslovného povolení se do čerpadla nezapisuje – jen se loguje záměr."""
    reader, _, session = build_tng(tmp_path, tng_connect,
                                   boiler={"enabled": True, "default_temperature": 51,
                                           "schedule": []})
    state = reader.read_state()
    actions = reader.apply(state)

    assert actions == []                                  # 51 už v TNG platí
    assert not any(method == "POST" for method, _ in session.calls)


def test_tng_change_gate_blocks_second_write(tmp_path, tng_connect):
    reader, config, session = build_tng(tmp_path, tng_connect, write_enabled=True,
                                        boiler={"enabled": True, "default_temperature": 48,
                                                "schedule": []})
    state = reader.read_state()

    assert reader.apply(state) == ["post:basic"]
    posts = [call for call in session.calls if call[0] == "POST"]
    assert len(posts) == 1

    # Druhý pokus musí narazit na čekání na potvrzení, ne poslat další požadavek.
    reader.pending_sent.clear()
    actions = reader.apply(state)
    assert actions and actions[0].startswith("skip:basic:waiting for TNG confirmation")
    assert len([c for c in session.calls if c[0] == "POST"]) == 1


def test_tng_gate_state_survives_restart(tmp_path, tng_connect):
    reader, config, _ = build_tng(tmp_path, tng_connect, write_enabled=True)
    reader._mark_posted("basic", {"boiler_temperature": 48})

    fresh = TngReader(config, session=FakeSession({}), connect=tng_connect)
    assert fresh.can_post("basic", False)[0] is False


def test_scheduled_value_helper_matches_prototype():
    from datetime import datetime
    section = {"default_temperature": 45, "schedule": [
        {"from": "22:00", "to": "06:00", "temperature": 51}]}
    assert scheduled_value(section, datetime(2026, 8, 19, 23, 0)) == 51
    assert scheduled_value(section, datetime(2026, 8, 19, 12, 0)) == 45
