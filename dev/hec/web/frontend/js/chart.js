// Spojnicový a plošný graf v SVG. Bez knihovny – běží i bez internetu.
//
// Pravidla podle dev/step01/UI_DESIGN.md:
//   * jedna osa Y (dvojitá osa je zakázaná – druhá veličina = druhý graf),
//   * legenda vždy při dvou a více sériích,
//   * zaměřovač s tooltipem je součást grafu, ne doplněk,
//   * ke každému grafu existuje tabulkový pohled.

import { num, time } from './i18n.js';

const WIDTH = 960;
const HEIGHT = 320;
const PAD = { top: 16, right: 16, bottom: 28, left: 52 };

function niceStep(range, target = 5) {
  if (!(range > 0)) return 1;
  const rough = range / target;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalised = rough / magnitude;
  const step = normalised >= 5 ? 10 : normalised >= 2 ? 5 : normalised >= 1 ? 2 : 1;
  return step * magnitude;
}

function extent(rows, fields) {
  let min = Infinity;
  let max = -Infinity;
  rows.forEach((row) => fields.forEach((field) => {
    const value = Number(row[field]);
    if (Number.isFinite(value)) { min = Math.min(min, value); max = Math.max(max, value); }
  }));
  if (!Number.isFinite(min)) return [0, 1];
  if (min === max) return [min - 1, max + 1];
  return [Math.min(0, min), max];
}

function pathFor(rows, field, x, y) {
  let path = '';
  let open = false;
  rows.forEach((row, index) => {
    const value = Number(row[field]);
    if (!Number.isFinite(value)) { open = false; return; }
    path += `${open ? 'L' : 'M'}${x(index).toFixed(1)} ${y(value).toFixed(1)}`;
    open = true;
  });
  return path;
}

/**
 * @param {object} options
 *   rows    – pole záznamů se `timestamp`
 *   series  – [{ field, labelKey|label, color, area }]
 *   unit    – jednotka osy Y
 *   scale   – násobitel hodnot (např. 0.001 pro W → kW)
 */
export function renderChart(container, { rows = [], series = [], unit = '', scale = 1 }) {
  container.innerHTML = '';
  const active = series.filter((entry) => rows.some((row) => Number.isFinite(Number(row[entry.field]))));
  if (!rows.length || !active.length) {
    container.innerHTML = `<p class="notice">${container.dataset.emptyText || ''}</p>`;
    return;
  }

  const scaled = rows.map((row) => {
    const copy = { timestamp: row.timestamp };
    active.forEach(({ field }) => {
      const value = Number(row[field]);
      copy[field] = Number.isFinite(value) ? value * scale : null;
    });
    return copy;
  });

  const [min, max] = extent(scaled, active.map((entry) => entry.field));
  const step = niceStep(max - min);
  const top = Math.ceil(max / step) * step;
  const bottom = Math.floor(min / step) * step;

  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const x = (index) => PAD.left + (scaled.length === 1 ? plotWidth / 2 : (index / (scaled.length - 1)) * plotWidth);
  const y = (value) => PAD.top + plotHeight - ((value - bottom) / (top - bottom || 1)) * plotHeight;

  const gridLines = [];
  for (let value = bottom; value <= top + 1e-9; value += step) {
    gridLines.push(`<line class="grid-line" x1="${PAD.left}" x2="${WIDTH - PAD.right}" y1="${y(value).toFixed(1)}" y2="${y(value).toFixed(1)}"/>`
      + `<text class="axis-label" x="${PAD.left - 8}" y="${(y(value) + 4).toFixed(1)}" text-anchor="end">${num(value, step < 1 ? 1 : 0)}</text>`);
  }

  const ticks = [];
  const tickCount = Math.min(6, scaled.length);
  for (let i = 0; i < tickCount; i += 1) {
    const index = Math.round((i / Math.max(1, tickCount - 1)) * (scaled.length - 1));
    ticks.push(`<text class="axis-label" x="${x(index).toFixed(1)}" y="${HEIGHT - 8}" text-anchor="middle">${time(scaled[index].timestamp)}</text>`);
  }

  const paths = active.map((entry) => {
    const line = pathFor(scaled, entry.field, x, y);
    const area = entry.area
      ? `<path class="series-area" fill="${entry.color}" d="${line} L${x(scaled.length - 1).toFixed(1)} ${y(bottom).toFixed(1)} L${x(0).toFixed(1)} ${y(bottom).toFixed(1)} Z"/>`
      : '';
    return `${area}<path class="series-line" stroke="${entry.color}" d="${line}"/>`;
  }).join('');

  container.insertAdjacentHTML('beforeend', `
    <svg class="chart" viewBox="0 0 ${WIDTH} ${HEIGHT}" preserveAspectRatio="none" role="img">
      <g>${gridLines.join('')}</g>
      <g>${ticks.join('')}</g>
      <text class="axis-label" x="${PAD.left - 8}" y="${PAD.top - 4}" text-anchor="end">${unit}</text>
      ${paths}
      <line class="crosshair" y1="${PAD.top}" y2="${HEIGHT - PAD.bottom}" x1="0" x2="0" hidden/>
      <rect x="${PAD.left}" y="${PAD.top}" width="${plotWidth}" height="${plotHeight}" fill="transparent"/>
    </svg>
    <div class="tooltip" hidden></div>`);

  if (active.length > 1) {
    container.insertAdjacentHTML('beforeend', `<div class="legend">${active.map((entry) =>
      `<span><span class="swatch" style="background:${entry.color}"></span>${entry.label}</span>`).join('')}</div>`);
  }

  attachCrosshair(container, scaled, active, unit, { x, plotWidth });
}

