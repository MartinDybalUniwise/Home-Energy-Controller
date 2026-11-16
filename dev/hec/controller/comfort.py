"""Cloud-only comfort guard; no passive/candidate sensors are control inputs."""
from math import isfinite

from ..core.timeutil import parse_iso, to_iso


def evaluate_comfort(saved, heatpump, moment, heating_on):
    """Observe distinct fresh samples; release only after 30min stable recovery.

    Fifteen minutes continuously low triggers heating. A sudden >=0.5 C drop
    within ten minutes while heating gets thirty minutes to recover first.
    Missing/stale samples cannot advance timers or release an active guard.
    """
    state = dict(saved)
    stamp = parse_iso(heatpump.get('sample_time'))
    room = heatpump.get('room_temperature')
    if (stamp is None or stamp.tzinfo is None or moment.tzinfo is None
            or not isinstance(room, (int, float)) or isinstance(room, bool)
            or not isfinite(room) or not 0 <= room <= 40
            or not 0 <= (moment - stamp).total_seconds() <= 900):
        state.pop('recovered_since', None)
        return state
    previous = parse_iso(state.get('last_sample'))
    if previous and stamp <= previous:
        return state
    if previous and (stamp - previous).total_seconds() > 900:
        state.pop('below_since', None)
        state.pop('ventilation_since', None)
        state.pop('recovered_since', None)
        previous = None
    if (previous and heating_on and (stamp - previous).total_seconds() <= 600
            and state.get('last_room', room) - room >= 0.5
            and not state.get('ventilation_since')):
        state['ventilation_since'] = to_iso(stamp)
    # A small sustained cooling step near the floor should be handled before
    # another 15 minutes below21C. Preserve the separate sudden-ventilation wait.
    if (previous and 0 < (stamp - previous).total_seconds() <= 900
            and 21 <= room <= 21.2 and not state.get('ventilation_since')
            and state.get('last_room', room) - room >= 0.1 - 1e-9):
        state['active'] = True
        state['activation_reason'] = 'cooling_near_comfort_floor'
    if room >= 21:
        state.pop('below_since', None)
        state.pop('ventilation_since', None)
        if room >= 21.5 and state.get('active'):
            state.setdefault('recovered_since', to_iso(stamp))
            if (stamp - parse_iso(state['recovered_since'])).total_seconds() >= 1800:
                state['active'] = False
        elif room < 21.5:
            state.pop('recovered_since', None)
    else:
        state.pop('recovered_since', None)
        state.setdefault('below_since', to_iso(stamp))
        low_seconds = (stamp - parse_iso(state['below_since'])).total_seconds()
        vent = parse_iso(state.get('ventilation_since'))
        if low_seconds >= 900 and (vent is None or (stamp - vent).total_seconds() >= 1800):
            state['active'] = True
    state.update(last_sample=to_iso(stamp), last_room=room)
    return state
