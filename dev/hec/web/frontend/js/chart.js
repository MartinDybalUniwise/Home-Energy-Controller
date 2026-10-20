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

function numericValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

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
    const value = numericValue(row[field]);
    if (value !== null) { min = Math.min(min, value); max = Math.max(max, value); }
  }));
  if (!Number.isFinite(min)) return [0, 1];
  if (min === max) return [min - 1, max + 1];
  return [Math.min(0, min), max];
}

function pathFor(rows, field, x, y) {
  let path = '';
  let open = false;
  rows.forEach((row, index) => {
    const value = numericValue(row[field]);
    if (value === null) { open = false; return; }
    path += `${open ? 'L' : 'M'}${x(index).toFixed(1)} ${y(value).toFixed(1)}`;
    open = true;
  });
  return path;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function axisScale(rows, entries, fixedRange = null) {
  const values = [];
  rows.forEach((row) => entries.forEach((entry) => {
    const value = numericValue(row[entry.field]);
    if (value !== null) values.push(value);
  }));
  let [minimum, maximum] = fixedRange || (values.length
    ? [Math.min(...values), Math.max(...values)] : [0, 1]);
  if (minimum === maximum) {
    minimum -= 1;
    maximum += 1;
  }
  if (!fixedRange) minimum = Math.min(0, minimum);
  const step = niceStep(maximum - minimum);
  return {
    bottom: fixedRange ? minimum : Math.floor(minimum / step) * step,
    top: fixedRange ? maximum : Math.ceil(maximum / step) * step,
    step,
  };
}

function normalizedRows(rows, series) {
  const limits = new Map(series.map((entry) => {
    const values = rows.map((row) => numericValue(row[entry.field])).filter((value) => value !== null);
    return [entry.field, values.length ? [Math.min(...values), Math.max(...values)] : null];
  }));
  return rows.map((row) => {
    const copy = { timestamp: row.timestamp };
    series.forEach((entry) => {
      const raw = numericValue(row[entry.field]);
      const limit = limits.get(entry.field);
      if (raw === null || !limit) copy[entry.field] = null;
      else if (limit[0] === limit[1]) copy[entry.field] = 50;
      else copy[entry.field] = 100 * (raw - limit[0]) / (limit[1] - limit[0]);
    });
    return copy;
  });
}

function localTimestampParts(timestamp) {
  const match = String(timestamp ?? '').match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/);
  if (!match) return null;
  return { day: match[1], minute: Number(match[2]) * 60 + Number(match[3]) };
}

function goodweTimeAxis(rows, x, padding, range) {
  if (range !== '-7d' && range !== '-30d') {
    const labels = [];
    const tickCount = Math.min(6, rows.length);
    for (let index = 0; index < tickCount; index += 1) {
      const rowIndex = Math.round((index / Math.max(1, tickCount - 1)) * (rows.length - 1));
      labels.push(`<text class="axis-label x-time-label" x="${x(rowIndex).toFixed(1)}" y="${HEIGHT - 8}" text-anchor="middle">${time(rows[rowIndex].timestamp)}</text>`);
    }
    return { markup: labels.join(''), dayCount: 0 };
  }

  const days = new Map();
  rows.forEach((row, index) => {
    const local = localTimestampParts(row.timestamp);
    if (!local) return;
    const entries = days.get(local.day) || [];
    entries.push({ index, minute: local.minute });
    days.set(local.day, entries);
  });
  const markup = [];
  const usedIndexes = new Set();
  days.forEach((entries, day) => {
    entries.sort((left, right) => left.minute - right.minute || left.index - right.index);
    const major = entries[0];
    usedIndexes.add(major.index);
    markup.push(`<line class="x-marker x-marker--major" data-day="${day}" data-sample-index="${major.index}" x1="${x(major.index).toFixed(1)}" x2="${x(major.index).toFixed(1)}" y1="${padding.top}" y2="${HEIGHT - padding.bottom}"/>`);
    const labelDate = new Date(`${day}T12:00:00`);
    markup.push(`<text class="axis-label x-day-label" data-day="${day}" x="${x(major.index).toFixed(1)}" y="${HEIGHT - 8}" text-anchor="middle">${time(labelDate, { weekday: 'short', day: '2-digit', month: '2-digit' })}</text>`);
    [360, 720, 1080].forEach((boundary) => {
      const minor = entries
        .filter((entry) => entry.minute >= boundary - 180
          && entry.minute < boundary + 180 && !usedIndexes.has(entry.index))
        .sort((left, right) => Math.abs(left.minute - boundary) - Math.abs(right.minute - boundary)
          || left.index - right.index)[0];
      if (!minor) return;
      usedIndexes.add(minor.index);
      const localTime = `${String(boundary / 60).padStart(2, '0')}:00`;
      markup.push(`<line class="x-marker x-marker--minor" data-day="${day}" data-local-time="${localTime}" data-sample-index="${minor.index}" x1="${x(minor.index).toFixed(1)}" x2="${x(minor.index).toFixed(1)}" y1="${HEIGHT - padding.bottom - 18}" y2="${HEIGHT - padding.bottom}"/>`);
    });
  });
  return { markup: markup.join(''), dayCount: days.size };
}

