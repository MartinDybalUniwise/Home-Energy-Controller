import {source, finite} from './telemetry.js';

export function thermalSnapshot(current, now = new Date()) {
  const data = source(current, 'tng');
  const wire = source(current,'tng_wire');
  const wireAge = (+now-Date.parse(wire.sample_time || wire.timestamp))/1000;
  const wireFresh = Number.isFinite(wireAge) && wireAge >= -5 && wireAge <= 180;
  const stamp = data.sample_time || data.timestamp;
  const age = (+now - Date.parse(stamp)) / 1000;
  const fresh = Number.isFinite(age) && age >= -60 && age <= 900;
  const temperature = (field, min, max) => {
    const passive = finite(wire[field]);
    if (wireFresh && passive !== null && passive >= min && passive <= max &&
        wire.field_quality?.[field] !== 'outside_verified_range') return passive;
    const value = finite(data[field]);
    return fresh && value !== null && value >= min && value <= max ? value : null;
  };
  return {timestamp:wireFresh ? wire.sample_time : stamp, fresh:fresh || wireFresh,
    room:temperature('room_temperature',-20,60),
    boiler:temperature('boiler_temperature',0,100),
    buffer:temperature('buffer_temperature',0,90),
    water:temperature('water_output_temperature',0,90),
    boilerTarget:temperature('boiler_set_temperature',0,100),
    waterTarget:temperature('heating_set_temperature',0,90),
    heatingEnabled:fresh ? data.heating_on : null,
    boilerEnabled:fresh ? data.boiler_on : null};
}
