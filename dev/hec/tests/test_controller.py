"""Testy řízení. Nejdůležitější je, co se NESMÍ stát: obejít komfortní meze,
zapisovat při zastaralých datech nebo obcházet ochranu čerpadla.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from hec.controller.controller import Controller
from hec.controller.metrics import Metrics
from hec.controller.rules import Context, dhw_price_high, dhw_pv_surplus, heating_preheat_cheap
from hec.core import config as config_mod
from hec.core import schema
from hec.core.model import ReaderStatus
from hec.core.timeutil import now_local, to_iso
from hec.storage.jsonl import JsonlStorage


def make_config(tmp_path, **sections):
    data = schema.defaults()
    for section, values in sections.items():
        if isinstance(values, dict) and isinstance(data.get(section), dict):
            for key, value in values.items():
                if isinstance(value, dict) and isinstance(data[section].get(key), dict):
                    data[section][key].update(value)
                else:
                    data[section][key] = value
    config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
    config.ensure_dirs()
    return config


def price_periods(cheap=True):
    base = 1.0 if cheap else 5.0
    return [{"period": i + 1, "start": f"{i // 4:02d}:{i % 4 * 15:02d}", "end": "23:59",
             "price_total_czk_kwh": base if i < 48 else 6.0} for i in range(96)]


def context(**overrides):
    values = {
        "goodwe": {"pv_w": 6000, "house_w": 1000, "battery_soc": 95},
        "tng": {"boiler_temperature": 46.0, "boiler_set_temperature": 45,
                "heating_set_temperature": 40, "outside_temperature": 5.0},
        "ote": {"price_total_czk_kwh": 1.0},
    }
    values.update(overrides.pop("values", {}))
    return Context(
        now=overrides.pop("now", datetime(2026, 8, 19, 12, 0)),
        values=values,
        prices=overrides.pop("prices", price_periods()),
        comfort=overrides.pop("comfort", {"dhw_min_c": 45.0, "dhw_max_c": 52.0,
                                          "max_preheat_k": 1.5,
                                          "quiet_hours_from": "22:00", "quiet_hours_to": "06:00"}),
        optimization=overrides.pop("optimization", {"pv_surplus_kw": 2.0,
                                                    "battery_soc_min_pct": 60.0,
                                                    "cheap_price_percentile": 0.25,
                                                    "expensive_price_percentile": 0.75}),
    )


# --- pravidla ----------------------------------------------------------------

def test_surplus_rule_raises_dhw_target():
    decision = dhw_pv_surplus(context())
    assert decision.action == "set_dhw" and decision.value == 52.0
    assert decision.reason_key == "reason.pv_surplus_high_soc"
    # Důvod je klíč s parametry, ne hotová věta – jinak by nešel přeložit.
    assert decision.reason_params["soc"] == 95


def test_surplus_rule_waits_for_a_charged_battery():
    assert dhw_pv_surplus(context(values={"goodwe": {"pv_w": 6000, "house_w": 1000,
                                                     "battery_soc": 40}})) is None


def test_surplus_rule_needs_a_real_surplus():
    assert dhw_pv_surplus(context(values={"goodwe": {"pv_w": 1500, "house_w": 1000,
                                                     "battery_soc": 95}})) is None


def test_rule_does_not_guess_when_measurement_is_missing():
    assert dhw_pv_surplus(context(values={"goodwe": {}})) is None


def test_expensive_price_lowers_dhw_target():
    decision = dhw_price_high(context(values={"goodwe": {"pv_w": 0, "house_w": 1000,
                                                         "battery_soc": 50},
                                              "ote": {"price_total_czk_kwh": 6.0}}))
    assert decision.value == 45.0 and decision.reason_key == "reason.price_high_use_inertia"


def test_expensive_price_ignored_while_pv_covers_the_house():
    assert dhw_price_high(context(values={"goodwe": {"pv_w": 5000, "house_w": 1000,
                                                     "battery_soc": 50},
                                          "ote": {"price_total_czk_kwh": 6.0}})) is None


def test_preheating_is_blocked_during_quiet_hours():
    assert heating_preheat_cheap(context(now=datetime(2026, 8, 19, 23, 30))) is None
    assert heating_preheat_cheap(context()) is not None


def test_preheating_respects_the_comfort_limit():
    decision = heating_preheat_cheap(context())
    assert decision.value == 41.5              # 40 + max_preheat_k


def test_preheating_skipped_when_it_is_warm_outside():
    assert heating_preheat_cheap(context(values={"tng": {"outside_temperature": 18.0,
                                                         "heating_set_temperature": 40}})) is None


# --- controller ---------------------------------------------------------------

class FakeReader:
    def __init__(self, name, age=10.0, enabled=True):
        self.name = name
        self.status = ReaderStatus(name=name, enabled=enabled, interval_seconds=60)
        self.status.last_success = now_local() - timedelta(seconds=age)
        self.requests = []

    def request_boiler_temperature(self, temperature, state):
        self.requests.append(temperature)
        return True, "ok"


class FakeApp:
    def __init__(self, config, readers=None, snapshot=None):
        self.config = config
        self.storage = JsonlStorage(config.data_dir, config.history_dir)
        self.readers = readers or []
        self.snapshot = snapshot or {}
        self.predictor = None

    def reader(self, name):
        return next((reader for reader in self.readers if reader.name == name), None)


def build(tmp_path, *, enabled=True, write=False, ages=(10.0, 10.0), snapshot=None):
    config = make_config(tmp_path, controller={"enabled": enabled}, tng={"write_enabled": write},
                         goodwe={"enabled": True})
    readers = [FakeReader("goodwe", ages[0]), FakeReader("tng", ages[1])]
    snapshot = snapshot if snapshot is not None else {
        "goodwe": {"pv_w": 6000, "house_w": 1000, "battery_soc": 95},
        "tng": {"boiler_temperature": 46.0, "boiler_set_temperature": 45,
                "heating_set_temperature": 40, "outside_temperature": 5.0,
                "pending_change": False},
        "ote": {"price_total_czk_kwh": 1.0},
    }
    app = FakeApp(config, readers, snapshot)
    (config.data_dir / f"ote-{now_local().date().isoformat()}.json").write_text(
        json.dumps({"periods": price_periods()}), encoding="utf-8")
    return Controller(app), app, config


def test_disabled_controller_does_nothing(tmp_path):
    controller, _, _ = build(tmp_path, enabled=False)
    result = controller.run_once()

    assert result == {"enabled": False, "decisions": []}
    assert controller.state()["safe_mode"] is True


def test_stale_data_triggers_safe_mode_and_no_writes(tmp_path):
    """Zastaralá data znamenají zastavení optimalizace, ne odhad."""
    controller, app, _ = build(tmp_path, write=True, ages=(10.0, 9999.0))
    result = controller.run_once()

    assert result["safe_mode"] is True and result["decisions"] == []
    assert app.reader("tng").requests == []
    assert controller.state()["safe_mode_reason"]["reason_key"] == "reason.safe_mode_stale_data"


def test_decision_is_recorded_even_when_writing_is_disabled(tmp_path):
    controller, app, _ = build(tmp_path, write=False)
    result = controller.run_once()

    dhw = next(d for d in result["decisions"] if d["action"] == "set_dhw")
    assert dhw["rule"] == "dhw_pv_surplus" and dhw["applied"] is False
    assert app.reader("tng").requests == []
    # Každé rozhodnutí se zapíše do historie, i když se nikam neposílá.
    # (Pravidlo předtopení může být podle denní doby v tichém režimu.)
    assert len(app.storage.query("controller")) == len(result["decisions"])


def test_write_goes_through_the_tng_change_gate(tmp_path):
    controller, app, _ = build(tmp_path, write=True)
    controller.run_once()

    assert app.reader("tng").requests == [52.0]


def test_same_decision_is_not_repeated(tmp_path):
    """Opakované posílání téhož nastavení by zbytečně zatěžovalo čerpadlo."""
    controller, app, _ = build(tmp_path, write=True)
    controller.run_once()
    controller._last_run = None
    controller.run_once()

    assert app.reader("tng").requests == [52.0]


def test_comfort_limits_cannot_be_exceeded_by_a_rule(tmp_path):
    controller, app, config = build(tmp_path, write=True)
    config.data["controller"]["comfort"]["dhw_max_c"] = 48.0
    controller.run_once()

    assert app.reader("tng").requests == [48.0]


def test_only_one_decision_per_action(tmp_path):
    controller, _, _ = build(tmp_path)
    decisions = controller.decide(controller.build_context())
    actions = [decision.action for decision in decisions]

    assert len(actions) == len(set(actions))


def test_controller_survives_a_broken_rule(tmp_path):
    controller, _, _ = build(tmp_path)
    controller.rules[0].evaluate = lambda ctx: (_ for _ in ()).throw(RuntimeError("chyba"))

    result = controller.run_once()
    assert "error" in result and result["decisions"] == []


def test_decision_interval_limits_how_often_rules_run(tmp_path):
    controller, _, _ = build(tmp_path)
    controller.run_once()
    first = controller._last_run

    controller.on_sample(object())
    assert controller._last_run == first


# --- metriky --------------------------------------------------------------------

def test_metrics_report_only_documented_numbers(tmp_path):
    config = make_config(tmp_path)
    storage = JsonlStorage(config.data_dir, config.history_dir)
    from hec.analysis.summaries import Summaries
    summaries = Summaries(config, storage)
    for offset in range(1, 4):
        storage.append("summary", {
            "timestamp": to_iso(now_local() - timedelta(days=offset)), "source": "summary",
            "date": (now_local().date() - timedelta(days=offset)).isoformat(),
            "pv_kwh": 40.0, "house_kwh": 20.0, "grid_import_kwh": 5.0,
            "grid_export_kwh": 10.0, "cost_czk": 25.0, "priced": True})

    report = Metrics(config, storage, summaries).report(30)
    assert report["totals"]["pv_kwh"] == 120.0
    assert report["totals"]["self_consumption_pct"] == 75.0
    assert report["totals"]["self_sufficiency_pct"] == 75.0     # (60 − 15) / 60
    # Úspora proti hypotetickému provozu bez optimalizace se netvrdí.
    assert report["counterfactual_available"] is False
