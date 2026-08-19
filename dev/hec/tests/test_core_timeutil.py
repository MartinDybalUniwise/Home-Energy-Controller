"""Testy práce s časem – všechny značky musí nést časovou zónu."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hec.core import timeutil


def test_parse_iso_accepts_zulu_and_offset():
    assert timeutil.parse_iso("2026-08-18T10:51:23Z").utcoffset() == timedelta(0)
    assert timeutil.parse_iso("2026-08-18T12:51:23+02:00").hour == 12
    assert timeutil.parse_iso("nesmysl") is None
    assert timeutil.parse_iso(None) is None


def test_naive_timestamp_gets_local_zone():
    parsed = timeutil.parse_iso("2026-08-18T12:00:00")
    assert parsed.tzinfo is not None


def test_age_seconds_never_negative():
    future = timeutil.now_local() + timedelta(seconds=30)
    assert timeutil.age_seconds(future) == 0.0
    assert timeutil.age_seconds(timeutil.now_local() - timedelta(seconds=60)) >= 59


def test_floor_to_aligns_to_interval():
    moment = datetime(2026, 8, 18, 12, 47, 33, tzinfo=UTC)
    assert timeutil.floor_to(moment, 900) == datetime(2026, 8, 18, 12, 45, tzinfo=UTC)


def test_in_window_matches_legacy_behaviour():
    now = datetime(2026, 8, 18, 23, 30)
    assert timeutil.in_window(now, "22:00", "06:00") is True
    assert timeutil.in_window(now, "06:00", "22:00") is False
