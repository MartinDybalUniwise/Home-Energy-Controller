"""Seed response from bounded confirmed history; activate only while HEC is stopped."""

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hec.controller.price import refresh_plans
from hec.controller.response import preheat_quarters, required_quarters
from hec.core import config as config_mod
from hec.core.timeutil import now_local, parse_iso
from hec.storage.base import atomic_write_json, read_json


def records(path):
    if not path.exists():
        return []
    result = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                result.append(json.loads(line))
            except ValueError:
                pass
    return result


def response_evidence(config, moment):
    day = moment.date().isoformat()
    commands = records(config.history_dir / "tng_commands" / f"{day}.jsonl")
    acks = [
        r
        for r in commands
        if r.get("phase") == "confirmed_recovery"
        and r.get("kind") == "thermostat"
        and r.get("requested", {}).get("day_temperature") == 21.7
    ]
    phases = (
        config.get("tng.thermostat.date_overrides", {}).get(day, {}).get("price_shift", {}).get("phases", [])
    )
    data = records(config.history_dir / "tng" / f"{day}.jsonl")
    for phase in phases:
        if phase["kind"] != "preheat":
            continue
        base = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        start = base + timedelta(minutes=phase["start"] * 15)
        end = base + timedelta(minutes=phase["end"] * 15)
        if end > moment:
            continue
        ack = next(
            (parse_iso(r["timestamp"]) for r in acks if start <= parse_iso(r["timestamp"]) < end), None
        )
        if ack is None:
            continue
        samples = {}
        for row in data:
            stamp = parse_iso(row.get("timestamp"))
            room = row.get("room_temperature")
            if (
                stamp
                and ack <= stamp < end
                and isinstance(room, (int, float))
                and not isinstance(room, bool)
                and 0 <= room <= 40
            ):
                samples[stamp] = room
        pairs = sorted(samples.items())
        if len(pairs) < 6:
            continue
        duration = (pairs[-1][0] - pairs[0][0]).total_seconds()
        if duration < 3600 or any((b[0] - a[0]).total_seconds() > 900 for a, b in zip(pairs, pairs[1:], strict=False)):
            continue
        return dict(
            lead_quarters=required_quarters(pairs[0][1], pairs[-1][1], duration),
            assessed_at=moment.isoformat(),
            last_outcome=dict(
                day=day,
                first_room=pairs[0][1],
                last_room=pairs[-1][1],
                observed_minutes=duration / 60,
                ready=pairs[-1][1] >= 21.5,
                confirmed_at=ack.isoformat(),
                first_at=pairs[0][0].isoformat(),
                last_at=pairs[-1][0].isoformat(),
                evidence="confirmed_thermostat_and_room_samples",
            ),
        )
    return None


def main():
    config = config_mod.load()
    moment = now_local()
    evidence = response_evidence(config, moment)
    print(json.dumps(dict(response_evidence=evidence)))
    if "--apply" not in sys.argv:
        return
    tracked = {p: p.read_bytes() for p in config.data_dir.glob("tng*.json") if p.is_file()}
    memory = config.data_dir / "battery-economic-state.json"
    if memory.exists():
        tracked[memory] = memory.read_bytes()
    if evidence:
        previous = read_json(config.data_dir / "thermal-response.json", {}) or {}
        evidence["lead_quarters"] = max(preheat_quarters(config, moment), evidence["lead_quarters"])
        if previous.get("active"):
            evidence["active"] = previous["active"]
        atomic_write_json(config.data_dir / "thermal-response.json", evidence)
    raw = read_json(config.path, {})
    raw["tng"]["price_shift"]["revised_at"] = moment.isoformat()
    errors = config_mod.save(config, raw)
    assert not errors, errors
    changes = refresh_plans(config, moment)
    assert all(p.read_bytes() == data for p, data in tracked.items()), "TNG/battery state changed"
    result = dict(
        activated_at=moment.isoformat(),
        response=evidence,
        changed_days=[p["date"] for p in changes],
        device_state_preserved=True,
    )
    target = Path("C:/TepelneCerpadlo/hec-monitoring-evidence/coordinated-peaks-20261101")
    target.mkdir(parents=True, exist_ok=True)
    (target / "activation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
