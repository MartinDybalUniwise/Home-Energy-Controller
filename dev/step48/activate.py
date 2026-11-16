"""Enable the owner's hourly floor check while the original service is stopped."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hec.core import config as config_mod
from hec.core.timeutil import now_local
from hec.storage.base import read_json


def main():
    config = config_mod.load()
    assert config.get("controller.enabled") and config.get("tng.write_enabled")
    assert config.get("tng.heating.enabled") and config.get("tng.thermostat.enabled")
    tracked = {p: p.read_bytes() for p in config.data_dir.glob("tng*.json") if p.is_file()}
    for name in ("battery-economic-state.json", "floor-circulation-state.json"):
        p = config.data_dir / name
        if p.exists():
            tracked[p] = p.read_bytes()
    raw = read_json(config.path, {})
    old = raw.get("tng", {}).get("floor_check", {})
    activated = old.get("activated_at") if old.get("enabled") else now_local().isoformat()
    values = dict(
        enabled=True,
        activated_at=activated,
        idle_minutes=60,
        probe_minutes=15,
        max_cycle_minutes=45,
        minimum_aku_c=35,
        recovery_aku_c=38,
        water_target_c=42,
        room_request_offset_c=0.5,
        maximum_room_request_c=24,
    )
    raw["tng"]["floor_check"] = values
    errors = config_mod.save(config, raw)
    assert not errors, errors
    assert all(p.read_bytes() == content for p, content in tracked.items()), "Device runtime state changed"
    result = dict(
        activated_at=now_local().isoformat(),
        floor_check=values,
        device_state_preserved=True,
        activity_basis="owner_assumption_from_thermostat_demand",
        separate_scheduler_created=False,
    )
    target = Path("C:/TepelneCerpadlo/hec-monitoring-evidence/hourly-floor-20261101")
    target.mkdir(parents=True, exist_ok=True)
    (target / "activation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
