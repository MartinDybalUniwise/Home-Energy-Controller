import { dateTime } from './i18n.js';
// Keep mobile values in HTML: connectors can resize without shrinking labels.
import { finite, quality, heatpumpQuality, wattsText } from './telemetry.js';

const APPLIANCES = ['heatpump', 'dishwasher', 'washing_machine', 'dryer', 'fridge'];

export function renderFlow(container, values, t, motion = 'full') {
  const devices = values.devices || {};
  const statuses = Object.values(values.device_status || {});
  const data = APPLIANCES.map(type => {
    const device = Object.values(devices).find(d => type === 'heatpump'
      ? d.role === 'heatpump_meter' : d.appliance_type === type && d.role !== 'heatpump_meter');
    const status = statuses.find(d => type === 'heatpump' ? d.role === 'heatpump_meter' : d.appliance_type === type);
    const watts = type === 'heatpump' ? finite(values.heatpump_power_w) : finite(device?.power_w);
    const state = type === 'heatpump' ? heatpumpQuality(values) : status?.quality || quality(device);
    return {type, watts, state, timestamp: status?.timestamp};
  });
  const power = value => { const n = finite(value); return n !== null && n >= 0 ? n : null; };
  const house = power(values.house_w);
  const complete = data.every(d => d.state === 'valid') && house !== null;
  const remainder = complete ? house - data.reduce((sum, d) => sum + d.watts, 0) : null;
  data.push({type:'other_appliances', watts: remainder !== null && remainder >= 0 ? remainder : null,
    state: remainder !== null && remainder >= 0 ? 'residual' : 'incomplete'});
  const charge = power(values.battery_charge_w), discharge = power(values.battery_discharge_w);
  const imported = power(values.grid_import_w), exported = power(values.grid_export_w);
  const battery = charge !== null && discharge !== null ? charge - discharge : null;
  const grid = imported !== null && exported !== null ? imported - exported : null;
  const mains = [
    {type:'pv', watts:power(values.pv_w), detail:power(values.pv_w) === null ? 'meter.missing' : power(values.pv_w) > 20 ? 'flow.to_house' : 'flow.idle', x:180,y:60},
    {type:'battery', watts:battery === null ? null : Math.abs(battery), detail:battery === null ? 'meter.missing' : battery > 20 ? 'flow.charging' : battery < -20 ? 'flow.discharging' : 'flow.idle', x:180,y:210},
    {type:'house', watts:house, detail:house === null ? 'meter.missing' : 'flow.consumption', x:580,y:60},
    {type:'grid', watts:grid === null ? null : Math.abs(grid), detail:grid === null ? 'meter.missing' : grid > 20 ? 'entity.grid_import' : grid < -20 ? 'entity.grid_export' : 'flow.balanced_short', x:580,y:210},
  ];
  const cards = mains.map(d => `<div class="flow-reading flow-reading--${d.type}"><span>${t('entity.'+d.type)}</span><strong>${wattsText(d.watts)}</strong><span>${t(d.detail)}</span></div>`).join('');
  const thickness = watts => 2 + 6 * Math.min(Math.abs(watts) / 5000, 1);
  const mobileLink = (type, watts, path, forwardFrom, forwardTo, color) => {
    const active = watts !== null && Math.abs(watts) > 20;
    const forward = watts > 0;
    const from = active ? (forward ? forwardFrom : forwardTo) : '';
    const to = active ? (forward ? forwardTo : forwardFrom) : '';
    const marker = `flow-mobile-arrow-${type}`;
    const label = active ? `${t('entity.'+from)} → ${t('entity.'+to)}` : t(watts === null ? 'meter.missing' : 'flow.idle');
    return `<svg class="flow-mobile-link flow-mobile-link--${type}" viewBox="0 0 100 48" preserveAspectRatio="none" role="img" aria-label="${label}" data-flow="${type}" data-from="${from}" data-to="${to}" data-active="${active}"><defs><marker id="${marker}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="context-stroke"/></marker></defs><path class="${active ? 'edge' + (motion === 'full' ? ' animated' : '') + (!forward ? ' flow-edge-reverse' : '') : 'flow-link-idle'}" d="${path}" fill="none" stroke="${active ? `var(--series-${color})` : 'var(--ink-muted)'}" stroke-width="${active ? thickness(watts) : 2}" vector-effect="non-scaling-stroke" ${active ? `marker-${forward ? 'end' : 'start'}="url(#${marker})"` : ''}/></svg>`;
  };
  const links = mobileLink('pv', power(values.pv_w), 'M50 2 L50 44', 'pv', 'house', 'pv')
    + mobileLink('battery', battery, 'M85 2 Q50 2 50 44', 'house', 'battery', 'battery')
    + mobileLink('grid', grid === null ? null : -grid, 'M15 2 Q50 2 50 44', 'house', 'grid', grid !== null && grid < 0 ? 'grid-export' : 'grid-import');
  const nodes = mains.map(d => `<g class="main-node main-node--${d.type}" transform="translate(${d.x} ${d.y})"><rect class="node" x="-140" y="-45" width="280" height="104" rx="12"/><text text-anchor="middle" y="-15" font-size="20">${t('entity.'+d.type)}</text><text text-anchor="middle" y="15" font-size="27">${wattsText(d.watts)}</text><text text-anchor="middle" y="43" font-size="17">${t(d.detail)}</text></g>`).join('');
  const edge = (a,b,watts,color) => {
    if (watts === null || Math.abs(watts) <= 20) return '';
    const [from,to] = watts >= 0 ? [a,b] : [b,a];
    return `<path class="edge${motion === 'full' ? ' animated' : ''}" d="M${from} L${to}" stroke="var(--series-${color})" stroke-width="${thickness(watts)}" marker-end="url(#flow-arrow)"/>`;
  };
  const edges = edge('330 60','430 60',power(values.pv_w),'pv')
    + edge('450 110','310 175',battery,'battery')
    + edge('580 160','580 120',grid,grid !== null && grid < 0 ? 'grid-export' : 'grid-import');
  container.innerHTML = `<div class="flow-main-readings" role="group" aria-label="${t('overview.flow')}">${cards}${links}</div>
    <svg class="flow flow-desktop" viewBox="0 0 760 280" role="img" aria-label="${t('overview.flow')}"><defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="context-stroke"/></marker></defs>${edges}${nodes}</svg>
    <h3 class="flow-devices-heading">${t('flow.devices')}</h3><dl class="flow-device-list">${data.map(d => `<div class="flow-device-row" data-device="${d.type}" data-quality="${d.state}"><dt>${t('entity.'+d.type)}</dt><dd><strong>${wattsText(d.watts)}</strong><div class="flow-device-details"><span>${t('meter.'+d.state)}</span>${d.timestamp ? `<span>${t('flow.device_checked', {time: dateTime(d.timestamp)})}</span>` : ''}</div></dd></div>`).join('')}</dl>`;
}
