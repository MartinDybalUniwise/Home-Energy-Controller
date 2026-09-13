// Schéma toku energie. Šipka má směr a tloušťku úměrnou výkonu.
//
// Pojmenované spotřebiče pod domem jsou zatím z valné části bez měření
// (Shelly ještě nemá přiřazená zařízení) – ikony a rozvržení jsou ale hotové
// už teď, takže jakmile v konfiguraci přibude `shelly.devices[].appliance_type`,
// hodnoty se samy rozsvítí bez další úpravy. "Ostatní" je výjimka: není to
// samostatně přiřaditelné zařízení, ale dopočítaný zbytek (dům minus vše
// změřené zvlášť), takže svítí od začátku, i bez jediného Shelly zařízení.

import { applianceIconGroup } from './icons.js';
import { power } from './i18n.js';

const NODES = {
  pv:      { x: 420, y: 45,  key: 'entity.pv',      color: 'var(--series-pv)' },
  house:   { x: 420, y: 165, key: 'entity.house',   color: 'var(--series-house)' },
  battery: { x: 125, y: 165, key: 'entity.battery', color: 'var(--series-battery)' },
  grid:    { x: 715, y: 165, key: 'entity.grid',    color: 'var(--series-grid-import)' },
};
const NODE_WIDTH = 150;
const NODE_HEIGHT = 74;

// Tepelné čerpadlo první, protože jediné má dnes reálná data (agregát ze
// Shelly Pro 3EM); zbytek se rozsvítí, jakmile budou nakonfigurovaná zařízení.
const APPLIANCES = [
  { x: 70,  y: 325, type: 'heatpump',        key: 'entity.heatpump' },
  { x: 210, y: 325, type: 'dishwasher',      key: 'entity.dishwasher' },
  { x: 350, y: 325, type: 'washing_machine', key: 'entity.washing_machine' },
  { x: 490, y: 325, type: 'dryer',           key: 'entity.dryer' },
  { x: 630, y: 325, type: 'fridge',          key: 'entity.fridge' },
  { x: 770, y: 325, type: 'other',           key: 'entity.other_appliances' },
];
const APPLIANCE_WIDTH = 115;
const APPLIANCE_HEIGHT = 64;
const BUS_Y = 245;

function thickness(watts) {
  const kw = Math.abs(Number(watts) || 0) / 1000;
  return Math.max(3, Math.min(10, 3 + kw * 1.4));
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
  const trunk = `<line class="wire" x1="${NODES.house.x}" y1="${NODES.house.y + NODE_HEIGHT / 2}" x2="${NODES.house.x}" y2="${BUS_Y}"/>`;
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
  return `<g class="appliance-node" transform="translate(${appliance.x} ${appliance.y})">
      <rect class="node" x="${-APPLIANCE_WIDTH / 2}" y="${-APPLIANCE_HEIGHT / 2}" width="${APPLIANCE_WIDTH}" height="${APPLIANCE_HEIGHT}" rx="5"/>
      <g class="appliance-node__icon" transform="translate(0 -17) scale(1.25) translate(-12 -12)">${applianceIconGroup(appliance.type)}</g>
      <text text-anchor="middle" y="14" font-size="10" fill="var(--ink-secondary)">${t(appliance.key)}</text>
      <text text-anchor="middle" y="28" font-size="13" font-family="var(--font-value)" font-weight="650">${value}<tspan font-size="9" dx="2" fill="var(--ink-secondary)">${unit}</tspan></text>
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

  // Jeden průchod přes pojmenované spotřebiče: totéž pole se použije pro
  // vykreslení uzlů (applianceNode) i pro barevný přechod nad jejich vodičem
  // (applianceEdges). "Ostatní" není samostatně přiřaditelné zařízení, ale
  // zbytek – viz níže.
  const namedData = APPLIANCES.filter((appliance) => appliance.type !== 'other').map((appliance) => {
    if (appliance.type === 'heatpump') {
      return { appliance, watts: heatpump, measured: isMeasured(values.heatpump_power_w),
               color: 'var(--series-heatpump)' };
    }
    const device = deviceFor(devices, appliance.type);
    return { appliance, watts: device ? Number(device.power_w) : 0,
             measured: !!device && isMeasured(device.power_w), color: 'var(--series-appliances)' };
  });

  // "Ostatní" = spotřeba domu (GoodWe) minus vše, co je změřeno zvlášť (TČ +
  // pojmenované spotřebiče) – ne samostatně přiřazené Shelly zařízení. Bez
  // jediného nakonfigurovaného spotřebiče se tak rovná celé spotřebě domu,
  // ne "–". Drobný záporný zbytek (časové zpoždění mezi měřeními) se ořízne
  // na 0 – reálný zpětný tok z jednotlivého spotřebiče do domu to není.
  const namedMeasuredTotal = namedData.filter((d) => d.measured).reduce((sum, d) => sum + d.watts, 0);
  const otherData = {
    appliance: APPLIANCES.find((appliance) => appliance.type === 'other'),
    watts: Math.max(0, house - namedMeasuredTotal),
    measured: isMeasured(values.house_w),
    color: 'var(--series-appliances)',
  };
  const applianceData = [...namedData, otherData];

  const edges = [
    edge({ x: NODES.pv.x, y: NODES.pv.y + NODE_HEIGHT / 2 },
      { x: NODES.house.x, y: NODES.house.y - NODE_HEIGHT / 2 }, pv, 'var(--series-pv)', motion),
    edge({ x: NODES.house.x - NODE_WIDTH / 2, y: NODES.house.y },
      { x: NODES.battery.x + NODE_WIDTH / 2, y: NODES.battery.y },
      charge - discharge, 'var(--series-battery)', motion),
    edge({ x: NODES.grid.x - NODE_WIDTH / 2, y: NODES.grid.y },
      { x: NODES.house.x + NODE_WIDTH / 2, y: NODES.house.y }, gridImport || -gridExport,
      gridImport ? 'var(--series-grid-import)' : 'var(--series-grid-export)', motion),
    edge({ x: NODES.house.x, y: NODES.house.y + NODE_HEIGHT / 2 },
      { x: NODES.house.x, y: BUS_Y }, house, 'var(--series-house)', motion),
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
    return `<g class="main-node main-node--${name}" transform="translate(${node.x} ${node.y})">
        <rect class="node" x="${-NODE_WIDTH / 2}" y="${-NODE_HEIGHT / 2}" width="${NODE_WIDTH}" height="${NODE_HEIGHT}" rx="5"/>
      <text text-anchor="middle" y="-9" font-size="13" fill="var(--ink-secondary)">${t(node.key)}</text>
      <text text-anchor="middle" y="17" font-size="22" font-family="var(--font-value)" font-weight="650">${value}<tspan font-size="13" dx="3" fill="var(--ink-secondary)">${unit}</tspan></text>
      </g>`;
  }).join('');

  const applianceLabels = applianceData
    .map(({ appliance, watts, measured: m }) => applianceNode(appliance, watts, m, t)).join('');

    container.innerHTML = `<svg class="flow" viewBox="0 0 840 365" role="img" aria-label="${t('overview.flow')}">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker></defs>
      ${applianceWiring()}
      ${edges}${mainLabels}${applianceLabels}
    </svg>`;
}