/** GoodWe History-only renderer for approved dual-axis actual values and unitless trends. */
export function renderGoodWeHistoryChart(container, {
  rows = [], series = [], mode = 'actual', range = '-24h', trendAxisLabel = '', ariaLabel = '',
}) {
  const active = series.filter((entry) => rows.some((row) => numericValue(row[entry.field]) !== null));
  if (!rows.length || !active.length) {
    container.innerHTML = `<p class="notice">${container.dataset.emptyText || ''}</p>`;
    return;
  }

  const plottedRows = mode === 'trend' ? normalizedRows(rows, active) : rows.map((row) => {
    const copy = { timestamp: row.timestamp };
    active.forEach((entry) => {
      const value = numericValue(row[entry.field]);
      copy[entry.field] = value === null ? null : value * entry.scale;
    });
    return copy;
  });
  const groups = [...new Set(active.map((entry) => entry.group))];
  const groupAxes = new Map();
  if (mode === 'actual') {
    groups.forEach((group) => {
      const preferred = active.find((entry) => entry.group === group)?.axis || 'left';
      const occupied = new Set(groupAxes.values());
      groupAxes.set(group, occupied.has(preferred) ? (preferred === 'left' ? 'right' : 'left') : preferred);
    });
  }
  const hasRightAxis = mode === 'actual' && [...groupAxes.values()].includes('right');
  const padding = { top: 22, right: hasRightAxis ? 58 : 18, bottom: 28, left: 58 };
  const plotWidth = WIDTH - padding.left - padding.right;
  const plotHeight = HEIGHT - padding.top - padding.bottom;
  const x = (index) => padding.left + (plottedRows.length === 1
    ? plotWidth / 2 : (index / (plottedRows.length - 1)) * plotWidth);
  const scales = new Map();
  if (mode === 'trend') {
    scales.set('trend', { bottom: 0, top: 100, step: 20 });
  } else {
    groups.forEach((group) => {
      const entries = active.filter((entry) => entry.group === group);
      const fixed = entries.every((entry) => entry.axisMin === 0 && entry.axisMax === 100) ? [0, 100] : null;
      scales.set(group, axisScale(plottedRows, entries, fixed));
    });
  }
  const scaleFor = (entry) => scales.get(mode === 'trend' ? 'trend' : entry.group);
  const yFor = (entry) => {
    const scale = scaleFor(entry);
    return (value) => padding.top + plotHeight
      - ((value - scale.bottom) / (scale.top - scale.bottom || 1)) * plotHeight;
  };

  const axisMarkup = [];
  const axisGroups = mode === 'trend'
    ? [{ key: 'trend', side: 'left', unit: trendAxisLabel }]
    : groups.map((group) => {
      const entry = active.find((candidate) => candidate.group === group);
      return { key: group, side: groupAxes.get(group), unit: entry.unit };
    });
  axisGroups.forEach(({ key, side, unit }, axisIndex) => {
    const scale = scales.get(key);
    const entry = mode === 'trend' ? active[0] : active.find((candidate) => candidate.group === key);
    const axisX = side === 'right' ? WIDTH - padding.right + 8 : padding.left - 8;
    const anchor = side === 'right' ? 'start' : 'end';
    const axisColor = mode === 'trend' ? 'currentColor' : entry.color;
    for (let value = scale.bottom; value <= scale.top + 1e-9; value += scale.step) {
      const y = yFor(entry)(value);
      if (axisIndex === 0) {
        axisMarkup.push(`<line class="grid-line" x1="${padding.left}" x2="${WIDTH - padding.right}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"/>`);
      }
      axisMarkup.push(`<text class="axis-label axis-label--${side}" data-axis="${side}" x="${axisX}" y="${(y + 4).toFixed(1)}" text-anchor="${anchor}" style="color:${axisColor}">${num(value, scale.step < 1 ? 1 : 0)}</text>`);
    }
    axisMarkup.push(`<text class="axis-label axis-unit axis-unit--${side}" data-axis-unit="${side}" x="${axisX}" y="${padding.top - 8}" text-anchor="${anchor}" style="color:${axisColor}">${escapeHtml(unit)}</text>`);
  });

  const timeAxis = goodweTimeAxis(plottedRows, x, padding, range);
  const minimumWidth = Math.max(720, timeAxis.dayCount * 84);
  const paths = active.map((entry) => {
    const path = pathFor(plottedRows, entry.field, x, yFor(entry));
    const values = plottedRows.map((row) => numericValue(row[entry.field])?.toFixed(4) ?? 'gap').join(',');
    return `<path class="series-line" data-field="${escapeHtml(entry.field)}" data-values="${values}" stroke="${entry.color}" d="${path}"/>`;
  }).join('');

  container.innerHTML = `
    <svg class="chart goodwe-history-chart" data-mode="${mode}" data-range="${escapeHtml(range)}" viewBox="0 0 ${WIDTH} ${HEIGHT}" preserveAspectRatio="none" role="img" aria-label="${escapeHtml(ariaLabel)}" style="min-width:${minimumWidth}px">
      <g>${axisMarkup.join('')}</g>
      <g>${timeAxis.markup}</g>
      ${paths}
      <line class="crosshair" y1="${padding.top}" y2="${HEIGHT - padding.bottom}" x1="0" x2="0" hidden/>
      <rect x="${padding.left}" y="${padding.top}" width="${plotWidth}" height="${plotHeight}" fill="transparent"/>
    </svg>
    <div class="tooltip" hidden></div>`;
  attachGoodWeCrosshair(container, rows, active, { x, plotWidth, padding });
}

