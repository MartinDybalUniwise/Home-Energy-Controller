// Schéma toku energie. Šipka má směr a tloušťku úměrnou výkonu.
//
// Spotřebiče pod domem jsou zatím z valné části bez měření (Shelly ještě
// nemá přiřazená zařízení) – ikony a rozvržení jsou ale hotové už teď, takže
// jakmile v konfiguraci přibude `shelly.devices[].appliance_type`, hodnoty
// se samy rozsvítí bez další úpravy.

import { applianceIconGroup } from './icons.js';
import { power } from './i18n.js';

const NODES = {
  pv:      { x: 200, y: 26,  key: 'entity.pv',      color: 'var(--series-pv)' },
  house:   { x: 200, y: 100, key: 'entity.house',   color: 'var(--series-house)' },
  battery: { x: 58,  y: 100, key: 'entity.battery', color: 'var(--series-battery)' },
  grid:    { x: 342, y: 100, key: 'entity.grid',    color: 'var(--series-grid-import)' },
};
const NODE_WIDTH = 96;
const NODE_HEIGHT = 44;

// Tepelné čerpadlo první, protože jediné má dnes reálná data (agregát ze
// Shelly Pro 3EM); zbytek se rozsvítí, jakmile budou nakonfigurovaná zařízení.
const APPLIANCES = [
  { x: 68,  y: 172, type: 'heatpump',        key: 'entity.heatpump' },
  { x: 200, y: 172, type: 'dishwasher',      key: 'entity.dishwasher' },
  { x: 332, y: 172, type: 'washing_machine', key: 'entity.washing_machine' },
  { x: 68,  y: 240, type: 'dryer',           key: 'entity.dryer' },
  { x: 200, y: 240, type: 'fridge',          key: 'entity.fridge' },
  { x: 332, y: 240, type: 'other',           key: 'entity.other_appliances' },
];
const APPLIANCE_WIDTH = 78;
const APPLIANCE_HEIGHT = 56;
const BUS_Y = 138;

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

/** Zapojené zařízení Shelly pro daný typ spotřebiče, pokud je nakonfigurováno. */
function deviceFor(devices, type) {
  return Object.values(devices || {}).find((device) => device.appliance_type === type);
}

const APPLIANCE_ROWS = [...new Set(APPLIANCES.map((a) => a.y))];
const APPLIANCE_COLUMNS = [...new Set(APPLIANCES.map((a) => a.x))];

/** Přesná cesta vodiče od rozvodnice/předchozí řady až po konkrétní spotřebič
 * – používá se jak pro statické (šedé) vedení, tak pro barevný přechod nad
 * ním, aby oba přesně seděly na sebe. */
function wireSegment(appliance) {
  const top = appliance.y - APPLIANCE_HEIGHT / 2;
  return appliance.y === APPLIANCE_ROWS[0]
    ? { x1: appliance.x, y1: top, x2: appliance.x, y2: BUS_Y }
    : { x1: appliance.x, y1: top, x2: appliance.x, y2: APPLIANCE_ROWS[0] + APPLIANCE_HEIGHT / 2 };
}

function applianceWiring() {
  // Statické vodiče (dům → rozvodnice → spotřebiče) se kreslí vždy, aby bylo
  // vidět zapojení i bez dat. Barevný animovaný přechod se přidává navrch jen
  // tam, kde je výkon skutečně změřen – viz applianceEdges() níže.
  const trunk = `<line class="wire" x1="200" y1="${NODES.house.y + NODE_HEIGHT / 2}" x2="200" y2="${BUS_Y}"/>`;
  const bus = `<line class="wire" x1="${Math.min(...APPLIANCE_COLUMNS)}" y1="${BUS_Y}" x2="${Math.max(...APPLIANCE_COLUMNS)}" y2="${BUS_Y}"/>`;
  const branches = APPLIANCES.map((a) => {
    const s = wireSegment(a);
    return `<line class="wire" x1="${s.x1}" y1="${s.y1}" x2="${s.x2}" y2="${s.y2}"/>`;
  }).join('');
  return trunk + bus + branches;
}

