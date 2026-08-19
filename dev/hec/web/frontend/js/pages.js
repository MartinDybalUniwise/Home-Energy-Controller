// Stránky rozhraní. Každá odpovídá na tři otázky: co se děje, proč, co bude dál.

import { renderChart, renderTable } from './chart.js';
import { renderFlow } from './flow.js';
import { availableLanguages, currentLanguage, dateTime, duration, num, power, t, time, weekday } from './i18n.js';
import { weatherIcon } from './icons.js';

const SERIES_COLORS = {
  pv_w: 'var(--series-pv)',
  house_w: 'var(--series-house)',
  battery_charge_w: 'var(--series-battery)',
  battery_discharge_w: 'var(--series-battery)',
  battery_soc: 'var(--series-battery)',
  grid_import_w: 'var(--series-grid-import)',
  grid_export_w: 'var(--series-grid-export)',
  heatpump_power_w: 'var(--series-heatpump)',
  appliances_power_w: 'var(--series-appliances)',
  power_w: 'var(--series-appliances)',
  outside_temperature: 'var(--series-house)',
  boiler_temperature: 'var(--series-grid-import)',
  room_temperature: 'var(--series-heatpump)',
  water_output_temperature: 'var(--series-battery)',
};

const SERIES_LABELS = {
  pv_w: 'entity.pv',
  house_w: 'entity.house',
  battery_charge_w: 'entity.battery_charge',
  battery_discharge_w: 'entity.battery_discharge',
  battery_soc: 'entity.battery_soc',
  grid_import_w: 'entity.grid_import',
  grid_export_w: 'entity.grid_export',
  heatpump_power_w: 'entity.heatpump',
  appliances_power_w: 'entity.appliances',
  outside_temperature: 'entity.outside',
  room_temperature: 'entity.room',
  boiler_temperature: 'entity.dhw',
  water_output_temperature: 'entity.water_out',
};

const bigValue = (watts) => {
  const { value, unit } = power(watts);
  return `<span class="value big">${value}<span class="unit">${unit}</span></span>`;
};

const card = (titleKey, inner) => `<div class="card"><h3>${t(titleKey)}</h3>${inner}</div>`;

// --- Přehled ---------------------------------------------------------------

export async function overview(view, { api, motion }) {
  const [current, weather, prices] = await Promise.all([
    api.current(), api.weather().catch(() => ({})), api.prices().catch(() => ({})),
  ]);
  const sources = current.sources || {};
  const goodwe = sources.goodwe || {};
  const tng = sources.tng || {};
  const shelly = sources.shelly || {};
  const ote = sources.ote || {};
  const heatpumpW = shelly.heatpump_power_w ?? null;

  view.innerHTML = `
    <div>
      <span class="section-tab">${t('overview.title')}</span>
      <section class="panel">
        <div class="stripe" id="stripe"></div>
      </section>
    </div>
    <div>
      <span class="section-tab">${t('overview.flow')}</span>
      <section class="panel">
        <div id="flow"></div>
        <div class="cards" id="tiles"></div>
      </section>
    </div>`;

  renderStripe(view.querySelector('#stripe'), { goodwe, weather, prices, ote });
  renderFlow(view.querySelector('#flow'), { ...goodwe, heatpump_power_w: heatpumpW }, t, motion);

  const tiles = [
    card('entity.battery_soc', `<span class="value">${num(goodwe.battery_soc, 0)}<span class="unit">%</span></span>`),
    card('entity.heatpump', heatpumpW === null
      ? `<span class="value">–</span>` : bigValue(heatpumpW).replace('big', '')),
    card('entity.dhw', `<span class="value">${num(tng.boiler_temperature, 1)}<span class="unit">°C</span></span>`
      + `<p class="meta">${t('entity.heating')}: ${tng.heating_on === undefined ? '–' : t(tng.heating_on ? 'status.yes' : 'status.no')} · ${num(tng.heating_set_temperature, 0)} °C</p>`),
    card('entity.outside', `<span class="value">${num(tng.outside_temperature ?? weather?.current?.temp_c, 1)}<span class="unit">°C</span></span>`),
    card('entity.price', `<span class="value">${num(ote.price_total_czk_kwh ?? ote.price_czk_kwh, 2)}<span class="unit">${t('unit.czk_kwh')}</span></span>`),
    card('overview.phases', phaseTile(goodwe)),
  ].join('');
  view.querySelector('#tiles').innerHTML = tiles;

  const decision = current.status?.controller?.last_decision;
  view.querySelector('#tiles').insertAdjacentHTML('beforeend', card('overview.last_decision',
    decision
      ? `<p class="meta">${t(decision.reason_key, decision.reason_params) || ''}</p>`
      + `<p class="meta">${dateTime(decision.timestamp)}</p>`
      : `<p class="meta">${t('overview.no_decision')}</p>`));
}

