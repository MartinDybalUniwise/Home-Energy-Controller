"""Activate owner-approved economics with service stopped; preserve TNG state."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hec.core import config as config_mod
from hec.core.timeutil import now_local
from hec.storage.base import read_json


def main():
    config = config_mod.load()
    tracked = {p: p.read_bytes() for p in config.data_dir.glob('tng*.json') if p.is_file()}
    raw = read_json(config.path, {})
    assert raw and tracked, 'Expected production raw config and TNG state files'
    raw.setdefault('controller', {}).update(enabled=True, decision_interval_seconds=60)
    control = raw['controller'].setdefault('optimization', {}).setdefault('goodwe_control', {})
    control.update(enabled=True, export_limit_enabled=False, on_grid_soc_limit_enabled=False)
    control['economic'] = dict(enabled=True, roundtrip_efficiency=.90, wear_czk_kwh=.30,
                               minimum_profit_czk_kwh=.50, grid_target_soc_pct=60,
                               minimum_soc_pct=20, charge_power_pct=20, max_grid_import_w=7000)
    raw.setdefault('goodwe', {}).update(writer_enabled=True, verify_after_write=True,
                                      control_state_read_enabled=True)
    errors = config_mod.save(config_mod.Config(raw, path=config.path, root=config.root), raw)
    assert not errors, errors
    assert all(path.read_bytes() == content for path, content in tracked.items()), 'TNG state changed'
    result = dict(activated_at=now_local().isoformat(), economic=control['economic'],
                  export_limits_changed=False, tng_state_preserved=True,
                  tng_state_hashes={p.name: hashlib.sha256(content).hexdigest() for p, content in tracked.items()})
    target = Path('C:/TepelneCerpadlo/hec-monitoring-evidence/battery-control-20261031/activation.json')
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
