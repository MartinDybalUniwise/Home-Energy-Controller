"""Persistent cloud-only readiness and response evidence for the sole resolver.

Confirmed demand is not measured compressor/pump activity. Nothing here sends IO
to a device or uses passive AKU as an unrestricted control input.
"""
from copy import deepcopy
from zoneinfo import ZoneInfo

from ..core.timeutil import parse_iso
from ..storage.base import atomic_write_json, read_json
from .floor import number


def fresh_sample(hp, moment):
    stamp = parse_iso(hp.get('sample_time'))
    room = hp.get('room_temperature')
    if (stamp is None or stamp.tzinfo is None or not number(room)
            or not 0 <= room <= 40 or not 0 <= (moment - stamp).total_seconds() <= 900):
        return None
    return stamp


def observe_recovery(config, state, gates, comfort, moment):
    path = config.data_dir / 'thermal-recovery-state.json'
    saved = read_json(path, {}) or {}
    original = deepcopy(saved)
    hp, settings = state.get('heatpump') or {}, state.get('settings') or {}
    stamp = fresh_sample(hp, moment)
    day = moment.astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
    if saved.get('day') != day:
        saved.update(day=day, day_blocked=bool(saved.get('response_fault')))
    # Retain protection on stale data; no missing interval proves warm recovery.
    previous = parse_iso(saved.get('last_sample'))
    if stamp is None:
        saved.pop('warm_since', None)
        saved.pop('response', None)
        saved.pop('preheat', None)
    elif previous is None or stamp > previous:
        room = hp['room_temperature']
        if previous is None or (stamp - previous).total_seconds() > 900:
            for key in ('warm_since', 'response', 'preheat'):
                saved.pop(key, None)
        if room < 21 or comfort.get('active'):
            saved['day_blocked'] = True
        if room >= 21.5:
            saved.setdefault('warm_since', stamp.isoformat())
        else:
            saved.pop('warm_since', None)
        confirmed = (
            config.get('tng.write_enabled', False)
            and config.get('tng.heating.enabled', False)
            and config.get('tng.thermostat.enabled', False)
            and settings.get('heating_on') is True and settings.get('boiler_on') is False
            and settings.get('last_settings_not_confirmed') is False
            and state.get('LastSettingsNotConfirmed') is False
            and all(gates.get(k, {}).get('awaiting_confirmation') is False for k in ('basic', 'thermostat'))
            and number(settings.get('heating_set_temperature'))
            and 41.9 <= settings['heating_set_temperature'] <= 42
            and number(state.get('DayTemperature')) and state['DayTemperature'] >= 21.5
        )
        if confirmed and room < 21.5:
            run = saved.setdefault('response', dict(first_at=stamp.isoformat(), first_room=room))
            minutes = (stamp - parse_iso(run['first_at'])).total_seconds() / 60
            run.update(minutes=round(minutes, 1), room_gain_c=round(room - run['first_room'], 2))
            if minutes >= 60 and (room < 21 or (room <= 21.3 and room - run['first_room'] < .1 - 1e-9)):
                saved.update(response_fault=True, day_blocked=True)
                saved.setdefault('response_fault_since', stamp.isoformat())
        else:
            saved.pop('response', None)
        # Count only acknowledged heating during the actual owned preheat block.
        local = moment.astimezone(ZoneInfo('Europe/Prague'))
        meta = config.get('tng.heating.date_overrides', {}).get(day, {}).get('price_shift', {})
        index = local.hour * 4 + local.minute // 15
        phase = next((p for p in meta.get('phases', [])
                      if p['kind'] == 'preheat' and p['start'] <= index < p['end']), None)
        pre = saved.get('preheat') or {}
        if confirmed and phase and 21.65 <= state['DayTemperature'] <= 21.75:
            key = f"{day}:{phase['start']}"
            if pre.get('key') != key:
                pre = dict(key=key, first_at=stamp.isoformat(), first_room=room, minutes=0)
            pre.update(last_at=stamp.isoformat(), last_room=room,
                       minutes=round((stamp - parse_iso(pre['first_at'])).total_seconds() / 60, 1))
            saved['preheat'] = pre
        elif phase:
            saved.pop('preheat', None)
        if room >= 21.5 and saved.get('warm_since'):
            if (stamp - parse_iso(saved['warm_since'])).total_seconds() >= 1800:
                saved['response_fault'] = False
                saved.pop('response_fault_since', None)
        saved.update(last_sample=stamp.isoformat(), last_room=room)
    warm = parse_iso(saved.get('warm_since'))
    stable = bool(stamp and warm and 0 <= (stamp - warm).total_seconds() and
                  (stamp - warm).total_seconds() >= 1800)
    pre = saved.get('preheat') or {}
    end = parse_iso(pre.get('last_at'))
    recent_preheat = bool(stamp and end and 0 <= (stamp - end).total_seconds() <= 900
                          and pre.get('key', '').startswith(day + ':')
                          and pre.get('minutes', 0) >= 60
                          and pre.get('last_room', 0) >= 21.5
                          and pre.get('last_room', 0) >= pre.get('first_room', 40))
    model = read_json(config.data_dir / 'thermal-response.json', {}) or {}
    assessed = parse_iso(model.get('assessed_at'))
    model_fresh = bool(assessed and 0 <= (moment - assessed).total_seconds() <= 7 * 86400
                       and model.get('last_outcome', {}).get('ready') is True)
    ready = bool(stamp and stable and recent_preheat and model_fresh
                 and not saved.get('day_blocked') and not saved.get('response_fault')
                 and settings.get('heating_on') is True and settings.get('boiler_on') is False
                 and settings.get('last_settings_not_confirmed') is False
                 and state.get('LastSettingsNotConfirmed') is False
                 and all(gates.get(k, {}).get('awaiting_confirmation') is False for k in ('basic', 'thermostat')))
    if saved != original:
        atomic_write_json(path, saved)
    return dict(day_blocked=bool(saved.get('day_blocked')), stable_recovery=stable,
                coast_ready=ready, confirmed_preheat_minutes=pre.get('minutes', 0),
                response_model_fresh=model_fresh, response_fault=bool(saved.get('response_fault')),
                response_fault_since=saved.get('response_fault_since'),
                response=saved.get('response'), evidence='cloud_settings_and_room_samples',
                compressor_run_measured=False, pump_run_measured=False,
                last_sample=saved.get('last_sample'))