function phaseTile(goodwe) {
  const phases = [goodwe.l1_w, goodwe.l2_w, goodwe.l3_w];
  if (phases.some((value) => value === undefined || value === null)) {
    return `<p class="meta">${t('app.no_data')}</p>`;
  }
  return phases.map((value, index) => `<div class="meta">L${index + 1}: ${num(value, 0)} W</div>`).join('')
    + `<div class="meta">${t('overview.imbalance')}: ${num(goodwe.phase_imbalance_w, 0)} W</div>`;
}

function localDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function isDaytime(stamp, weather) {
  const daily = (weather?.forecast_daily || []).find((day) => day.date === localDateKey(stamp));
  const sunrise = daily?.sunrise ? new Date(daily.sunrise) : null;
  const sunset = daily?.sunset ? new Date(daily.sunset) : null;
  if (!sunrise || !sunset || Number.isNaN(sunrise.getTime()) || Number.isNaN(sunset.getTime())) {
    return true;          // bez východu/západu slunce se ikona chová jako dřív
  }
  return stamp >= sunrise && stamp <= sunset;
}

function renderStripe(container, { goodwe, weather, prices, ote }) {
  const hours = (weather?.forecast_hourly || []).slice(0, 7);
  const current = weather?.current || {};
  const periods = prices?.today?.periods || [];

  const first = `<div class="col">
      <div class="col-label">${t('overview.now')} · ${time(new Date())}</div>
      ${weatherIcon(current.condition, current.is_day !== false)}
      ${bigValue(goodwe.pv_w)}
      <p class="meta">
        ${t('entity.house')}: ${power(goodwe.house_w).value} ${power(goodwe.house_w).unit}<br>
        ${t('entity.battery_soc')}: ${num(goodwe.battery_soc, 0)} %<br>
        ${t('entity.price')}: ${num(ote.price_total_czk_kwh ?? ote.price_czk_kwh, 2)} ${t('unit.czk_kwh')}<br>
        ${t('weather.wind')}: ${num(current.wind_kmh, 0)} km/h · ${t('weather.cloud_cover')}: ${num(current.cloud_pct, 0)} %
      </p>
    </div>`;

  const columns = hours.map((hour) => {
    const stamp = new Date(hour.time);
    const period = periods.find((p) => p.start <= String(stamp.getHours()).padStart(2, '0') + ':00'
      && p.end > String(stamp.getHours()).padStart(2, '0') + ':00');
    return `<div class="col">
        <div class="col-label">${time(stamp)}</div>
        ${weatherIcon(hour.condition, isDaytime(stamp, weather))}
        <span class="value">${num(hour.temp_c, 0)}<span class="unit">°C</span></span>
        <div class="value alt">${period ? num(period.price_total_czk_kwh, 2) : '–'}</div>
        <div class="col-label">${t('unit.czk_kwh')}</div>
      </div>`;
  }).join('');

  container.innerHTML = first + (columns || `<div class="col"><p class="meta">${t('app.no_data')}</p></div>`);
}

// --- Historie ---------------------------------------------------------------

const RANGES = [
  { key: 'history.range_today', from: 'today' },
  { key: 'history.range_24h', from: '-24h' },
  { key: 'history.range_7d', from: '-7d' },
  { key: 'history.range_30d', from: '-30d' },
];

