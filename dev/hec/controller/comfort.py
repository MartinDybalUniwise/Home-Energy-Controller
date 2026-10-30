"""Cloud-only comfort guard; no passive/candidate sensors are control inputs."""
from math import isfinite

from ..core.timeutil import parse_iso, to_iso


def evaluate_comfort(saved, heatpump, moment, heating_on):
    """Observe distinct fresh samples; latch below 21 C, release at 21.5 C.

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
        return state
    previous = parse_iso(state.get('last_sample'))
    if previous and stamp <= previous:
        return state
    if previous and (stamp - previous).total_seconds() > 900:
        state.pop('below_since', None)
        state.pop('ventilation_since', None)
        previous = None
    if (previous and heating_on and (stamp - previous).total_seconds() <= 600
            and state.get('last_room', room) - room >= 0.5
            and not state.get('ventilation_since')):
        state['ventilation_since'] = to_iso(stamp)
    if room >= 21:
        state.pop('below_since', None)
        state.pop('ventilation_since', None)
        if room >= 21.5:
            state['active'] = False
    else:
        state.setdefault('below_since', to_iso(stamp))
        low_seconds = (stamp - parse_iso(state['below_since'])).total_seconds()
        vent = parse_iso(state.get('ventilation_since'))
        if low_seconds >= 900 and (vent is None or (stamp - vent).total_seconds() >= 1800):
            state['active'] = True
    state.update(last_sample=to_iso(stamp), last_room=room)
    return state
