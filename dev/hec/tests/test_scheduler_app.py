"""Testy plánovače a propojení aplikace."""

from __future__ import annotations

import time

from hec.core import config as config_mod
from hec.core import schema
from hec.core.app import Application
from hec.core.scheduler import Scheduler
from hec.readers.base import BaseReader


class CountingReader(BaseReader):
    name = "goodwe"

    def __init__(self, config, storage=None, fail=False):
        self.fail = fail
        self.count = 0
        super().__init__(config, storage)

    def interval_seconds(self):
        return 2

    def read(self):
        self.count += 1
        if self.fail:
            raise RuntimeError("zdroj nedostupný")
        return {"pv_w": 100 * self.count}


class OtherReader(CountingReader):
    name = "weather"


def make_config(tmp_path):
    data = schema.defaults()
    data["goodwe"]["enabled"] = True
    data["weather"]["enabled"] = True
    return config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)


def test_run_once_polls_every_reader(tmp_path):
    config = make_config(tmp_path)
    readers = [CountingReader(config), OtherReader(config)]
    samples = Scheduler(readers).run_once()

    assert [s.source for s in samples] == ["goodwe", "weather"]
    assert all(r.count == 1 for r in readers)


def test_failing_reader_does_not_stop_the_others(tmp_path):
    config = make_config(tmp_path)
    broken, healthy = CountingReader(config, fail=True), OtherReader(config)

    samples = Scheduler([broken, healthy]).run_once()
    assert samples[0].ok is False and samples[1].ok is True


def test_scheduler_threads_start_and_stop(tmp_path):
    config = make_config(tmp_path)
    reader = CountingReader(config)
    scheduler = Scheduler([reader])

    scheduler.start()
    time.sleep(0.3)
    scheduler.stop(timeout=3)

    assert reader.count >= 1


def test_application_wires_readers_storage_and_snapshot(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    monkeypatch.setattr("hec.core.app.build_readers",
                        lambda cfg, storage: [CountingReader(cfg, storage)])
    app = Application(config)

    app.run_once()
    current = app.current()

    assert current["sources"]["goodwe"]["pv_w"] == 100
    assert current["status"]["readers"]["goodwe"]["success_count"] == 1
    assert app.storage.latest("goodwe")["pv_w"] == 100


def test_application_restores_last_known_values_after_restart(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    monkeypatch.setattr("hec.core.app.build_readers",
                        lambda cfg, storage: [CountingReader(cfg, storage)])
    Application(config).run_once()

    restarted = Application(config)
    assert restarted.snapshot["goodwe"]["pv_w"] == 100


def test_stale_sources_are_listed_in_status(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    monkeypatch.setattr("hec.core.app.build_readers",
                        lambda cfg, storage: [CountingReader(cfg, storage)])
    app = Application(config)

    assert "goodwe" in app.status()["stale_sources"]
    app.run_once()
    assert app.status()["stale_sources"] == []
