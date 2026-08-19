"""Testy chování readerů: izolace chyb, backoff, stav, ukládání."""

from __future__ import annotations

from hec.core import config as config_mod
from hec.core import schema
from hec.readers.base import BaseReader, slug
from hec.storage.jsonl import JsonlStorage


class FlakyReader(BaseReader):
    name = "goodwe"

    def __init__(self, config, storage=None, fail_times=0):
        self.fail_times = fail_times
        self.calls = 0
        super().__init__(config, storage)

    def read(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("měnič neodpovídá")
        return {"pv_w": 4210, "battery_soc": 91}


def make_config(tmp_path, **overrides):
    data = schema.defaults()
    data["goodwe"]["enabled"] = True
    for key, value in overrides.items():
        data["goodwe"][key] = value
    return config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)


def test_failure_is_reported_not_raised(tmp_path):
    reader = FlakyReader(make_config(tmp_path), fail_times=1)

    sample = reader.poll()
    assert sample.ok is False
    assert "ConnectionError" in sample.error
    assert reader.status.error_count == 1
    assert reader.status.last_success is None


def test_backoff_grows_with_failures_and_resets_on_success(tmp_path):
    reader = FlakyReader(make_config(tmp_path), fail_times=3)
    interval = reader.interval_seconds()

    reader.poll()
    first = reader.backoff_seconds()
    reader.poll()
    second = reader.backoff_seconds()
    assert second > first >= interval

    reader.poll()
    reader.poll()
    assert reader.status.last_success is not None
    assert reader.backoff_seconds() == float(interval)


def test_backoff_is_capped(tmp_path):
    reader = FlakyReader(make_config(tmp_path), fail_times=99)
    for _ in range(12):
        reader.poll()
    assert reader.backoff_seconds() <= 600


def test_successful_poll_persists_current_and_history(tmp_path):
    config = make_config(tmp_path)
    storage = JsonlStorage(config.data_dir, config.history_dir)
    reader = FlakyReader(config, storage=storage)

    reader.poll()

    assert storage.latest("goodwe")["pv_w"] == 4210
    assert len(storage.query("goodwe")) == 1


def test_stale_flag_uses_three_intervals(tmp_path):
    reader = FlakyReader(make_config(tmp_path))
    assert reader.status.is_stale is True          # zatím žádné čtení
    reader.poll()
    assert reader.status.is_stale is False


def test_disabled_reader_is_never_stale(tmp_path):
    """Vypnutý zdroj nesmí strhnout systém do bezpečného režimu."""
    config = config_mod.Config(schema.defaults(), path=tmp_path / "c.json", root=tmp_path)
    reader = FlakyReader(config)
    assert reader.status.enabled is False
    assert reader.status.is_stale is False


def test_slug_handles_czech_names():
    assert slug("Myčka nádobí") == "mycka_nadobi"
    assert slug("TČ – Pro 3EM") == "tc_pro_3em"
    assert slug("???") == "device"
