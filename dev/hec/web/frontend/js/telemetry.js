// Shared observational semantics: no physical control or guessed measurements.
import { t, power } from './i18n.js';

export function finite(value) {
  return (typeof value === 'number' || (typeof value === 'string' && value.trim() !== ''))
    && Number.isFinite(Number(value)) ? Number(value) : null;
}

export function source(current, name) {
  const value = current?.sources?.[name] || {};
  const reader = current?.status?.readers?.[name] || {};
  if (reader.enabled === false) return {};
  const stale = current?.status?.stale_sources?.includes(name);
  const failed = value.online === false || value.ok === false || reader.state === 'error' || !!reader.last_error;
  if (!stale && !failed) return value;
  if (name !== 'shelly') return {};
  const state = failed ? 'offline' : 'stale';
  const metadata = {...(value.devices || {}), ...(value.device_status || {})};
  return {heatpump_quality: state, device_status: Object.fromEntries(Object.entries(metadata)
    .map(([key, device]) => [key, {role: device.role, appliance_type: device.appliance_type, quality: state, timestamp: device.timestamp}]))};
}

export function quality(device) {
  if (!device) return 'missing';
  if (device.measurement_quality && device.measurement_quality !== 'valid') return device.measurement_quality;
  const watts = finite(device.power_w);
  if (watts === null) return 'missing';
  if (watts < 0) return 'negative';
  if (['l1_v', 'l2_v', 'l3_v'].some(key => finite(device[key]) !== null && finite(device[key]) <= 0)) return 'phase';
  return 'valid';
}

// Both energy pages consume the same validity rules without changing raw data.
export function energySnapshot(current) {
  const raw = source(current, 'goodwe');
  const result = {...raw};
  for (const key of ['pv_w', 'house_w', 'grid_import_w', 'grid_export_w',
    'battery_charge_w', 'battery_discharge_w', 'battery_soc']) {
    const value = finite(raw[key]);
    result[key] = value !== null && value >= 0 && (key !== 'battery_soc' || value <= 100) ? value : null;
  }
  for (const [a,b] of [['grid_import_w','grid_export_w'],['battery_charge_w','battery_discharge_w']]) {
    if (result[a] === null || result[b] === null || (result[a] > 20 && result[b] > 20)) {
      result[a] = null; result[b] = null;
    }
  }
  return result;
}

export function heatpumpPower(shelly) {
  return heatpumpQuality(shelly) === 'valid' ? finite(shelly.heatpump_power_w) : null;
}

export function heatpumpQuality(shelly) {
  if (shelly.heatpump_quality && shelly.heatpump_quality !== 'valid') return shelly.heatpump_quality;
  const meters = Object.values(shelly.devices || {}).filter(d => d.role === 'heatpump_meter');
  const bad = meters.map(quality).find(q => q !== 'valid');
  return bad || quality({ power_w: shelly.heatpump_power_w });
}

export function heatpumpText(shelly) {
  const q = heatpumpQuality(shelly);
  if (q !== 'valid') return t(`meter.${q}`);
  return t(finite(shelly.heatpump_power_w) >= 200 ? 'flow.running_estimate' : 'flow.low_power');
}

export function heatingPermission(tng) {
  return t(tng.heating_on === true ? 'flow.heating_enabled'
    : tng.heating_on === false ? 'flow.heating_disabled' : 'meter.missing');
}

export function batteryText(goodwe) {
  const charge = finite(goodwe.battery_charge_w), discharge = finite(goodwe.battery_discharge_w);
  if (charge === null || discharge === null || (charge > 20 && discharge > 20)) return t('meter.missing');
  return t(charge > 20 ? 'flow.charging' : discharge > 20 ? 'flow.discharging' : 'flow.idle');
}

export function batteryReason(goodwe) {
  const soc = finite(goodwe.battery_soc), reserve = finite(goodwe.on_grid_soc_limit_pct);
  return t(finite(goodwe.battery_charge_w) > 20 && goodwe.operation_mode === 'GENERAL'
    && soc !== null && reserve !== null && soc < reserve
    ? 'flow.possible_reserve_charge' : 'flow.battery_reason_unknown');
}

export function wattsText(value) {
  if (finite(value) === null) return '–';
  const p = power(finite(value));
  return `${p.value} ${p.unit}`;
}