export async function history(view, { api, state }) {
  const { sources } = await api.sources();
  state.historySource = state.historySource && sources.includes(state.historySource)
    ? state.historySource : (sources[0] || 'goodwe');
  state.historyRange = state.historyRange || '-24h';
  state.historyView = state.historyView || 'chart';

  view.innerHTML = `
    <div>
      <span class="section-tab">${t('history.title')}</span>
      <section class="panel">
        <div class="controls">
          <select id="source">${sources.map((name) =>
            `<option value="${name}"${name === state.historySource ? ' selected' : ''}>${name}</option>`).join('')}</select>
          ${RANGES.map((range) => `<button data-range="${range.from}" aria-pressed="${state.historyRange === range.from}">${t(range.key)}</button>`).join('')}
          <button id="toggle-view" aria-pressed="${state.historyView === 'table'}">${t('history.table')}</button>
        </div>
        <div class="chart-wrap" id="chart" style="position:relative"></div>
        <div id="table"></div>
      </section>
    </div>
    <div>
      <span class="section-tab">${t('history.daily_summary')}</span>
      <section class="panel"><div class="cards" id="summaries"></div></section>
    </div>
    <div>
      <span class="section-tab">${t('analysis.title')}</span>
      <section class="panel"><div class="cards" id="analysis"></div></section>
    </div>`;

  const draw = async () => {
    const chart = view.querySelector('#chart');
    chart.innerHTML = `<p class="notice">${t('app.loading')}</p>`;
    const payload = await api.history({ source: state.historySource, from: state.historyRange, to: 'now' });
    const isTemperature = payload.fields.some((field) => field.includes('temperature'));
    const series = payload.fields
      .filter((field) => SERIES_LABELS[field] || isTemperature)
      .map((field) => ({
        field,
        label: t(SERIES_LABELS[field] || field),
        color: SERIES_COLORS[field] || 'var(--series-house)',
        area: field === 'pv_w',
      }));
    const unit = isTemperature ? t('unit.celsius') : t('unit.kw');
    const scale = isTemperature ? 1 : 0.001;

    if (state.historyView === 'table') {
      chart.innerHTML = '';
      renderTable(view.querySelector('#table'), payload.rows.map((row) => {
        const copy = { timestamp: row.timestamp };
        series.forEach(({ field }) => { copy[field] = Number(row[field]) * scale; });
        return copy;
      }), series, unit);
    } else {
      view.querySelector('#table').innerHTML = '';
      chart.dataset.emptyText = t('app.no_data');
      renderChart(chart, { rows: payload.rows, series, unit, scale });
    }
  };

  view.querySelector('#source').addEventListener('change', (event) => {
    state.historySource = event.target.value;
    draw();
  });
  view.querySelectorAll('[data-range]').forEach((button) => button.addEventListener('click', () => {
    state.historyRange = button.dataset.range;
    view.querySelectorAll('[data-range]').forEach((other) =>
      other.setAttribute('aria-pressed', String(other === button)));
    draw();
  }));
  view.querySelector('#toggle-view').addEventListener('click', (event) => {
    state.historyView = state.historyView === 'chart' ? 'table' : 'chart';
    event.target.setAttribute('aria-pressed', String(state.historyView === 'table'));
    draw();
  });

  await draw();
  await renderSummaries(view.querySelector('#summaries'), api);
  await renderAnalysis(view.querySelector('#analysis'), api);
}

