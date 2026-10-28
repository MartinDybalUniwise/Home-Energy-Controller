import {source, finite} from './telemetry.js';
import {t, num} from './i18n.js';
import {siteDateTime, siteTime, siteDate, siteClock} from './today-chart.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fresh = (data, now, seconds) => {
  const age = (+now-Date.parse(data.sample_time || data.timestamp))/1000;
  return Number.isFinite(age) && age >= -5 && age <= seconds;
};
const rows = pairs => `<dl class="hp-rows">${pairs.map(([label,value,cls='']) => `<div class="${cls}"><dt>${esc(label)}</dt><dd>${value}</dd></div>`).join('')}</dl>`;

export function heatpumpPanel(current, config, now = new Date()) {
  const wire = source(current,'tng_wire'), cloud = source(current,'tng');
  const receiver = source(current,'tng_wire_receiver');
  const wireFresh = fresh(wire,now,180), cloudFresh = fresh(cloud,now,900);
  const field = key => {
    if (wireFresh && finite(wire[key]) !== null && wire.field_quality?.[key] !== 'outside_verified_range')
      return {value:wire[key], origin:'wire'};
    if (cloudFresh && finite(cloud[key]) !== null) return {value:cloud[key], origin:'cloud'};
    return {value:null,origin:null};
  };
  const temp = key => {
    const result = field(key);
    return result.value === null ? '—' : `${num(result.value,1)} <small>°C${result.origin === 'cloud' ? ' · API' : ''}</small>`;
  };
  const unknown = '—';
  const candidate = wireFresh && finite(wire.candidate_frequency_or_ack) !== null ? `${num(wire.candidate_frequency_or_ack,0)} <small>?</small>` : unknown;
  const left = [
    [t('hp.outlet'),temp('water_output_temperature')], [t('hp.inlet'),temp('water_input_temperature')],
    [t('hp.refrigerant_out'),temp('refrigerant_output_temperature')], [t('hp.refrigerant_in'),unknown],
    [t('hp.outside'),temp('outside_temperature')], [t('hp.boiler'),temp('boiler_temperature'),'hp-hot'],
    [t('hp.buffer'),temp('buffer_temperature'),'hp-buffer'], [t('hp.room'),temp('room_temperature')],
    [t('hp.equit'),unknown], [t('hp.boost'),unknown], [t('hp.outdoor'),candidate === unknown ? unknown : `${candidate} Hz`],
  ];
  const actualMode = cloudFresh ? cloud.boiler_on ? 'boiler' : cloud.heating_on ? 'heating' : 'off' : 'unknown';
  const right = [[t('hp.sw'),unknown],[t('hp.model'),unknown],[t('hp.switch'),unknown],
    [t('hp.inputs'),wireFresh && Number.isInteger(wire.candidate_inputs) ? `${wire.candidate_inputs.toString(2).padStart(8,'0')} ?` : unknown],
    [t('hp.outputs'),unknown],[t('hp.power_req'),unknown],[t('hp.power_ack'),candidate],
    [t('hp.request'),`${t(`hp.mode_${actualMode}`)}${cloudFresh ? ' <small>· API</small>' : ''}`],[t('hp.errors'),unknown]];
  const moment = siteTime(now), date = siteDate(moment), clock = siteClock(moment);
  const effective = name => {
    const base = config?.tng?.[name] || {};
    return {...base,...(base.date_overrides?.[date] || {})};
  };
  const inWindow = item => item.from <= item.to ? clock >= item.from && clock < item.to : clock >= item.from || clock < item.to;
  const operation = effective('operation');
  let desiredMode = operation.default_mode || 'heating';
  for (const item of operation.schedule || []) if (inWindow(item)) desiredMode = item.mode;
  const target = name => {
    const section = effective(name);
    let value = section.default_temperature;
    for (const item of section.schedule || []) if (inWindow(item)) value = item.temperature;
    return finite(value) === null ? '—' : `${num(value,1)} °C`;
  };
  const gate = source(current,'tng_gate').basic || {};
  const command = source(current,'tng_command');
  const thermostatGate = source(current,'tng_gate').thermostat || {};
  const thermostatPhase = thermostatGate.last_post_at ? thermostatGate.awaiting_confirmation ? 'pending' : 'confirmed' : 'none';
  const sent = command.kind === 'BASIC_SETTINGS' ? command.requested || {} : {};
  const sentMode = sent.BoilerSet?.Boiler === true ? 'boiler' : sent.HeatSet?.Heat === true ? 'heating' :
    sent.BoilerSet?.Boiler === false && sent.HeatSet?.Heat === false ? 'off' : 'unknown';
  const sentTemp = (key, fallback) => {
    const value = finite(sent[key] ?? gate.last_requested?.[fallback]);
    return value === null ? '—' : `${num(value,1)} °C`;
  };
  let phase = 'none';
  if (gate.last_post_at) phase = gate.awaiting_confirmation ? 'pending' : 'confirmed';
  if (command.phase === 'failed' && (!gate.last_post_at || command.timestamp >= gate.last_post_at)) phase = 'failed';
  if (command.phase === 'dry_run' && (!gate.last_post_at || command.timestamp >= gate.last_post_at)) phase = 'dry_run';
  const settingsMatch = cloudFresh && desiredMode === actualMode &&
    (desiredMode === 'off' || finite(cloud[desiredMode === 'boiler' ? 'boiler_set_temperature' : 'heating_set_temperature']) ===
      Number(target(desiredMode === 'boiler' ? 'boiler' : 'heating').replace(',','.').split(' ')[0]));
  const commandRows = [[t('hp.plan_mode'),esc(t(`hp.mode_${desiredMode}`))],
    [t('hp.heat_target'),esc(target('heating'))],[t('hp.boiler_target'),esc(target('boiler'))],
    [t('hp.room_target'),esc(target('thermostat'))], [t('hp.command_state'),esc(t(`hp.phase_${phase}`))],
    [t('hp.thermostat_state'),esc(t(`hp.phase_${thermostatPhase}`))],
    [t('hp.last_sent'),gate.last_post_at ? esc(siteDateTime(gate.last_post_at)) : '—'],
    [t('hp.sent_mode'),esc(t(`hp.mode_${sentMode}`))],
    [t('hp.sent_heat'),sentTemp('HeatTemp_Const','heating_temperature')],
    [t('hp.sent_boiler'),sentTemp('BoilerTemp','boiler_temperature')],
    [t('hp.reported_heat'),cloudFresh ? `${num(cloud.heating_set_temperature,1)} °C` : '—'],
    [t('hp.reported_boiler'),cloudFresh ? `${num(cloud.boiler_set_temperature,1)} °C` : '—']];
  return `<section class="workspace-card hp-panel" id="heatpump-panel">
    <header class="workspace-card-header"><h4>${t('hp.title')}</h4><span class="hp-badge ${wireFresh && !receiver.log_limit_reached ? 'is-fresh' : 'is-stale'}">${t(receiver.log_limit_reached ? 'hp.log_limit' : wireFresh ? 'hp.receiving' : 'hp.no_wire')}</span></header>
    <div class="hp-panels"><article><h5>${t('hp.actual')}</h5><div class="hp-display">${rows(left)}${rows(right)}</div>
      <div class="meta">${t('hp.wire_time')}: ${wire.sample_time ? esc(siteDateTime(wire.sample_time)) : '—'}</div>
      <div class="meta">API: ${cloud.sample_time ? esc(siteDateTime(cloud.sample_time)) : '—'}</div></article>
    <article><h5>${t('hp.command')}</h5>${rows(commandRows)}<span class="hp-badge ${settingsMatch ? 'is-fresh' : 'is-stale'}">${t(settingsMatch ? 'hp.matches' : 'hp.not_matched')}</span></article></div>
    <details><summary>ⓘ</summary><p>${t('hp.help')}</p><p>${t('hp.trace_counts',{requests:receiver.requests ?? 0,responses:receiver.responses ?? 0,pairs:receiver.pairs ?? 0})}</p><a href="/api/tng-wire/events?hours=1&limit=100" target="_blank" rel="noopener">${t('hp.raw_events')}</a></details>
  </section>`;
}
