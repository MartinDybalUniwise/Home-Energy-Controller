// Schéma toku energie. Šipka má směr a tloušťku úměrnou výkonu.

import { power } from './i18n.js';

const NODES = {
  pv:        { x: 240, y: 40,  key: 'entity.pv',        color: 'var(--series-pv)' },
  house:     { x: 240, y: 150, key: 'entity.house',     color: 'var(--series-house)' },
  battery:   { x: 70,  y: 150, key: 'entity.battery',   color: 'var(--series-battery)' },
  grid:      { x: 410, y: 150, key: 'entity.grid',      color: 'var(--series-grid-import)' },
  heatpump:  { x: 240, y: 260, key: 'entity.heatpump',  color: 'var(--series-heatpump)' },
};

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

export function renderFlow(container, values, t, motion = 'full') {
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

  const labels = Object.entries(NODES).map(([name, node]) => {
    const watts = { pv, house, battery: charge || discharge, grid: gridImport || gridExport, heatpump }[name];
    const { value, unit } = power(watts);
    return `<g transform="translate(${node.x} ${node.y})">
        <rect class="node" x="-58" y="-30" width="116" height="60" rx="6"/>
        <text text-anchor="middle" y="-10" font-size="11" fill="var(--ink-secondary)">${t(node.key)}</text>
        <text text-anchor="middle" y="14" font-size="20" font-family="var(--font-value)" font-weight="600">${value}<tspan font-size="11" dx="3" fill="var(--ink-secondary)">${unit}</tspan></text>
      </g>`;
  }).join('');

  container.innerHTML = `<svg class="flow" viewBox="0 0 480 320" role="img" aria-label="${t('overview.flow')}">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker></defs>
      ${edges}${labels}
    </svg>`;
}
