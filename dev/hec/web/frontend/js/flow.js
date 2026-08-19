// Schéma toku energie. Šipka má směr a tloušťku úměrnou výkonu.

import { power } from './i18n.js';

const NODES = {
  pv:        { x: 200, y: 30,  key: 'entity.pv',        color: 'var(--series-pv)' },
  house:     { x: 200, y: 108, key: 'entity.house',     color: 'var(--series-house)' },
  battery:   { x: 58,  y: 108, key: 'entity.battery',   color: 'var(--series-battery)' },
  grid:      { x: 342, y: 108, key: 'entity.grid',      color: 'var(--series-grid-import)' },
  heatpump:  { x: 200, y: 186, key: 'entity.heatpump',  color: 'var(--series-heatpump)' },
};
const NODE_WIDTH = 96;
const NODE_HEIGHT = 46;

function thickness(watts) {
  const kw = Math.abs(Number(watts) || 0) / 1000;
  return Math.max(2, Math.min(8, 2 + kw * 1.2));
}

function edge(from, to, watts, color, motion) {
  if (!Number.isFinite(Number(watts)) || Math.abs(watts) < 20) return '';
  const [a, b] = watts >= 0 ? [from, to] : [to, from];
  const animated = motion === 'full' ? ' animated' : '';
  return `<line class="edge${animated}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"
            stroke="${color}" stroke-width="${thickness(watts)}" marker-end="url(#arrow)"/>`;
}

function isMeasured(value) {
  return value !== undefined && value !== null && !Number.isNaN(Number(value));
}

export function renderFlow(container, values, t, motion = 'full') {
  // Chybějící zdroj (vypnutý reader) se nesmí vydávat za změřenou nulu –
  // "0 W" tvrdí, že se nic nevyrábí/nespotřebovává, zatímco pravda je
  // "nezměřeno". Šipky pod prahem edge() se stejně nekreslí; jde jen o popisek.
  const pv = Number(values.pv_w) || 0;
  const house = Number(values.house_w) || 0;
  const gridImport = Number(values.grid_import_w) || 0;
  const gridExport = Number(values.grid_export_w) || 0;
  const charge = Number(values.battery_charge_w) || 0;
  const discharge = Number(values.battery_discharge_w) || 0;
  const heatpump = Number(values.heatpump_power_w) || 0;

  const edges = [
    edge(NODES.pv, NODES.house, pv, 'var(--series-pv)', motion),
    edge(NODES.house, NODES.battery, charge - discharge, 'var(--series-battery)', motion),
    edge(NODES.grid, NODES.house, gridImport || -gridExport,
      gridImport ? 'var(--series-grid-import)' : 'var(--series-grid-export)', motion),
    edge(NODES.house, NODES.heatpump, heatpump, 'var(--series-heatpump)', motion),
  ].join('');

  const measured = {
    pv: isMeasured(values.pv_w),
    house: isMeasured(values.house_w),
    battery: isMeasured(values.battery_charge_w) || isMeasured(values.battery_discharge_w),
    grid: isMeasured(values.grid_import_w) || isMeasured(values.grid_export_w),
    heatpump: isMeasured(values.heatpump_power_w),
  };

  const labels = Object.entries(NODES).map(([name, node]) => {
    const watts = { pv, house, battery: charge || discharge, grid: gridImport || gridExport, heatpump }[name];
    const { value, unit } = measured[name] ? power(watts) : { value: '–', unit: t('unit.w') };
    return `<g transform="translate(${node.x} ${node.y})">
        <rect class="node" x="${-NODE_WIDTH / 2}" y="${-NODE_HEIGHT / 2}" width="${NODE_WIDTH}" height="${NODE_HEIGHT}" rx="5"/>
        <text text-anchor="middle" y="-8" font-size="9" fill="var(--ink-secondary)">${t(node.key)}</text>
        <text text-anchor="middle" y="11" font-size="15" font-family="var(--font-value)" font-weight="600">${value}<tspan font-size="9" dx="2" fill="var(--ink-secondary)">${unit}</tspan></text>
      </g>`;
  }).join('');

  container.innerHTML = `<svg class="flow" viewBox="0 0 400 216" role="img" aria-label="${t('overview.flow')}">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker></defs>
      ${edges}${labels}
    </svg>`;
}
