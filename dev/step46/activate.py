"""Activate EVV1 with the production service stopped; no device IO."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import timedelta

from hec.controller.price import build_plan, earliest_quarter, refresh_plans
from hec.core import config as config_mod
from hec.core.electricity_price import load_priced_day
from hec.core.timeutil import now_local
from hec.storage.base import read_json

TARIFF = dict(
    enabled=True,
    code="EVV1",
    distributor="CEZ Distribuce",
    rate="D57d",
    valid_from="2026-10-31",
    valid_to="2026-12-31",
    verified_on="2026-10-31",
    source="Owner EVV1 weekly XLS export; CEZ distribution price list 2026 page2 rows4/5",
    price_source="https://www.cez.cz/webpublic/file/edee/ceniky/moo_ele_cez_bez_starosti_na_3_roky_01012026_12026.pdf",
    timezone="Europe/Prague",
    nt_czk_kwh=0.11650,
    vt_czk_kwh=0.75477,
    supplier_fees_verified=False,
    nt_windows=[
        dict(zip(("from", "to"), w, strict=False))
        for w in [
            ("00:00", "06:00"),
            ("07:00", "09:00"),
            ("10:00", "13:00"),
            ("14:00", "16:00"),
            ("17:00", "24:00"),
        ]
    ],
)


def main():
    config = config_mod.load()
    moment = now_local()
    raw = read_json(config.path, {})
    tracked = {p: p.read_bytes() for p in config.data_dir.glob("tng*.json") if p.is_file()}
    battery_path = config.data_dir / "battery-economic-state.json"
    if battery_path.exists():
        tracked[battery_path] = battery_path.read_bytes()
    raw["ote"]["distribution_tariff"] = TARIFF
    raw["tng"]["price_shift"]["revised_at"] = moment.isoformat()
    candidate = config_mod.Config(raw, path=config.path, root=config.root)
    for delta in (0, 1):
        day = (moment.date() + timedelta(days=delta)).isoformat()
        payload = load_priced_day(candidate, day)
        plan = build_plan(payload, day, candidate.get("tng.operation", {}), earliest_quarter(candidate, day))
        print(json.dumps(dict(date=day, prices_valid=plan["prices_valid"], phases=plan["phases"])))
        assert plan["prices_valid"], "Expected full published prices"
    if "--apply" not in sys.argv:
        return
    errors = config_mod.save(config, raw)
    assert not errors, errors
    changes = refresh_plans(config, moment)
    assert all(p.read_bytes() == content for p, content in tracked.items()), "Device state changed"
    result = dict(
        activated_at=moment.isoformat(),
        tariff=TARIFF,
        changed_days=[p["date"] for p in changes],
        device_state_preserved=True,
    )
    target = Path("C:/TepelneCerpadlo/hec-monitoring-evidence/evv1-20261031")
    target.mkdir(parents=True, exist_ok=True)
    (target / "activation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