async function renderAnalysis(container, api) {
  const [phases, heatpump, cycles, metrics] = await Promise.all([
    api.phases().catch(() => ({ available: false })),
    api.heatpump().catch(() => ({ measured: false })),
    api.appliances(7).catch(() => ({ cycles: [] })),
    api.metrics(30).catch(() => ({ totals: { days: 0 } })),
  ]);

  const parts = [];
  parts.push(card('overview.phases', phases.available
    ? ['l1_w', 'l2_w', 'l3_w'].map((phase, index) =>
        `<div class="meta">L${index + 1}: ⌀ ${num(phases.phases[phase].mean_w, 0)} W · p95 ${num(phases.phases[phase].p95_w, 0)} W</div>`).join('')
      + (phases.recommendations || []).map((item) =>
        `<p class="meta">${t(item.reason_key, item.reason_params)}</p>`).join('')
    : `<p class="meta">${t(phases.reason_key || 'app.no_data')}</p>`));

  parts.push(card('analysis.heatpump_energy', heatpump.measured
    ? `<span class="value">${num(heatpump.energy_kwh, 1)}<span class="unit">${t('unit.kwh')}</span></span>`
      + `<p class="meta">${t('analysis.run_hours')}: ${num(heatpump.run_hours, 1)} ${t('unit.hours')}<br>`
      + `${t('entity.outside')}: ${num(heatpump.mean_outside_c, 1)} °C<br>`
      + `${t('analysis.kwh_per_degree_day')}: ${num(heatpump.kwh_per_degree_day, 2)}</p>`
    : `<p class="meta">${t('analysis.not_measured')}</p>`));

  const recent = (cycles.cycles || []).slice(-6).reverse();
  parts.push(card('history.appliance_cycles', recent.length
    ? recent.map((cycle) => `<p class="meta"><strong>${cycle.name}</strong> ${dateTime(cycle.started)}<br>`
        + `${t('history.duration')}: ${duration(cycle.duration_min)} · ${t('history.energy')}: ${num(cycle.energy_kwh, 2)} ${t('unit.kwh')}`
        + ` · ${t('history.peak')}: ${num(cycle.peak_w, 0)} W</p>`).join('')
    : `<p class="meta">${t('app.no_data')}</p>`));

  const totals = metrics.totals || {};
  parts.push(card('metrics.title', totals.days
    ? `<p class="meta">${t('metrics.period', { days: totals.days })}<br>
        ${t('metrics.self_consumption')}: ${num(totals.self_consumption_pct, 0)} %<br>
        ${t('metrics.self_sufficiency')}: ${num(totals.self_sufficiency_pct, 0)} %<br>
        ${t('entity.pv')}: ${num(totals.pv_kwh, 0)} ${t('unit.kwh')}<br>
        ${t('metrics.cost')}: ${totals.cost_czk === null ? '–' : num(totals.cost_czk, 0) + ' Kč'}<br>
        ${t('metrics.decisions')}: ${metrics.decisions?.total ?? 0} (${t('metrics.applied')} ${metrics.decisions?.applied ?? 0})</p>
       <p class="meta">${t('metrics.no_counterfactual')}</p>`
    : `<p class="meta">${t('app.no_data')}</p>`));

  container.innerHTML = parts.join('');
}

async function renderSummaries(container, api) {
  const { days } = await api.summaries(7).catch(() => ({ days: [] }));
  if (!days.length) { container.innerHTML = `<p class="notice">${t('app.no_data')}</p>`; return; }
  container.innerHTML = days.slice(-7).reverse().map((day) => `
    <div class="card">
      <div class="card-header">${day.date}</div>
      <p class="meta">
        ${t('entity.pv')}: ${num(day.pv_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('entity.house')}: ${num(day.house_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('entity.grid_import')}: ${num(day.grid_import_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('entity.grid_export')}: ${num(day.grid_export_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('overview.self_consumption')}: ${num(day.self_consumption_pct, 0)} %<br>
        ${t('overview.cost_today')}: ${num(day.cost_czk, 0)} Kč
      </p>
    </div>`).join('');
}

// --- Predikce ----------------------------------------------------------------

export async function prediction(view, { api }) {
  const payload = await api.prediction();
  view.innerHTML = `<div><span class="section-tab">${t('prediction.title')}</span>
      <section class="panel"><div class="cards" id="days"></div></section></div>`;

  const container = view.querySelector('#days');
  if (payload.available === false || !(payload.days || []).length) {
    container.innerHTML = `<p class="notice">${t('prediction.not_enough_data')}</p>`;
    return;
  }

  container.innerHTML = payload.days.map((day) => `
    <div class="card">
      <div class="card-header">${weekday(day.date)} ${day.date}</div>
      <span class="value">${num(day.pv_kwh_low, 0)}–${num(day.pv_kwh_high, 0)}<span class="unit">${t('unit.kwh')}</span></span>
      <p class="meta">
        ${t('prediction.expected_pv')} · ${t('prediction.confidence')}: ${t('prediction.confidence_' + (day.confidence || 'low'))}<br>
        ${t('prediction.expected_consumption')}: ${num(day.consumption_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('prediction.expected_grid')}: ${num(day.grid_balance_kwh, 1)} ${t('unit.kwh')}<br>
        ${t('prediction.expected_cost')}: ${num(day.cost_czk, 0)} Kč<br>
        ${t('prediction.heat_demand')}: ${num(day.heat_kwh, 1)} ${t('unit.kwh')}
      </p>
      ${day.best_appliance_window ? `<p class="meta">${t('prediction.best_appliance_window')}: <strong>${day.best_appliance_window}</strong></p>` : ''}
      ${day.best_dhw_window ? `<p class="meta">${t('prediction.best_dhw_window')}: <strong>${day.best_dhw_window}</strong></p>` : ''}
    </div>`).join('');

  if (payload.accuracy) {
    container.insertAdjacentHTML('beforeend', card('prediction.accuracy',
      `<p class="meta">MAPE: ${num(payload.accuracy.pv_mape_pct, 0)} % (${payload.accuracy.samples} dní)</p>`));
  }
}

