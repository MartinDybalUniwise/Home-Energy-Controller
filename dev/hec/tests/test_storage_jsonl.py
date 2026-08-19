"""Testy úložiště JSONL – denní soubory, dotazy, odolnost proti poškození."""

from __future__ import annotations

import json
from datetime import timedelta

from hec.core.timeutil import floor_to, now_local, to_iso
from hec.storage.jsonl import JsonlStorage
from hec.storage.series import downsample, integrate_kwh, series_fields


def make_storage(tmp_path):
    return JsonlStorage(tmp_path / "data", tmp_path / "history")


def test_append_writes_one_object_per_line(tmp_path):
    storage = make_storage(tmp_path)
    storage.append("goodwe", {"timestamp": "2026-08-19T10:00:00+02:00", "pv_w": 4210})
    storage.append("goodwe", {"timestamp": "2026-08-19T10:00:10+02:00", "pv_w": 4160})

    path = tmp_path / "history" / "goodwe" / "2026-08-19.jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["pv_w"] == 4160


def test_records_land_in_the_day_of_their_own_timestamp(tmp_path):
    storage = make_storage(tmp_path)
    storage.append("tng", {"timestamp": "2026-08-18T23:59:00+02:00", "t": 1})
    storage.append("tng", {"timestamp": "2026-08-19T00:01:00+02:00", "t": 2})

    assert storage.days("tng") == ["2026-08-18", "2026-08-19"]


def test_write_current_is_atomic(tmp_path):
    storage = make_storage(tmp_path)
    storage.write_current("weather", {"temp_c": 17.9})

    assert storage.latest("weather")["temp_c"] == 17.9
    assert list((tmp_path / "data").glob("*.tmp")) == []


def test_query_filters_by_range_and_keeps_order(tmp_path):
    storage = make_storage(tmp_path)
    base = now_local().replace(microsecond=0)
    for offset in range(5):
        storage.append("goodwe", {"timestamp": to_iso(base + timedelta(minutes=offset)),
                                  "pv_w": offset})

    result = storage.query("goodwe", base + timedelta(minutes=1), base + timedelta(minutes=3))
    assert [r["pv_w"] for r in result] == [1, 2, 3]


def test_end_exclusive_keeps_midnight_out_of_two_days(tmp_path):
    """Denní řez: vzorek přesně o půlnoci patří jen následujícímu dni."""
    storage = make_storage(tmp_path)
    midnight = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    storage.append("goodwe", {"timestamp": to_iso(midnight), "pv_w": 1})

    day_before = storage.query("goodwe", midnight - timedelta(days=1), midnight, end_exclusive=True)
    day_after = storage.query("goodwe", midnight, midnight + timedelta(days=1), end_exclusive=True)
    assert day_before == [] and len(day_after) == 1


def test_corrupted_line_does_not_break_reading(tmp_path):
    storage = make_storage(tmp_path)
    storage.append("goodwe", {"timestamp": to_iso(now_local()), "pv_w": 1})
    path = tmp_path / "history" / "goodwe" / f"{now_local():%Y-%m-%d}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"broken": \n')
    storage.append("goodwe", {"timestamp": to_iso(now_local()), "pv_w": 2})

    assert [r["pv_w"] for r in storage.query("goodwe")] == [1, 2]


def test_downsample_buckets_and_aggregates():
    # Základ zarovnaný na patnáctiminutovou hranici – jinak by výsledek testu
    # závisel na tom, v kolik hodin běží.
    base = floor_to(now_local().replace(second=0, microsecond=0), 900)
    records = [{"timestamp": to_iso(base + timedelta(seconds=step)), "pv_w": step}
               for step in (0, 60, 120, 900, 960)]

    result = downsample(records, ["pv_w"], 900, how="mean")
    assert len(result) == 2
    assert result[0]["pv_w"] == 60.0        # průměr z 0, 60, 120
    assert result[1]["pv_w"] == 930.0


def test_series_fields_ignores_text_and_booleans():
    records = [{"timestamp": "x", "source": "goodwe", "pv_w": 10, "mode": "eco", "on": True}]
    assert series_fields(records) == ["pv_w"]


def test_integrate_kwh_skips_long_gaps():
    base = now_local().replace(microsecond=0)
    records = [
        {"timestamp": to_iso(base), "power_w": 3600},
        {"timestamp": to_iso(base + timedelta(hours=1)), "power_w": 3600},
        # Hodinová mezera po výpadku měření se nedopočítává.
        {"timestamp": to_iso(base + timedelta(hours=5)), "power_w": 3600},
    ]
    assert integrate_kwh(records, "power_w", max_gap_seconds=3600) == 3.6