function attachGoodWeCrosshair(container, rawRows, series, { x, plotWidth, padding }) {
  const svg = container.querySelector('svg');
  const crosshair = svg.querySelector('.crosshair');
  const tooltip = container.querySelector('.tooltip');
  const move = (event) => {
    const bounds = svg.getBoundingClientRect();
    const pointer = (event.touches ? event.touches[0].clientX : event.clientX) - bounds.left;
    const ratio = pointer / bounds.width;
    const index = Math.max(0, Math.min(rawRows.length - 1,
      Math.round((ratio * WIDTH - padding.left) / plotWidth * (rawRows.length - 1))));
    const row = rawRows[index];
    crosshair.setAttribute('x1', x(index));
    crosshair.setAttribute('x2', x(index));
    crosshair.removeAttribute('hidden');
    tooltip.innerHTML = `<strong>${time(row.timestamp)}</strong>` + series.map((entry) => {
      const raw = numericValue(row[entry.field]);
      const value = raw === null ? '–' : num(raw * entry.scale, 2);
      return `<span class="tooltip-row" data-field="${escapeHtml(entry.field)}" style="color:${entry.color}"><span class="swatch" style="background:${entry.color}"></span>${escapeHtml(entry.label)}: ${value} ${escapeHtml(entry.unit)}</span>`;
    }).join('');
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(bounds.width - tooltip.offsetWidth - 8, Math.max(0, pointer + 12))}px`;
    tooltip.style.top = '16px';
  };
  const hide = () => { crosshair.setAttribute('hidden', ''); tooltip.hidden = true; };
  svg.addEventListener('mousemove', move);
  svg.addEventListener('mouseleave', hide);
  svg.addEventListener('touchstart', move, { passive: true });
  svg.addEventListener('touchmove', move, { passive: true });
  svg.addEventListener('touchend', hide);
}

/**
 * @param {object} options
 *   rows    – pole záznamů se `timestamp`
 *   series  – [{ field, labelKey|label, color, area }]
 *   unit    – jednotka osy Y
 *   scale   – násobitel hodnot (např. 0.001 pro W → kW)
 *   yMin/yMax – volitelné pevné meze osy Y
 */
export function renderChart(container, {
  rows = [], series = [], unit = '', scale = 1, yMin = null, yMax = null,
}) {
  const available = series.filter((entry) => rows.some((row) => numericValue(row[entry.field]) !== null));
  if (!rows.length || !available.length) {
    container.innerHTML = `<p class="notice">${container.dataset.emptyText || ''}</p>`;
    return;
  }
  const enabled = new Set(available.map((entry) => entry.field));

  const draw = () => {
    container.innerHTML = '';
    const active = available.filter((entry) => enabled.has(entry.field));

    const scaled = rows.map((row) => {
      const copy = { timestamp: row.timestamp };
      active.forEach(({ field }) => {
        const value = numericValue(row[field]);
        copy[field] = value === null ? null : value * scale;
      });
      return copy;
    });

    const [dataMin, dataMax] = extent(scaled, active.map((entry) => entry.field));
    const min = Number.isFinite(yMin) ? yMin : dataMin;
    const max = Number.isFinite(yMax) ? yMax : dataMax;
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
      <div class="tooltip" hidden></div>
      <div class="legend">${available.map((entry, index) =>
        `<button type="button" class="legend-toggle" data-series-index="${index}" aria-pressed="${enabled.has(entry.field)}"><span class="swatch" style="background:${entry.color}"></span>${entry.label}</button>`).join('')}</div>`);

    container.querySelectorAll('.legend-toggle').forEach((button) => {
      button.addEventListener('click', () => {
        const field = available[Number(button.dataset.seriesIndex)].field;
        if (enabled.has(field)) enabled.delete(field);
        else enabled.add(field);
        draw();
      });
    });

    attachCrosshair(container, scaled, active, unit, { x, plotWidth });
  };

  draw();
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
    tooltip.innerHTML = `<strong>${time(row.timestamp)}</strong>` + series.map((entry) =>
      `<span class="tooltip-row" style="color:${entry.color}"><span class="swatch" style="background:${entry.color}"></span>${entry.label}: ${num(row[entry.field], 2)} ${unit}</span>`).join('');
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
  const head = series.map((entry) => `<th>${entry.label} [${entry.unit ?? unit}]</th>`).join('');
  const body = rows.map((row) => `<tr><td>${time(row.timestamp, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>`
    + series.map((entry) => `<td>${num(row[entry.field], 2)}</td>`).join('') + '</tr>').join('');
  container.innerHTML = `<div class="table-wrap"><table class="data"><thead><tr><th>Čas</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
