"""Read explicit daily files; shadow the resolver with isolated state and no IO.

Use --code-root for a baseline git archive. Real telemetry/config stay outside
Git. Historical readbacks are reconstructed at recorded acknowledgements; this
does not simulate the physical effects of counterfactual decisions.
"""
import argparse
import json
import logging
import sys
import tempfile
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def read_rows(root, source, day):
    path = root / 'history' / source / f'{day}.jsonl'
    with path.open(encoding='utf-8-sig') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--code-root', type=Path)
    parser.add_argument('--day', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str((args.code_root or args.root) / 'dev'))
    from hec.controller import price as price_module
    from hec.controller.thermal import ThermalPlanner
    from hec.core.config import Config
    from hec.storage.base import atomic_write_json

    raw = json.loads((args.root / 'dev/hec/config/config.json').read_text(encoding='utf-8-sig'))
    # Explicit allowlist: never copy connection secrets into a shadow configuration.
    tng_keys = ('heating', 'thermostat', 'boiler', 'operation', 'price_shift', 'floor_check', 'write_enabled')
    config_data = dict(tng={k: deepcopy(raw['tng'][k]) for k in tng_keys},
                       ote={k: deepcopy(raw.get('ote', {}).get(k))
                            for k in ('distribution_tariff', 'fees_czk_kwh', 'vat_rate')})
    samples = read_rows(args.root, 'tng', args.day)
    commands = read_rows(args.root, 'tng_commands', args.day)
    goodwe = read_rows(args.root, 'goodwe', args.day)
    wire = read_rows(args.root, 'tng_wire', args.day)
    results, transitions, diagnostics = [], [], []
    energy_index = wire_index = command_index = 0
    last_signature = None
    pending_payloads = {}
    state = dict(DayTemperature=21.5, LastSettingsNotConfirmed=False,
                 settings=dict(heating_on=True, boiler_on=False, heating_set_temperature=42,
                               boiler_set_temperature=50, last_settings_not_confirmed=False,
                               external_circulation_pump=True))
    gates = {k: dict(awaiting_confirmation=False) for k in ('basic', 'thermostat')}
    with tempfile.TemporaryDirectory(prefix='hec-shadow-') as temp:
        work = Path(temp)
        config_data['storage'] = dict(data_path=str(work / 'data'), history_path=str(work / 'history'),
                                      logs_path=str(work / 'logs'))
        config = Config(config_data, path=work / 'config.json', root=work)
        config.ensure_dirs()
        atomic_write_json(config.path, config.data)
        price = json.loads((args.root / 'data' / f'ote-{args.day}.json').read_text(encoding='utf-8'))
        atomic_write_json(config.data_dir / f'ote-{args.day}.json', price)
        # Historical assessment known from evidence; do not inject a fresh model.
        atomic_write_json(config.data_dir / 'thermal-response.json', dict(
            assessed_at='2026-11-01T07:00:34+01:00', lead_quarters=16,
            last_outcome=dict(ready=False)))
        current = {}
        reader = SimpleNamespace(config=config, comfort_state={}, price_shift_state={},
                                 price_shift_status=None, floor_check_status={}, change_gate=gates,
                                 log=logging.getLogger('shadow'), _save_state=lambda: None,
                                 _command_audit=lambda *a, **k: None,
                                 storage=SimpleNamespace(latest=lambda name: current.get(name)))
        planner = ThermalPlanner()
        real_build = price_module.build_plan
        plan_cache = {}

        def cached_build(*positional, **named):
            key = json.dumps([positional, named], sort_keys=True)
            if key not in plan_cache:
                plan_cache[key] = real_build(*positional, **named)
            return deepcopy(plan_cache[key])

        # Do not rewrite even temporary plans: compare the same owned dated plans.
        # Device/network IO is prohibited, including accidental future code paths.
        with ExitStack() as stack, patch('hec.controller.thermal.refresh_plans', return_value=[]), \
             patch('hec.controller.price.build_plan', side_effect=cached_build), \
             patch('requests.sessions.Session.request', side_effect=AssertionError('Device/network IO in replay')):
            # State remains isolated in memory for speed; persistence/restarts are
            # exercised separately by regression tests using real atomic files.
            import importlib
            memory = {}
            for module_name in ('response', 'floor', 'dhw', 'recovery'):
                try:
                    module = importlib.import_module('hec.controller.' + module_name)
                except ModuleNotFoundError:
                    continue  # pre-repair baseline has no recovery module
                original_read = module.read_json

                def shadow_read(path, default=None, original_read=original_read):
                    key = str(path)
                    if key not in memory:
                        memory[key] = original_read(path, default)
                    return deepcopy(memory[key])

                def shadow_write(path, value):
                    memory[str(path)] = deepcopy(value)

                stack.enter_context(patch.object(module, 'read_json', side_effect=shadow_read))
                stack.enter_context(patch.object(module, 'atomic_write_json', side_effect=shadow_write))
            for hp in samples:
                moment = datetime.fromisoformat(hp['timestamp']) + timedelta(seconds=1)
                while command_index < len(commands) and datetime.fromisoformat(commands[command_index]['timestamp']) <= moment:
                    event = commands[command_index]
                    command_index += 1
                    kind = event.get('kind')
                    if event.get('phase') == 'sent' and kind in ('BASIC_SETTINGS', 'THERMOSTAT_SETTINGS'):
                        key = 'basic' if kind == 'BASIC_SETTINGS' else 'thermostat'
                        pending_payloads[key] = event['requested']
                        gates[key].update(awaiting_confirmation=True, last_post_at=event['timestamp'])
                        if key == 'basic':
                            state['settings']['last_settings_not_confirmed'] = True
                        else:
                            state['LastSettingsNotConfirmed'] = True
                    elif event.get('phase') in ('confirmed_cycle', 'confirmed_recovery') and kind in gates:
                        gates[kind]['awaiting_confirmation'] = False
                        payload = pending_payloads.get(kind, {})
                        if kind == 'basic':
                            settings = state['settings']
                            settings['last_settings_not_confirmed'] = False
                            for source, destination in (('HeatTemp_Const', 'heating_set_temperature'),
                                                        ('BoilerTemp', 'boiler_set_temperature')):
                                if source in payload:
                                    settings[destination] = payload[source]
                            for section, field, destination in (('HeatSet', 'Heat', 'heating_on'),
                                    ('HeatSet', 'ExternalCirculationPump', 'external_circulation_pump'),
                                    ('BoilerSet', 'Boiler', 'boiler_on')):
                                if field in payload.get(section, {}):
                                    settings[destination] = payload[section][field]
                        else:
                            state['LastSettingsNotConfirmed'] = False
                            state['DayTemperature'] = payload.get('DayTemperature', state['DayTemperature'])
                for records, name in ((goodwe, 'goodwe'), (wire, 'tng_wire')):
                    index = energy_index if name == 'goodwe' else wire_index
                    while index + 1 < len(records) and datetime.fromisoformat(records[index + 1]['timestamp']) <= moment:
                        index += 1
                    current[name] = records[index] if records and datetime.fromisoformat(records[index]['timestamp']) <= moment else None
                    if name == 'goodwe':
                        energy_index = index
                    else:
                        wire_index = index
                state.update(heatpump=hp, timestamp=moment.isoformat())
                plan = planner.prepare_tng(reader, state, moment)
                signature = tuple(plan[k] for k in ('mode', 'heating_temperature', 'room_target', 'phase'))
                row = dict(timestamp=hp['timestamp'], room_c=hp['room_temperature'],
                           boiler_c=hp['boiler_temperature'], mode=plan['mode'], phase=plan['phase'],
                           heating_target=plan['heating_temperature'], room_target=plan['room_target'],
                           recovery=plan.get('recovery'), dhw_catchup=plan.get('dhw_catchup'),
                           alerts=plan.get('alerts', []))
                results.append(row)
                if signature != last_signature:
                    transitions.append(row)
                    last_signature = signature
                if row['alerts'] and (not diagnostics or row['alerts'] != diagnostics[-1]['alerts']):
                    diagnostics.append(row)
    coast = [r for r in results if r['phase'] == 'coast']
    output = dict(day=args.day, rows=len(results), coast_samples=len(coast),
                  transitions=transitions, diagnostic_transitions=diagnostics,
                  afternoon_coast_samples=sum(r['timestamp'][11:16] >= '13:00' for r in coast),
                  checkpoints={time: min(results, key=lambda r: abs((datetime.fromisoformat(r['timestamp'])
                                     - datetime.fromisoformat(args.day + 'T' + time + '+01:00')).total_seconds()))
                               for time in ('09:00', '13:00', '16:10', '18:00', '20:30')},
                  limitations=['Shadow decisions on actual historical inputs, no physical counterfactual.',
                               'Readbacks reconstructed from recorded acknowledgements, initial state assumed42/21.5.',
                               'No device writes/network or production state/config changes.'])
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: output[k] for k in ('day', 'rows', 'coast_samples', 'afternoon_coast_samples')}))


if __name__ == '__main__':
    main()