// --- Nastavení ---------------------------------------------------------------

const SECTION_LABELS = {
  system: 'settings.general', storage: 'settings.storage', logging: 'settings.logging',
  polling: 'settings.polling', goodwe: 'settings.goodwe', tng: 'settings.tng',
  ote: 'settings.ote', weather: 'settings.weather', shelly: 'settings.shelly',
  controller: 'settings.controller', prediction: 'settings.prediction',
  web: 'settings.web', ui: 'settings.ui',
};

export async function settings(view, { api, onUiChange }) {
  const [{ config }, { fields }] = await Promise.all([api.config(), api.configSchema()]);

  const groups = {};
  fields.filter((field) => !['list', 'dict'].includes(field.kind)).forEach((field) => {
    const section = field.path.split('.')[0];
    (groups[section] ||= []).push(field);
  });

  view.innerHTML = `<div><span class="section-tab">${t('settings.title')}</span>
    <section class="panel">
      <form id="settings-form">
        ${Object.entries(groups).map(([section, list]) => `
          <div class="settings-group">
            <h3>${t(SECTION_LABELS[section] || section)}</h3>
            ${list.map((field) => fieldRow(field, valueAt(config, field.path))).join('')}
          </div>`).join('')}
        <div class="controls">
          <button type="submit">${t('settings.save')}</button>
          <span id="settings-message" class="meta"></span>
        </div>
      </form>
    </section></div>`;

  view.querySelector('#settings-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = view.querySelector('#settings-message');
    const payload = {};
    view.querySelectorAll('[data-path]').forEach((input) => {
      const field = fields.find((entry) => entry.path === input.dataset.path);
      setAt(payload, input.dataset.path, readInput(input, field));
    });
    try {
      const result = await api.saveConfig(payload);
      message.textContent = t('settings.saved')
        + (result.restart_required?.length ? ` · ${t('settings.restart_required')}` : '');
      onUiChange?.(payload.ui || {});
    } catch (error) {
      message.innerHTML = `<span class="error">${(error.payload?.errors || [t('error.save_failed')]).join('<br>')}</span>`;
    }
  });
}

function fieldRow(field, value) {
  const id = `f_${field.path.replace(/\./g, '_')}`;
  const label = field.path.split('.').slice(1).join('.');
  let input;
  if (field.kind === 'bool') {
    input = `<input id="${id}" data-path="${field.path}" type="checkbox"${value ? ' checked' : ''}>`;
  } else if (field.kind === 'enum') {
    input = `<select id="${id}" data-path="${field.path}">${field.choices.map((choice) =>
      `<option value="${choice}"${String(choice) === String(value) ? ' selected' : ''}>${choice}</option>`).join('')}</select>`;
  } else if (field.kind === 'int' || field.kind === 'float') {
    const step = field.kind === 'int' ? '1' : 'any';
    input = `<input id="${id}" data-path="${field.path}" type="number" step="${step}"`
      + `${field.min !== null ? ` min="${field.min}"` : ''}${field.max !== null ? ` max="${field.max}"` : ''} value="${value ?? ''}">`;
  } else {
    input = `<input id="${id}" data-path="${field.path}" type="${field.secret ? 'password' : 'text'}" value="${value ?? ''}">`;
  }
  const hint = field.restart ? `<span class="hint">${t('settings.restart_required')}</span>` : '';
  return `<div class="field"><label for="${id}">${label}</label>${input}${hint}</div>`;
}

