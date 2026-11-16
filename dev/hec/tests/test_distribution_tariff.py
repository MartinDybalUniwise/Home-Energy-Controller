from copy import deepcopy
from datetime import datetime

import pytest
from hec.controller.battery import charging_windows
from hec.controller.price import build_plan
from hec.core.electricity_price import load_priced_day, priced_day
from hec.readers.price_snapshot import cached_price_snapshot
from hec.storage.base import atomic_write_json
from test_readers_ote_tng import make_config

DAY = "2026-11-01"
WINDOWS = [("00:00", "06:00"), ("07:00", "09:00"), ("10:00", "13:00"), ("14:00", "16:00"), ("17:00", "24:00")]


def configured(tmp_path):
    return make_config(
        tmp_path,
        ote={
            "distribution_tariff": dict(
                enabled=True,
                code="EVV1",
                valid_from="2026-10-31",
                valid_to="2026-12-31",
                nt_czk_kwh=0.11650,
                vt_czk_kwh=0.75477,
                nt_windows=[dict(zip(("from", "to"), w, strict=True)) for w in WINDOWS],
            )
        },
    )


def curve():
    def clock(i):
        return f"{i // 4:02}:{i % 4 * 15:02}"

    return dict(
        date=DAY,
        eur_czk_rate=24.36,
        periods=[
            dict(
                start=clock(i),
                end=clock(i + 1),
                price_eur_mwh=240,
                price_czk_kwh=5.8464,
                price_total_czk_kwh=7.0741,
            )
            for i in range(96)
        ],
    )


@pytest.mark.parametrize(
    "index,tariff",
    [
        (0, "NT"),
        (23, "NT"),
        (24, "VT"),
        (27, "VT"),
        (28, "NT"),
        (35, "NT"),
        (36, "VT"),
        (39, "VT"),
        (40, "NT"),
        (51, "NT"),
        (52, "VT"),
        (55, "VT"),
        (56, "NT"),
        (63, "NT"),
        (64, "VT"),
        (67, "VT"),
        (68, "NT"),
        (95, "NT"),
    ],
)
def test_all_exact_boundaries(tmp_path, index, tariff):
    config = configured(tmp_path)
    raw = curve()
    original = deepcopy(raw)
    result = priced_day(config, raw)
    assert result["periods"][index]["distribution_tariff"] == tariff
    assert sum(r["distribution_tariff"] == "NT" for r in result["periods"]) == 80
    assert raw == original
    assert priced_day(config, result) == result  # no double distribution or VAT
    fee = 0.11650 if tariff == "NT" else 0.75477
    assert result["periods"][index]["price_total_czk_kwh"] == round((5.8464 + fee) * 1.21, 4)


def test_existing_cache_and_fast_snapshot_use_same_price_without_rewriting(tmp_path):
    config = configured(tmp_path)
    path = config.data_dir / f"ote-{DAY}.json"
    atomic_write_json(path, curve())
    before = path.read_bytes()
    payload = load_priced_day(config, DAY)
    snapshot = cached_price_snapshot(config, {}, datetime.fromisoformat(DAY + "T06:00:00+01:00"))
    assert snapshot["price_total_czk_kwh"] == payload["periods"][24]["price_total_czk_kwh"]
    assert path.read_bytes() == before


def test_real_tariff_edge_preheats_before_six_not_at_six(tmp_path):
    payload = priced_day(configured(tmp_path), curve())
    phases = build_plan(payload, DAY, {})["phases"]
    assert phases[:2] == [dict(start=16, end=24, kind="preheat"), dict(start=24, end=28, kind="coast")]
    assert all(
        payload["periods"][i]["distribution_tariff"] == "NT"
        for p in phases
        if p["kind"] == "preheat"
        for i in range(p["start"], p["end"])
    )
    assert not charging_windows(payload, DAY, {})[0]  # tariff alone cannot pay battery losses


def test_expired_or_invalid_tariff_cannot_drive_economic_plan(tmp_path):
    config = configured(tmp_path)
    for change in (
        {"valid_to": "2026-10-31"},
        {"vt_czk_kwh": float("nan")},
        {"nt_windows": [{"from": "00:00", "to": "99:00"}]},
    ):
        altered = deepcopy(config.data["ote"]["distribution_tariff"])
        config.data["ote"]["distribution_tariff"].update(change)
        payload = priced_day(config, curve())
        assert not payload["distribution_pricing"]["valid"]
        assert not build_plan(payload, DAY, {})["prices_valid"]
        assert not charging_windows(payload, DAY, {})[0]
        config.data["ote"]["distribution_tariff"] = altered


def test_disabled_tariff_preserves_legacy_contract(tmp_path):
    config = configured(tmp_path)
    config.data["ote"]["distribution_tariff"]["enabled"] = False
    assert priced_day(config, curve()) == curve()