function attachCrosshair(container, rows, series, unit, { x, plotWidth }) {
  const svg = container.querySelector('svg');
  const crosshair = svg.querySelector('.crosshair');
  const tooltip = container.querySelector('.tooltip');

  const move = (event) => {
    const bounds = svg.getBoundingClientRect();
    const pointer = (event.touches ? event.touches[0].clientX : event.clientX) - bounds.left;
    const ratio = pointer / bounds.width;
    const index = Math.max(0, Math.min(rows.length - 1, Math.round((ratio * WIDTH - PAD.left) / plotWidth * (rows.length - 1))));
    const row = rows[index];
    crosshair.setAttribute('x1', x(index));
    crosshair.setAttribute('x2', x(index));
    crosshair.removeAttribute('hidden');
    tooltip.innerHTML = `<strong>${time(row.timestamp)}</strong><br>` + series.map((entry) =>
      `<span class="swatch" style="background:${entry.color}"></span>${entry.label}: ${num(row[entry.field], 2)} ${unit}`).join('<br>');
    tooltip.hidden = false;
    const left = Math.min(bounds.width - tooltip.offsetWidth - 8, Math.max(0, pointer + 12));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = '16px';
  };

  const hide = () => { crosshair.setAttribute('hidden', ''); tooltip.hidden = true; };
  svg.addEventListener('mousemove', move);
  svg.addEventListener('mouseleave', hide);
  svg.addEventListener('touchstart', move, { passive: true });
  svg.addEventListener('touchmove', move, { passive: true });
  svg.addEventListener('touchend', hide);
}

/** Tabulkový pohled – přístupnost i export. */
export function renderTable(container, rows, series, unit) {
  if (!rows.length) { container.innerHTML = ''; return; }
  const head = series.map((entry) => `<th>${entry.label} [${unit}]</th>`).join('');
  const body = rows.map((row) => `<tr><td>${time(row.timestamp, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>`
    + series.map((entry) => `<td>${num(row[entry.field], 2)}</td>`).join('') + '</tr>').join('');
  container.innerHTML = `<div class="table-wrap"><table class="data"><thead><tr><th>Čas</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
