import {source, finite} from './telemetry.js';

export function thermalSnapshot(current, now = new Date()) {
  const data = source(current, 'tng');
  const stamp = data.sample_time || data.timestamp;
  const age = (+now - Date.parse(stamp)) / 1000;
  const fresh = Number.isFinite(age) && age >= -60 && age <= 900;
  const temperature = (field, min, max) => {
    const value = finite(data[field]);
    return fresh && value !== null && value >= min && value <= max ? value : null;
  };
  return {timestamp:stamp, fresh,
    room:temperature('room_temperature',-20,60),
    boiler:temperature('boiler_temperature',0,100),
    water:temperature('water_output_temperature',0,90),
    boilerTarget:temperature('boiler_set_temperature',0,100),
    waterTarget:temperature('heating_set_temperature',0,90),
    heatingEnabled:fresh ? data.heating_on : null,
    boilerEnabled:fresh ? data.boiler_on : null};
}
