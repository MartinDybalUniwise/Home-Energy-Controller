import {source, finite} from './telemetry.js';

const recent=(data,now,seconds,tolerance)=>{
  const timestamp=data.sample_time||data.timestamp;
  const age=(+now-Date.parse(timestamp))/1000;
  return Number.isFinite(age)&&age>=-tolerance&&age<=seconds;
};
// A plausible low passive value can be an aliased high branch. Until branch
// selection is verified, these fields must never fall back to that candidate.
const CLOUD_ONLY=new Set(['boiler_temperature','water_output_temperature',
  'boiler_set_temperature','heating_set_temperature']);
export function temperatureReading(current,field,now=new Date()) {
  const cloud=source(current,'tng'),wire=source(current,'tng_wire');
  const reading=(data,origin)=>({value:finite(data[field]),origin,timestamp:data.sample_time||data.timestamp});
  const cloudReading=recent(cloud,now,900,60)&&finite(cloud[field])!==null?reading(cloud,'cloud'):null;
  if(CLOUD_ONLY.has(field))return cloudReading;
  // Owner request: AKU display is independent of the old photo-reference range.
  const displayable=field==='buffer_temperature'||wire.field_quality?.[field]!=='outside_verified_range';
  if(recent(wire,now,180,5)&&finite(wire[field])!==null&&displayable)return reading(wire,'wire');
  return cloudReading;
}

export function thermalSnapshot(current, now = new Date()) {
  const cloud=source(current,'tng'),fresh=recent(cloud,now,900,60);
  const timestamps={};
  const temperature=(field,min,max)=>{
    const result=temperatureReading(current,field,now);
    if(!result||result.value<min||result.value>max)return null;
    timestamps[field]=result.timestamp;
    return result.value;
  };
  const values={room:temperature('room_temperature',-20,60),
    boiler:temperature('boiler_temperature',0,100),
    buffer:temperature('buffer_temperature',0,90),
    water:temperature('water_output_temperature',0,90),
    boilerTarget:temperature('boiler_set_temperature',0,100),
    waterTarget:temperature('heating_set_temperature',0,90),
    heatingEnabled:fresh?cloud.heating_on:null,
    boilerEnabled:fresh?cloud.boiler_on:null};
  // The shared timestamp must not make an older cloud reading appear newer.
  const stamps=Object.values(timestamps).filter(s=>Number.isFinite(Date.parse(s))).sort((a,b)=>Date.parse(a)-Date.parse(b));
  return {...values,timestamps,timestamp:stamps[0]||null,fresh:stamps.length>0};
}