/** Barevný animovaný přechod přesně nad vodičem každého změřeného spotřebiče. */
function applianceEdges(rows, motion) {
  return rows.map(({ appliance, watts, color }) => {
    const segment = wireSegment(appliance);
    return edge({ x: segment.x2, y: segment.y2 }, { x: segment.x1, y: segment.y1 }, watts, color, motion);
  }).join('');
}

function applianceNode(appliance, watts, measured, t) {
  const { value, unit } = measured ? power(watts) : { value: '–', unit: t('unit.w') };
  return `<g transform="translate(${appliance.x} ${appliance.y})">
      <rect class="node" x="${-APPLIANCE_WIDTH / 2}" y="${-APPLIANCE_HEIGHT / 2}" width="${APPLIANCE_WIDTH}" height="${APPLIANCE_HEIGHT}" rx="5"/>
      <g transform="translate(0 -12) scale(0.8) translate(-12 -12)" style="color: var(--ink-secondary)">${applianceIconGroup(appliance.type)}</g>
      <text text-anchor="middle" y="14" font-size="7.5" fill="var(--ink-secondary)">${t(appliance.key)}</text>
      <text text-anchor="middle" y="24" font-size="10" font-family="var(--font-value)" font-weight="600">${value}<tspan font-size="7.5" dx="1.5" fill="var(--ink-secondary)">${unit}</tspan></text>
    </g>`;
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
  const devices = values.devices || {};

  // Jeden průchod přes spotřebiče: totéž pole se použije pro vykreslení uzlů
  // (applianceNode) i pro barevný přechod nad jejich vodičem (applianceEdges).
  const applianceData = APPLIANCES.map((appliance) => {
    if (appliance.type === 'heatpump') {
      return { appliance, watts: heatpump, measured: isMeasured(values.heatpump_power_w),
               color: 'var(--series-heatpump)' };
    }
    const device = deviceFor(devices, appliance.type);
    return { appliance, watts: device ? Number(device.power_w) : 0,
             measured: !!device && isMeasured(device.power_w), color: 'var(--series-appliances)' };
  });

  const edges = [
    edge(NODES.pv, NODES.house, pv, 'var(--series-pv)', motion),
    edge(NODES.house, NODES.battery, charge - discharge, 'var(--series-battery)', motion),
    edge(NODES.grid, NODES.house, gridImport || -gridExport,
      gridImport ? 'var(--series-grid-import)' : 'var(--series-grid-export)', motion),
    applianceEdges(applianceData.filter((d) => d.measured), motion),
  ].join('');

  const measured = {
    pv: isMeasured(values.pv_w),
    house: isMeasured(values.house_w),
    battery: isMeasured(values.battery_charge_w) || isMeasured(values.battery_discharge_w),
    grid: isMeasured(values.grid_import_w) || isMeasured(values.grid_export_w),
  };

  const mainLabels = Object.entries(NODES).map(([name, node]) => {
    const watts = { pv, house, battery: charge || discharge, grid: gridImport || gridExport }[name];
    const { value, unit } = measured[name] ? power(watts) : { value: '–', unit: t('unit.w') };
    return `<g transform="translate(${node.x} ${node.y})">
        <rect class="node" x="${-NODE_WIDTH / 2}" y="${-NODE_HEIGHT / 2}" width="${NODE_WIDTH}" height="${NODE_HEIGHT}" rx="5"/>
        <text text-anchor="middle" y="-7" font-size="9" fill="var(--ink-secondary)">${t(node.key)}</text>
        <text text-anchor="middle" y="11" font-size="15" font-family="var(--font-value)" font-weight="600">${value}<tspan font-size="9" dx="2" fill="var(--ink-secondary)">${unit}</tspan></text>
      </g>`;
  }).join('');

  const applianceLabels = applianceData
    .map(({ appliance, watts, measured: m }) => applianceNode(appliance, watts, m, t)).join('');

  container.innerHTML = `<svg class="flow" viewBox="0 -6 400 296" role="img" aria-label="${t('overview.flow')}">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker></defs>
      ${applianceWiring()}
      ${edges}${mainLabels}${applianceLabels}
    </svg>`;
}
