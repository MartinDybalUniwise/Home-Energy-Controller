"""Testy webového API – bez otevírání soketu, přímo na vrstvě api.py."""

from __future__ import annotations

import json
from datetime import timedelta

from hec.core import config as config_mod
from hec.core import schema
from hec.core.timeutil import now_local, to_iso
from hec.storage.jsonl import JsonlStorage
from hec.web import api


class FakeApp:
    def __init__(self, tmp_path):
        data = schema.defaults()
        data["goodwe"]["enabled"] = True
        self.config = config_mod.Config(data, path=tmp_path / "config.json", root=tmp_path)
        self.config.ensure_dirs()
        self.storage = JsonlStorage(self.config.data_dir, self.config.history_dir)
        self.snapshot = {}

    def current(self):
        return {"timestamp": to_iso(now_local()), "sources": self.snapshot, "status": self.status()}

    def status(self):
        return {"readers": {}, "stale_sources": [], "controller": {"enabled": False}}


def seed(app, minutes=60, step=10):
    base = now_local() - timedelta(minutes=minutes)
    for index in range(minutes * 60 // step):
        app.storage.append("goodwe", {
            "timestamp": to_iso(base + timedelta(seconds=index * step)),
            "source": "goodwe", "pv_w": 1000 + index, "house_w": 500,
        })


def test_parse_moment_accepts_relative_and_iso():
    now = now_local()
    assert api.parse_moment("-24h", now) < now
    assert api.parse_moment("today", now).hour == 0
    assert api.parse_moment("2026-08-19T10:00:00+02:00", now).hour == 10
    assert api.parse_moment(None, now) == now


def test_auto_bucket_grows_with_range():
    assert api.auto_bucket(3600) == 60
    assert api.auto_bucket(24 * 3600) == 300
    assert api.auto_bucket(7 * 86400) == 900
    assert api.auto_bucket(30 * 86400) == 3600


def test_history_requires_source(tmp_path):
    status, payload = api.history(FakeApp(tmp_path), {})
    assert status == 400 and payload["error"] == "missing_source"


def test_history_downsamples_for_the_client(tmp_path):
    app = FakeApp(tmp_path)
    seed(app)

    status, payload = api.history(app, {"source": "goodwe", "from": "-2h", "to": "now"})
    assert status == 200
    assert payload["raw_count"] == 360           # 60 minut po 10 s
    assert payload["bucket_seconds"] == 60
    assert payload["count"] <= 61                # zhuštěno na minutové koše
    assert "pv_w" in payload["fields"]


def test_history_swaps_reversed_range(tmp_path):
    app = FakeApp(tmp_path)
    seed(app)
    status, payload = api.history(app, {"source": "goodwe", "from": "now", "to": "-2h"})
    assert status == 200 and payload["from"] < payload["to"]


def test_config_get_hides_secrets(tmp_path):
    app = FakeApp(tmp_path)
    app.config.data["web"]["password"] = "tajne-heslo-123"

    _, payload = api.config_get(app)
    assert "tajne-heslo-123" not in json.dumps(payload)


def test_config_put_validates_and_saves(tmp_path):
    app = FakeApp(tmp_path)
    app.config.path.write_text(json.dumps(app.config.data), encoding="utf-8")

    status, payload = api.config_put(app, {"config": {"polling": {"goodwe_seconds": 1}}})
    assert status == 400 and payload["errors"]

    status, payload = api.config_put(app, {"config": {"polling": {"goodwe_seconds": 30}}})
    assert status == 200
    assert json.loads(app.config.path.read_text(encoding="utf-8"))["polling"]["goodwe_seconds"] == 30


def test_config_put_never_writes_back_masked_secret(tmp_path):
    app = FakeApp(tmp_path)
    app.config.data["web"]["password"] = "tajne-heslo-123"
    app.config.path.write_text(json.dumps(app.config.data), encoding="utf-8")

    api.config_put(app, {"config": {"web": {"password": "ta***23 (15)"}}})
    assert app.config.get("web.password") == "tajne-heslo-123"


def test_config_put_reports_fields_needing_restart(tmp_path):
    app = FakeApp(tmp_path)
    app.config.path.write_text(json.dumps(app.config.data), encoding="utf-8")

    _, payload = api.config_put(app, {"config": {"web": {"port": 9099}}})
    assert "web.port" in payload["restart_required"]


def test_prediction_is_optional_until_the_module_exists(tmp_path):
    status, payload = api.prediction(FakeApp(tmp_path))
    assert status == 200 and payload["available"] is False


def test_translations_serves_catalogs():
    status, payload = api.translations("cs")
    assert status == 200 and payload["catalog"]["nav"]["overview"] == "Přehled"

    status, payload = api.translations("xx")
    assert status == 404 and "cs" in payload["available"]


def test_logs_requires_source(tmp_path):
    status, payload = api.logs(FakeApp(tmp_path), {})
    assert status == 400 and payload["error"] == "missing_source"


def test_logs_tail_returns_last_records_unaggregated(tmp_path):
    """Na rozdíl od /api/history se tady nic nezhušťuje – je to pro ruční kontrolu."""
    app = FakeApp(tmp_path)
    seed(app)

    status, payload = api.logs(app, {"source": "goodwe", "tail": "5"})
    assert status == 200
    assert payload["count"] == 5
    assert payload["rows"][-1]["pv_w"] == 1359          # poslední zapsaný vzorek


def test_logs_tail_is_capped(tmp_path):
    app = FakeApp(tmp_path)
    seed(app)

    _, payload = api.logs(app, {"source": "goodwe", "tail": "999999"})
    assert payload["count"] == 360                       # tolik vzorků seed() vytvoří


def test_logs_for_a_specific_day_is_not_downsampled(tmp_path):
    app = FakeApp(tmp_path)
    seed(app)
    day = now_local().date().isoformat()

    status, payload = api.logs(app, {"source": "goodwe", "day": day})
    assert status == 200
    assert payload["day"] == day
    assert payload["count"] == payload["rows"].__len__() > 0


def test_log_days_requires_source(tmp_path):
    status, payload = api.log_days(FakeApp(tmp_path), {})
    assert status == 400 and payload["error"] == "missing_source"


def test_log_days_lists_available_days(tmp_path):
    app = FakeApp(tmp_path)
    seed(app)

    _, payload = api.log_days(app, {"source": "goodwe"})
    assert payload["days"] == [now_local().date().isoformat()]


def test_log_days_empty_for_unknown_source(tmp_path):
    _, payload = api.log_days(FakeApp(tmp_path), {"source": "nikdy_nepsano"})
    assert payload["days"] == []
