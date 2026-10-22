"""Regressions for impossible historical TNG temperatures (Step28)."""

from types import SimpleNamespace

import pytest
from hec.storage.jsonl import JsonlStorage
from hec.storage.series import downsample, history_record, record_values
from hec.web.api import history


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("value", [-3255.1, -3254.7, float("nan"), float("inf"), -float("inf"), True, "broken"])
def test_invalid_history_is_unknown_without_rewriting_raw_or_current(tmp_path, nested, value):
    storage = JsonlStorage(tmp_path / "data", tmp_path / "history")
    values = {"room_temperature": value, "outside_temperature": -10, "boiler_temperature": 48}
    record = {"timestamp": "2026-10-02T17:46:13+02:00", **({"values": values} if nested else values)}
    path = storage.append("tng", record)
    storage.write_current("tng", record)
    original = path.read_bytes()
    current = (storage.data_dir / "current_tng.json").read_bytes()

    for result in (storage.query("tng"), storage.last("tng")):
        assert len(result) == 1
        assert record_values(result[0])["room_temperature"] is None
        assert record_values(result[0])["outside_temperature"] == -10
        assert record_values(result[0])["boiler_temperature"] == 48
    assert path.read_bytes() == original
    assert (storage.data_dir / "current_tng.json").read_bytes() == current
    assert record_values(record)["room_temperature"] is value


@pytest.mark.parametrize("value", [-273.15, -25, 0, 19.93, 100, None])
def test_valid_values_are_not_clipped_and_other_sources_are_unchanged(value):
    record = {"room_temperature": value, "other": -3255.1}
    assert history_record("tng", record) is record
    assert history_record("other", {"room_temperature": -3255.1}) == {"room_temperature": -3255.1}


def test_api_filters_inputs_before_hourly_mean_and_keeps_a_missing_bucket(tmp_path):
    storage = JsonlStorage(tmp_path / "data", tmp_path / "history")
    for minute, value in (("15:45", 21.7), ("15:46", -3255.1), ("16:00", -3255.1), ("17:00", 0)):
        storage.append("tng", {
            "timestamp": f"2026-10-02T{minute}:00+00:00", "room_temperature": value,
            "outside_temperature": -5, "boiler_temperature": 48,
        })
    status, result = history(SimpleNamespace(storage=storage), {
        "source": "tng", "from": "2026-10-02T00:00:00+00:00", "to": "2026-10-03T00:00:00+00:00",
        "bucket": "3600",
    })
    assert status == 200 and result["raw_count"] == 4 and result["count"] == 3
    rows = result["rows"]
    assert rows[0]["room_temperature"] == 21.7
    assert rows[1].get("room_temperature") is None
    assert rows[2]["room_temperature"] == 0
    assert all(row["outside_temperature"] == -5 for row in rows)
    raw = storage.query("tng")
    assert downsample(raw, ["room_temperature"], 0)[1]["room_temperature"] is None


def test_all_missing_temperature_columns_remain_available_in_api(tmp_path):
    storage = JsonlStorage(tmp_path / "data", tmp_path / "history")
    fields = ["outside_temperature", "water_output_temperature", "boiler_temperature", "room_temperature"]
    storage.append("tng", {"timestamp": "2026-10-02T15:00:00Z", **dict.fromkeys(fields, -3255.1)})
    _, result = history(SimpleNamespace(storage=storage), {
        "source": "tng", "from": "2026-10-02T00:00:00Z", "to": "2026-10-03T00:00:00Z",
    })
    assert result["fields"] == fields
    assert len(result["rows"]) == 1
    assert all(result["rows"][0].get(field) is None for field in fields)