function readInput(input, field) {
  if (input.type === 'checkbox') return input.checked;
  if (field && (field.kind === 'int' || field.kind === 'float')) return Number(input.value);
  if (field && field.kind === 'enum' && typeof field.default === 'number') return Number(input.value);
  return input.value;
}

const valueAt = (object, path) => path.split('.').reduce((node, part) => (node ?? {})[part], object);

function setAt(object, path, value) {
  const parts = path.split('.');
  const last = parts.pop();
  let node = object;
  parts.forEach((part) => { node = node[part] ||= {}; });
  node[last] = value;
}

// --- Stav ---------------------------------------------------------------
//
// Formátovaný přehled /api/status pro snadné sledování za provozu – žádný
// syrový JSON, jen to, co by člověk chtěl vidět na první pohled. Auto-refresh
// běží každých 5 s a stránka vrací úklidovou funkci, kterou app.js zavolá
// při odchodu na jinou stránku.

function statusPill(ok, okKey, badKey) {
  return `<span class="pill" data-level="${ok ? 'ok' : 'critical'}">${t(ok ? okKey : badKey)}</span>`;
}

function neutralPill(key) {
  // Vypnuto je záměrný výchozí stav, ne porucha – nesmí vypadat jako varování.
  return `<span class="pill" data-level="neutral">${t(key)}</span>`;
}

function renderReaderRow(reader) {
  const state = !reader.enabled
    ? neutralPill('status.disabled')
    : statusPill(!reader.stale, 'status.ok', 'status.stale');
  const age = reader.age_seconds === null ? '–' : `${Math.round(reader.age_seconds)} s`;
  return `<tr>
      <td>${reader.name}</td>
      <td>${state}</td>
      <td>${reader.last_success ? dateTime(reader.last_success) : '–'}</td>
      <td>${age}</td>
      <td>${reader.success_count}</td>
      <td>${reader.error_count}</td>
      <td>${reader.last_error || '–'}</td>
    </tr>`;
}

function renderStatusReport(payload) {
  const readers = Object.values(payload.readers || {});
  const controller = payload.controller || {};
  const decision = controller.last_decision;

  const readerTable = readers.length
    ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>${t('status.source')}</th><th>${t('status.state')}</th>
          <th>${t('status.last_success')}</th><th>${t('status.age')}</th>
          <th>${t('status.successes')}</th><th>${t('status.errors')}</th>
          <th>${t('status.last_error')}</th></tr></thead>
        <tbody>${readers.map(renderReaderRow).join('')}</tbody>
      </table></div>`
    : `<p class="notice">${t('status.no_readers')}</p>`;

  const controllerCard = card('settings.controller', `
    <p class="meta">
      ${controller.enabled
        ? `<span class="pill" data-level="ok">${t('status.controller_running')}</span>`
        : neutralPill('status.controller_disabled')}
      ${controller.enabled && controller.safe_mode
        ? `<span class="pill" data-level="warning">${t('status.safe_mode')}</span>` : ''}
      ${controller.write_enabled ? '' : `<br>${neutralPill('status.write_disabled')}`}
    </p>
    <p class="meta">
      ${t('overview.last_decision')}:<br>
      ${decision ? `<strong>${decision.rule} → ${decision.action}</strong> (${dateTime(decision.timestamp)})<br>${t(decision.reason_key, decision.reason_params) || ''}`
                 : t('overview.no_decision')}
    </p>`);

  const stale = payload.stale_sources || [];
  const infoCard = card('status.title', `
    <p class="meta">
      ${t('app.name')} v${payload.version || '–'}<br>
      ${t('status.started')}: ${payload.started_at ? dateTime(payload.started_at) : '–'}<br>
      ${stale.length
        ? `<span class="pill" data-level="critical">${t('status.stale')}: ${stale.join(', ')}</span>`
        : `<span class="pill" data-level="ok">${t('status.ok')}</span>`}
    </p>`);

  return `<div class="cards">${infoCard}${controllerCard}</div>${readerTable}`;
}

export async function status(view, { api }) {
  view.innerHTML = `
    <div>
      <span class="section-tab">${t('status.title')}</span>
      <section class="panel">
        <div class="controls">
          <button id="status-refresh">${t('app.refresh')}</button>
          <label><input type="checkbox" id="status-auto" checked> ${t('app.auto_refresh')}</label>
          <span class="meta" id="status-updated"></span>
        </div>
        <div id="status-report"></div>
      </section>
    </div>`;

  const report = view.querySelector('#status-report');
  const updated = view.querySelector('#status-updated');

  async function draw() {
    try {
      const payload = await api.status();
      report.innerHTML = renderStatusReport(payload);
      updated.textContent = t('app.updated', { time: time(new Date()) });
    } catch (error) {
      if (error.unauthorised) throw error;
      report.innerHTML = `<p class="notice error">${t('error.load_failed')}</p>`;
    }
  }

  view.querySelector('#status-refresh').addEventListener('click', draw);
  await draw();

  const auto = view.querySelector('#status-auto');
  const timer = setInterval(() => { if (auto.checked) draw(); }, 5000);
  return () => clearInterval(timer);
}

// --- Data (prohlížeč JSONL historie) -------------------------------------
//
// Syrové, nezhuštěné záznamy jednoho zdroje – buď posledních N, nebo celý
// vybraný den. Auto-refresh se týká jen režimu "posledních N", aby procházení
// konkrétního dne neresetovalo rozjetý posun.

function formatLogLine(row) {
  return JSON.stringify(row);
}

export async function logsPage(view, { api }) {
  const { sources } = await api.sources();

  if (!sources.length) {
    view.innerHTML = `<div><span class="section-tab">${t('logs.title')}</span>
      <section class="panel"><p class="notice">${t('logs.no_sources')}</p></section></div>`;
    return;
  }

  view.innerHTML = `
    <div>
      <span class="section-tab">${t('logs.title')}</span>
      <section class="panel">
        <div class="controls">
          <select id="log-source" aria-label="${t('logs.source')}">
            ${sources.map((source) => `<option value="${source}">${source}</option>`).join('')}
          </select>
          <select id="log-day" aria-label="${t('logs.day')}">
            <option value="">${t('logs.tail', { count: 300 })}</option>
          </select>
          <button id="log-refresh">${t('app.refresh')}</button>
          <label><input type="checkbox" id="log-auto" checked> ${t('app.auto_refresh')}</label>
          <span class="meta" id="log-updated"></span>
        </div>
        <pre class="log-view" id="log-view"></pre>
      </section>
    </div>`;

  const sourceSelect = view.querySelector('#log-source');
  const daySelect = view.querySelector('#log-day');
  const box = view.querySelector('#log-view');
  const updated = view.querySelector('#log-updated');

  async function loadDays() {
    const { days } = await api.logDays(sourceSelect.value).catch(() => ({ days: [] }));
    const current = daySelect.value;
    daySelect.innerHTML = `<option value="">${t('logs.tail', { count: 300 })}</option>`
      + days.slice().reverse().map((day) => `<option value="${day}">${day}</option>`).join('');
    if (days.includes(current)) daySelect.value = current;
  }

  async function draw() {
    const params = daySelect.value ? { day: daySelect.value } : { tail: 300 };
    try {
      const payload = await api.logs(sourceSelect.value, params);
      box.textContent = payload.rows.length ? payload.rows.map(formatLogLine).join('\n') : t('app.no_data');
      box.scrollTop = box.scrollHeight;
      updated.textContent = t('app.updated', { time: time(new Date()) });
    } catch (error) {
      if (error.unauthorised) throw error;
      box.textContent = t('error.load_failed');
    }
  }

  sourceSelect.addEventListener('change', async () => { await loadDays(); await draw(); });
  daySelect.addEventListener('change', draw);
  view.querySelector('#log-refresh').addEventListener('click', draw);

  await loadDays();
  await draw();

  const auto = view.querySelector('#log-auto');
  const timer = setInterval(() => { if (auto.checked && !daySelect.value) draw(); }, 8000);
  return () => clearInterval(timer);
}

export const pages = { overview, history, prediction, status, logs: logsPage, settings };
export const helpers = { duration, availableLanguages, currentLanguage };
