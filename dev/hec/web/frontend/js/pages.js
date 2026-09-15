// Stránky rozhraní. Každá odpovídá na tři otázky: co se děje, proč, co bude dál.

import { renderChart, renderTable } from './chart.js';
import { renderForecastStory, renderToday } from './advisor.js?v=13';
import { renderFlow } from './flow.js';
import { availableLanguages, currentLanguage, dateTime, duration, num, power, t, time, weekday } from './i18n.js';
import { weatherIcon } from './icons.js';

const HTML_ESCAPES = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

function escapeParams(params) {
  if (!params || typeof params !== 'object') return params;
  return Object.fromEntries(Object.entries(params).map(([key, value]) => [key, escapeHtml(value)]));
}

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
  const [current, weather, prices, predictionPayload] = await Promise.all([
    api.current({ fast: 1 }), api.weather().catch(() => ({})), api.prices().catch(() => ({})),
    api.prediction().catch(() => ({})),
  ]);
  renderToday(view, { current, weather, prices, prediction: predictionPayload, motion });
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

// Šest tříhodinových úseků dne – běžné dělení počasí v ČR. Noc (21–6) přesahuje
// půlnoc, proto se řadí pod den, kdy začala (viz dayPartFor).
const DAYPARTS = [
  { key: 'morning', fromHour: 6 }, { key: 'forenoon', fromHour: 9 },
  { key: 'noon', fromHour: 12 }, { key: 'afternoon', fromHour: 15 },
  { key: 'evening', fromHour: 18 }, { key: 'night', fromHour: 21 },
];

function dayPartFor(stamp) {
  const hour = stamp.getHours();
  if (hour < 6) {
    const previous = new Date(stamp);
    previous.setDate(previous.getDate() - 1);
    return { dayKey: localDateKey(previous), part: 'night' };
  }
  const part = [...DAYPARTS].reverse().find((entry) => hour >= entry.fromHour);
  return { dayKey: localDateKey(stamp), part: part.key };
}

/** Hodinová předpověď seskupená podle dne a denní doby – pro rozklikávací bloky. */
function groupByDayPart(hours) {
  const days = new Map();
  for (const hour of hours) {
    const stamp = new Date(hour.time);
    if (Number.isNaN(stamp.getTime())) continue;
    const { dayKey, part } = dayPartFor(stamp);
    const parts = days.get(dayKey) || days.set(dayKey, new Map()).get(dayKey);
    const entries = parts.get(part) || parts.set(part, []).get(part);
    entries.push({ ...hour, stamp });
  }
  return days;
}

function renderForecastBlocks(container, weather) {
  const days = groupByDayPart(weather?.forecast_hourly || []);
  if (!days.size) {
    container.innerHTML = `<p class="notice">${t('app.no_data')}</p>`;
    return;
  }

  container.innerHTML = `<div class="forecast-days">${[...days.entries()].map(([dayKey, parts]) => `
    <div class="card">
      <div class="card-header">${weekday(new Date(`${dayKey}T00:00:00`))}, ${time(`${dayKey}T00:00:00`, { day: '2-digit', month: '2-digit' })}</div>
      <div class="daypart-row">
        ${DAYPARTS.filter((entry) => parts.has(entry.key)).map((entry) => {
          const rows = parts.get(entry.key);
          const temps = rows.map((row) => row.temp_c).filter((value) => value !== null && value !== undefined);
          const range = temps.length
            ? `${Math.round(Math.min(...temps))}–${Math.round(Math.max(...temps))}` : '–';
          const middle = rows[Math.floor(rows.length / 2)];
          const blockId = `daypart_${dayKey}_${entry.key}`;
          return `
            <div class="daypart">
              <button type="button" class="daypart-toggle" aria-expanded="false" aria-controls="${blockId}">
                <span class="col-label">${t(`weather.part_${entry.key}`)}</span>
                ${weatherIcon(middle.condition, isDaytime(middle.stamp, weather))}
                <span class="value">${range}<span class="unit">${t('unit.celsius')}</span></span>
                <span class="daypart-chevron" aria-hidden="true"></span>
              </button>
              <div class="daypart-hours" id="${blockId}" hidden>
                ${rows.map((row) => `
                  <div class="daypart-hour">
                    <span class="col-label">${time(row.stamp)}</span>
                    ${weatherIcon(row.condition, isDaytime(row.stamp, weather))}
                    <span class="value">${num(row.temp_c, 0)}<span class="unit">${t('unit.celsius')}</span></span>
                  </div>`).join('')}
              </div>
            </div>`;
        }).join('')}
      </div>
    </div>`).join('')}</div>`;

  container.querySelectorAll('.daypart-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!expanded));
      container.querySelector(`#${button.getAttribute('aria-controls')}`).hidden = expanded;
    });
  });
}

/** Cenová perioda pro daný okamžik – OTE vrací zvlášť dnešek a zítřek, takže
 * se nejdřív vybere správný den a teprve v něm 15minutová perioda. */
function periodFor(stamp, prices) {
  const dateKey = localDateKey(stamp);
  const day = [prices?.today, prices?.tomorrow].find((candidate) => candidate?.date === dateKey);
  const clock = `${String(stamp.getHours()).padStart(2, '0')}:00`;
  return (day?.periods || []).find((p) => p.start <= clock && p.end > clock) || null;
}

function renderStripe(container, { goodwe, weather, prices, ote }) {
  // Žádné oříznutí na pár hodin – kolik dopředu je vidět, určuje jen to, kolik
  // dat mají zdroje (weather.forecast_days, OTE dnešek+zítřek); posun je na
  // uživateli přes vodorovné scrollování pruhu (viz .stripe v app.css).
  const hours = weather?.forecast_hourly || [];
  const current = weather?.current || {};
  const todayKey = localDateKey(new Date());

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
    const period = periodFor(stamp, prices);
    // Jakmile sloupec patří jinému dni než dnešku, přidá se zkratka dne v
    // týdnu – jinak by se ve stovce hodin ztratilo, kde jeden den končí.
    const label = localDateKey(stamp) === todayKey ? time(stamp)
      : time(stamp, { weekday: 'short', hour: '2-digit', minute: '2-digit' });
    return `<div class="col">
        <div class="col-label">${label}</div>
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
            `<option value="${escapeHtml(name)}"${name === state.historySource ? ' selected' : ''}>${escapeHtml(name)}</option>`).join('')}</select>
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
    const isSdgHistory = state.historySource === 'sdg_history';
    const isTemperature = payload.fields.some((field) => field.includes('temperature'));
    const series = payload.fields
      .filter((field) => isSdgHistory || SERIES_LABELS[field] || isTemperature)
      .map((field) => ({
        field,
        label: t(SERIES_LABELS[field] || field),
        color: SERIES_COLORS[field] || 'var(--series-house)',
        area: field === 'pv_w',
      }));
    const unit = isSdgHistory ? '' : isTemperature ? t('unit.celsius') : t('unit.kw');
    const scale = isSdgHistory || isTemperature ? 1 : 0.001;

    // Navigace může mezitím nahradit celý view. Starý dotaz pak nesmí
    // přepisovat novou stránku ani vyvolat chybu při hledání původní tabulky.
    if (!chart.isConnected || !view.querySelector('#table')) return;

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
        `<p class="meta">${translatedText(item.reason_key, item.reason_params, item.reason_key || '')}</p>`).join('')
    : `<p class="meta">${phases.reason_key ? translatedText(phases.reason_key, undefined, phases.reason_key) : t('app.no_data')}</p>`));

  parts.push(card('analysis.heatpump_energy', heatpump.measured
    ? `<span class="value">${num(heatpump.energy_kwh, 1)}<span class="unit">${t('unit.kwh')}</span></span>`
      + `<p class="meta">${t('analysis.run_hours')}: ${num(heatpump.run_hours, 1)} ${t('unit.hours')}<br>`
      + `${t('entity.outside')}: ${num(heatpump.mean_outside_c, 1)} °C<br>`
      + `${t('analysis.kwh_per_degree_day')}: ${num(heatpump.kwh_per_degree_day, 2)}</p>`
    : `<p class="meta">${t('analysis.not_measured')}</p>`));

  const recent = (cycles.cycles || []).slice(-6).reverse();
  parts.push(card('history.appliance_cycles', recent.length
    ? recent.map((cycle) => `<p class="meta"><strong>${escapeHtml(cycle.name)}</strong> ${dateTime(cycle.started)}<br>`
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

  if (container.isConnected) container.innerHTML = parts.join('');
}

async function renderSummaries(container, api) {
  const { days } = await api.summaries(7).catch(() => ({ days: [] }));
  if (!container.isConnected) return;
  if (!days.length) { container.innerHTML = `<p class="notice">${t('app.no_data')}</p>`; return; }
  container.innerHTML = days.slice(-7).reverse().map((day) => `
    <div class="card">
      <div class="card-header">${escapeHtml(day.date)}</div>
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
  const [payload, weather, prices] = await Promise.all([
    api.prediction(), api.weather().catch(() => ({})), api.prices().catch(() => ({})),
  ]);
  renderForecastStory(view, { prediction: payload, weather, prices });
  const details = view.querySelector('#forecast-details');
  if (details) renderForecastBlocks(details, weather);
}

// --- Tok energie -------------------------------------------------------------

function translatedText(key, params, fallback = '') {
  const safeFallback = escapeHtml(fallback);
  if (!key) return safeFallback;
  const text = t(key, escapeParams(params));
  return text === key ? safeFallback : text;
}

function batteryStateText(goodwe) {
  return Number(goodwe?.battery_charge_w) > 20 ? t('flow.charging')
    : Number(goodwe?.battery_discharge_w) > 20 ? t('flow.discharging')
      : t('flow.idle');
}

function controllerStateText(controller) {
  if (controller?.safe_mode) {
    return translatedText(controller.safe_mode_reason?.reason_key, controller.safe_mode_reason?.reason_params, t('status.safe_mode_active'));
  }
  return controller?.enabled ? t('status.controller_running') : t('status.controller_disabled');
}

function lastDecisionText(controller) {
  const decision = controller?.last_decision;
  if (!decision) return t('overview.no_decision');
  return translatedText(decision.reason_key, decision.reason_params, `${decision.rule} → ${decision.action}`);
}

export async function flow(view, { api, motion }) {
  const current = await api.current();
  const sources = current.sources || {};
  const goodwe = sources.goodwe || {};
  const shelly = sources.shelly || {};
  const tng = sources.tng || {};
  const controller = current?.status?.controller || {};
  const staleSources = current?.status?.stale_sources || [];
  const grid = Number(goodwe.grid_import_w) > 20 ? 'import' : Number(goodwe.grid_export_w) > 20 ? 'export' : 'balanced';
  const gridPower = Number(goodwe.grid_import_w) || Number(goodwe.grid_export_w);
  const batteryPower = Number(goodwe.battery_charge_w) || Number(goodwe.battery_discharge_w);
  const lastMeasurement = current?.last_measurement_at ? dateTime(current.last_measurement_at) : '–';
  const controllerBadges = [
    controller.enabled
      ? `<span class="pill" data-level="ok">${t('status.controller_running')}</span>`
      : `<span class="pill" data-level="neutral">${t('status.controller_disabled')}</span>`,
    controller.safe_mode ? `<span class="pill" data-level="warning">${t('status.safe_mode')}</span>` : '',
    controller.write_enabled === false ? `<span class="pill" data-level="neutral">${t('status.write_disabled')}</span>` : '',
    staleSources.length ? `<span class="pill" data-level="critical">${t('status.stale')}: ${staleSources.map(escapeHtml).join(', ')}</span>` : '',
  ].filter(Boolean).join('');

  view.innerHTML = `<div class="story-page story-page--flow">
      <section class="story-hero story-hero--flow flow-hero">
        <div class="story-hero__main">
          <p class="story-hero__eyebrow">${t('flow.eyebrow')}</p>
          <h2>${t('flow.title')}</h2>
          <p class="story-hero__summary">${t(`flow.grid_${grid}`)}</p>
        </div>
        <div class="story-hero__aside">
          <dl class="story-hero__stats">
            <div><dt>${t('entity.pv')}</dt><dd>${power(goodwe.pv_w).value}<small>${power(goodwe.pv_w).unit}</small></dd></div>
            <div><dt>${t('entity.house')}</dt><dd>${power(goodwe.house_w).value}<small>${power(goodwe.house_w).unit}</small></dd></div>
            <div><dt>${t('entity.grid')}</dt><dd>${power(gridPower).value}<small>${power(gridPower).unit}</small></dd></div>
            <div><dt>${t('entity.battery_soc')}</dt><dd>${num(goodwe.battery_soc, 0)}<small>${t('unit.percent')}</small></dd></div>
          </dl>
        </div>
      </section>
      <section class="story-surface story-surface--flow flow-stage">
        <header class="story-surface__header">
          <div>
            <p>${t('overview.flow')}</p>
            <h3>${t(`flow.grid_${grid}`)}</h3>
          </div>
          <span class="story-surface__meta">${lastMeasurement}</span>
        </header>
        <div class="story-flow-stage">
          <div id="live-flow"></div>
          <div class="story-flow-summary">
            <p>${batteryStateText(goodwe)}</p>
            <p>${tng.heating_on === true ? t('flow.heating_active') : t('flow.heating_idle')}</p>
            <p>${controllerStateText(controller)}</p>
          </div>
        </div>
      </section>
      <section class="story-card-grid story-card-grid--flow-support flow-details">
        <article class="story-card story-card--soft">
          <p class="story-card__eyebrow">${t('entity.grid')}</p>
          <strong class="story-card__value">${bigValue(gridPower)}</strong>
          <p class="story-card__meta">${t(`flow.grid_${grid}`)}</p>
        </article>
        <article class="story-card story-card--soft">
          <p class="story-card__eyebrow">${t('entity.battery')}</p>
          <strong class="story-card__value">${bigValue(batteryPower)}</strong>
          <p class="story-card__meta">${batteryStateText(goodwe)}</p>
        </article>
        <article class="story-card story-card--soft">
          <p class="story-card__eyebrow">${t('entity.heatpump')}</p>
          <strong class="story-card__value">${bigValue(shelly.heatpump_power_w)}</strong>
          <p class="story-card__meta">${tng.heating_on === true ? t('flow.heating_active') : t('flow.heating_idle')}</p>
        </article>
        <article class="story-card story-card--soft">
          <div class="story-card__header-row">
            <p class="story-card__eyebrow">${t('settings.controller')}</p>
          </div>
          <div class="story-card__status">${controllerBadges}</div>
          <strong class="story-card__value story-card__value--copy">${lastDecisionText(controller)}</strong>
          <p class="story-card__meta">${controller?.last_decision?.timestamp ? dateTime(controller.last_decision.timestamp) : lastMeasurement}</p>
        </article>
      </section>
    </div>`;
  renderFlow(view.querySelector('#live-flow'), { ...goodwe, heatpump_power_w: shelly.heatpump_power_w, devices: shelly.devices }, t, motion);
}

// --- Nastavení ---------------------------------------------------------------

const SECTION_LABELS = {
  system: 'settings.general', storage: 'settings.storage', logging: 'settings.logging',
  polling: 'settings.polling', goodwe: 'settings.goodwe', tng: 'settings.tng',
  ote: 'settings.ote', weather: 'settings.weather', shelly: 'settings.shelly',
  controller: 'settings.controller', prediction: 'settings.prediction',
  web: 'settings.web', ui: 'settings.ui',
};

// Vnořené bloky uvnitř jedné sekce (např. tng.boiler.*) dostanou vlastní
// podnadpis, aby se od plochých polí sekce (tng.write_enabled apod.) opticky
// oddělily – jinak by rozvrh ohřevu, topení a termostatu splynul do jednoho
// nepřehledného seznamu.
const SUBGROUP_LABELS = {
  'goodwe.sdg': 'settings.goodwe_sdg',
  'tng.boiler': 'settings.tng_boiler', 'tng.heating': 'settings.tng_heating',
  'tng.thermostat': 'settings.tng_thermostat',
  'controller.comfort': 'settings.comfort', 'controller.optimization': 'settings.optimization',
};

// Čistě interní pole, která uživatel nikdy nemá důvod měnit ručně.
const HIDDEN_FIELDS = new Set(['system.config_version']);

const VERIFY_TARGETS = {
  'goodwe.sdg.log_root_path': 'sdg',
  'storage.data_path': 'storage.data',
  'storage.logs_path': 'storage.logs',
  'storage.history_path': 'storage.history',
  'storage.archive_path': 'storage.archive',
};

function groupFields(fields) {
  const groups = {};
  fields
    .filter((field) => !['list', 'dict'].includes(field.kind))
    .filter((field) => !HIDDEN_FIELDS.has(field.path))
    .forEach((field) => {
      const parts = field.path.split('.');
      const group = (groups[parts[0]] ||= { direct: [], subs: {} });
      if (parts.length > 2) (group.subs[parts[1]] ||= []).push(field);
      else group.direct.push(field);
    });
  return groups;
}

function verificationMatchesHost(verification, host) {
  return Boolean(verification?.verified && verification.status === 'SUCCESS' && verification.host === host);
}

function goodweAuthorizationLevel(status) {
  if (status === 'APPROVED') return 'ok';
  if (status === 'INVALID') return 'critical';
  return 'warning';
}

function renderGoodWeAuthorization(auth, config) {
  const authorization = auth?.authorization || {};
  const verification = auth?.verification || {};
  const host = String(valueAt(config, 'goodwe.host') || '').trim();
  const canApprove = verificationMatchesHost(verification, host);
  const verificationText = verification.status
    ? t(verification.message_key || (verification.verified ? 'settings.goodwe_verify_ok' : 'settings.goodwe_verify_failed'))
    : t('settings.goodwe_verify_missing');
  const details = [verification.host, verification.model, verification.firmware].filter(Boolean).map(escapeHtml).join(' · ');
  return `<div class="goodwe-authorization" data-goodwe-authorization>
    <h4>${t('settings.goodwe_authorization')}</h4>
    <dl>
      <dt>${t('settings.goodwe_authorization_status')}</dt><dd><span class="pill" data-level="${goodweAuthorizationLevel(authorization.status)}">${escapeHtml(authorization.status || 'NOT_AUTHORIZED')}</span></dd>
      <dt>${t('settings.goodwe_verification_status')}</dt><dd data-goodwe-verification-text>${escapeHtml(verificationText)}${details ? ` · ${details}` : ''}</dd>
    </dl>
    <div class="goodwe-authorization__actions">
      <button type="button" class="field-verify" data-goodwe-verify>${t('settings.verify')}</button>
      <button type="button" class="field-verify" data-goodwe-approve${canApprove ? '' : ' disabled'}>${t('settings.goodwe_approve')}</button>
      <span class="field-verify-result" data-goodwe-authorization-message aria-live="polite">${canApprove ? t('settings.goodwe_approve_ready') : t('settings.goodwe_approve_disabled')}</span>
    </div>
  </div>`;
}

function updateGoodWeAuthorization(view, auth) {
  const config = {};
  view.querySelectorAll('[data-path]').forEach((input) => {
    setAt(config, input.dataset.path, input.type === 'checkbox' ? input.checked : input.value);
  });
  const panel = view.querySelector('[data-goodwe-authorization]');
  if (panel) panel.outerHTML = renderGoodWeAuthorization(auth, config);
}

function settingsGroup(section, group, config, goodweAuth) {
  return `<div class="settings-group">
    <h3>${t(SECTION_LABELS[section] || section)}</h3>
    ${group.direct.map((field) => fieldRow(field, valueAt(config, field.path))).join('')}
    ${section === 'goodwe' ? renderGoodWeAuthorization(goodweAuth, config) : ''}
    ${Object.entries(group.subs).map(([sub, list]) => `
      <div class="settings-subgroup">
        <h4>${t(SUBGROUP_LABELS[`${section}.${sub}`] || sub)}</h4>
        ${list.map((field) => fieldRow(field, valueAt(config, field.path))).join('')}
      </div>`).join('')}
  </div>`;
}

export async function settings(view, { api, onUiChange }) {
  const [{ config }, { fields }, goodweAuth] = await Promise.all([
    api.config(), api.configSchema(), api.goodweAuthorization().catch(() => ({})),
  ]);
  const groups = groupFields(fields);
  const personal = Object.entries(groups).filter(([section]) => section === 'ui');
  const technical = Object.entries(groups).filter(([section]) => section !== 'ui');

  view.innerHTML = `<div><span class="section-tab">${t('settings.title')}</span>
    <section class="panel">
      <form id="settings-form">
        <div class="settings-intro"><p>${t('settings.personal_title')}</p><h2>${t('settings.personal_intro')}</h2></div>
        ${personal.map(([section, group]) => settingsGroup(section, group, config, goodweAuth)).join('')}
        <details class="technical-settings"><summary><span>${t('settings.technical_title')}</span><small>${t('settings.technical_intro')}</small></summary>
          ${technical.map(([section, group]) => settingsGroup(section, group, config, goodweAuth)).join('')}
        </details>
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
      await onUiChange?.(payload.ui || {});
    } catch (error) {
      message.innerHTML = `<span class="error">${(error.payload?.errors || [t('error.save_failed')]).map(escapeHtml).join('<br>')}</span>`;
    }
  });

  view.querySelectorAll('[data-verify-target]').forEach((button) => {
    button.addEventListener('click', async () => {
      const result = button.closest('.field').querySelector('.field-verify-result');
      button.disabled = true;
      result.textContent = t('settings.verify_checking');
      try {
        const payload = await api.verifyConfig(button.dataset.verifyTarget);
        result.textContent = `${t(payload.message_key)}${payload.file_count !== undefined ? ` · ${payload.file_count} ${t('settings.verify_files')}` : ''}`;
        result.dataset.level = payload.available ? 'ok' : 'warning';
      } catch (error) {
        result.textContent = error.unauthorised ? t('error.unauthorised') : t('settings.verify_failed');
        result.dataset.level = 'critical';
      } finally {
        button.disabled = false;
      }
    });
  });

  const hostInput = view.querySelector('[data-path="goodwe.host"]');
  hostInput?.addEventListener('input', async () => {
    const auth = await api.goodweAuthorization().catch(() => ({}));
    updateGoodWeAuthorization(view, auth);
  });

  view.addEventListener('click', async (event) => {
    const verify = event.target.closest?.('[data-goodwe-verify]');
    const approve = event.target.closest?.('[data-goodwe-approve]');
    if (!verify && !approve) return;
    const message = view.querySelector('[data-goodwe-authorization-message]');
    const button = verify || approve;
    button.disabled = true;
    if (message) message.textContent = t(verify ? 'settings.verify_checking' : 'settings.goodwe_approve_saving');
    try {
      const auth = verify ? await api.verifyGoodweAuthorization() : await api.approveGoodweAuthorization();
      updateGoodWeAuthorization(view, verify ? { verification: auth } : auth);
    } catch (error) {
      const auth = error.payload?.authorization ? error.payload : await api.goodweAuthorization().catch(() => ({}));
      updateGoodWeAuthorization(view, auth);
      const targetMessage = view.querySelector('[data-goodwe-authorization-message]');
      if (targetMessage) {
        targetMessage.textContent = error.unauthorised ? t('error.unauthorised') : t(error.payload?.message_key || 'settings.verify_failed');
        targetMessage.dataset.level = 'critical';
      }
    }
  });
}

function fieldRow(field, value) {
  const id = escapeHtml(`f_${field.path.replace(/\./g, '_')}`);
  const fieldPath = escapeHtml(field.path);
  const labelKey = `settings.field.${field.path}`;
  const helpKey = `settings.help.${field.path}`;
  // t() echoes back an unknown key verbatim – fall back to the raw config
  // path rather than show a translation key like "settings.field.x.y" in
  // the UI if a field is ever added to the schema without a translation.
  const translatedLabel = t(labelKey);
  const label = escapeHtml(translatedLabel === labelKey ? field.path.split('.').slice(1).join('.') : translatedLabel);
  const translatedHelp = t(helpKey);
  const help = translatedHelp === helpKey ? '' : `<p class="field-help">${escapeHtml(translatedHelp)}</p>`;
  let input;
  if (field.kind === 'bool') {
    input = `<input id="${id}" data-path="${fieldPath}" type="checkbox"${value ? ' checked' : ''}>`;
  } else if (field.kind === 'enum') {
    input = `<select id="${id}" data-path="${fieldPath}">${field.choices.map((choice) =>
      `<option value="${escapeHtml(choice)}"${String(choice) === String(value) ? ' selected' : ''}>${escapeHtml(choice)}</option>`).join('')}</select>`;
  } else if (field.kind === 'int' || field.kind === 'float') {
    const step = field.kind === 'int' ? '1' : 'any';
    input = `<input id="${id}" data-path="${fieldPath}" type="number" step="${step}"`
      + `${field.min !== null ? ` min="${field.min}"` : ''}${field.max !== null ? ` max="${field.max}"` : ''} value="${escapeHtml(value ?? '')}">`;
  } else {
    input = `<input id="${id}" data-path="${fieldPath}" type="${field.secret ? 'password' : 'text'}" value="${escapeHtml(value ?? '')}">`;
  }
  const hint = field.restart ? `<span class="hint">${t('settings.restart_required')}</span>` : '';
  const verifyTarget = VERIFY_TARGETS[field.path];
  const verify = verifyTarget
    ? `<button type="button" class="field-verify" data-verify-target="${verifyTarget}">${t('settings.verify')}</button><span class="field-verify-result" aria-live="polite"></span>`
    : '';
  return `<div class="field"><label for="${id}">${label}</label>${input}${verify}${hint}${help}</div>`;
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
      <td>${escapeHtml(reader.name)}</td>
      <td>${state}</td>
      <td>${reader.last_success ? dateTime(reader.last_success) : '–'}</td>
      <td>${age}</td>
      <td>${reader.success_count}</td>
      <td>${reader.error_count}</td>
      <td>${reader.last_error ? escapeHtml(reader.last_error) : '–'}</td>
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
      ${decision ? `<strong>${escapeHtml(decision.rule)} → ${escapeHtml(decision.action)}</strong> (${dateTime(decision.timestamp)})<br>${translatedText(decision.reason_key, decision.reason_params)}`
                 : t('overview.no_decision')}
    </p>`);

  const goodwe = payload.goodwe_diagnostics || {};
  const writer = payload.goodwe_writer_diagnostics || {};
  const sdg = payload.sdg_diagnostics || {};
  const diagnosticsCard = card('status.goodwe_diagnostics', `
    <dl class="status-details">
      <dt>${t('status.connection')}</dt><dd>${goodwe.connected ? t('status.connected') : t('status.disconnected')}</dd>
      <dt>${t('status.model_firmware')}</dt><dd>${escapeHtml(goodwe.model || '–')} / ${escapeHtml(goodwe.firmware || '–')}</dd>
      <dt>${t('status.last_read')}</dt><dd>${goodwe.last_read ? dateTime(goodwe.last_read) : '–'}</dd>
      <dt>${t('status.last_write')}</dt><dd>${goodwe.last_write?.command || '–'}</dd>
      <dt>${t('status.retries')}</dt><dd>${num(goodwe.retry_count, 0)}</dd>
      <dt>${t('status.writer')}</dt><dd>${writer.enabled ? t('status.enabled') : t('status.disabled')}</dd>
      <dt>${t('status.authorization')}</dt><dd>${escapeHtml(writer.hardware_authorization?.status || goodwe.hardware_authorization?.status || 'NOT_AUTHORIZED')}</dd>
      <dt>${t('status.sdg')}</dt><dd>${sdg.enabled ? t('status.enabled') : t('status.disabled')} / ${sdg.available ? t('status.available') : t('status.unavailable')}</dd>
      <dt>${t('status.sdg_checkpoint')}</dt><dd>${escapeHtml(sdg.checkpoint || '–')}</dd>
    </dl>`);

  const stale = payload.stale_sources || [];
  const infoCard = card('status.title', `
    <p class="meta">
      ${t('app.name')} v${payload.version ? escapeHtml(payload.version) : '–'}<br>
      ${t('status.started')}: ${payload.started_at ? dateTime(payload.started_at) : '–'}<br>
      ${stale.length
        ? `<span class="pill" data-level="critical">${t('status.stale')}: ${stale.map(escapeHtml).join(', ')}</span>`
        : `<span class="pill" data-level="ok">${t('status.ok')}</span>`}
    </p>`);

  return `<div class="cards">${infoCard}${controllerCard}${diagnosticsCard}</div>${readerTable}`;
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

// --- Control & Plan ------------------------------------------------------

function controlPlanPill(level, key) {
  return `<span class="pill" data-level="${level}">${t(key)}</span>`;
}

function controlPlanValue(value, formatter = (item) => escapeHtml(item)) {
  return value === null || value === undefined ? '–' : formatter(value);
}

function sourceState(reader) {
  if (!reader) return controlPlanPill('neutral', 'control_plan.unavailable');
  if (!reader.enabled) return controlPlanPill('neutral', 'status.disabled');
  if (reader.error_count && reader.last_error) return controlPlanPill('critical', 'status.reader_error');
  if (reader.stale) return controlPlanPill('warning', 'status.stale');
  return controlPlanPill('ok', 'status.ok');
}

function deviceMetric(labelKey, value) {
  return `<div class="control-plan-metric"><dt>${t(labelKey)}</dt><dd>${value}</dd></div>`;
}

function renderControlPlanDevice(titleKey, source, current, reader) {
  const values = current || {};
  const sourceLabel = reader?.name || source;
  return `<article class="control-plan-device">
    <header><h3>${t(titleKey)}</h3>${sourceState(reader)}</header>
    <p class="meta">${escapeHtml(sourceLabel)} · ${reader?.last_success ? dateTime(reader.last_success) : t('control_plan.no_observation')}</p>
    <dl class="control-plan-metrics">${values}</dl>
  </article>`;
}

function renderControlPlanMode(titleKey, enabled, reader) {
  const state = enabled === true ? 'on' : enabled === false ? 'off' : 'unknown';
  const labelKey = state === 'on' ? 'control_plan.on' : state === 'off' ? 'control_plan.off' : 'control_plan.unknown';
  return `<article class="control-plan-device control-plan-device--mode control-plan-device--${state}">
    <header><h3>${t(titleKey)}</h3><span class="control-plan-mode" data-state="${state}">${t(labelKey)}</span></header>
    <p class="meta">${reader?.name || 'tng'} · ${reader?.last_success ? dateTime(reader.last_success) : t('control_plan.no_observation')}</p>`;
}

function renderControlPlanDailyEnergy(goodwe, sdg, summary) {
  const values = sdg?.values || sdg || {};
  const currentDaily = {
    production: values.e_day_kwh ?? values.e_day,
    load: values.e_load_day_kwh ?? values.e_load_day,
    import: values.e_import_day_kwh ?? values.e_day_imp,
    export: values.e_export_day_kwh ?? values.e_day_exp,
  };
  const historicalDaily = {
    production: summary?.pv_kwh,
    load: summary?.house_kwh,
    import: summary?.grid_import_kwh,
    export: summary?.grid_export_kwh,
  };
  const hasCurrentDaily = Object.values(currentDaily).some((value) => value !== null && value !== undefined);
  const daily = hasCurrentDaily ? currentDaily : {
    production: historicalDaily.production ?? goodwe.e_day_kwh,
    load: historicalDaily.load ?? goodwe.e_load_day_kwh,
    import: historicalDaily.import ?? goodwe.e_import_day_kwh,
    export: historicalDaily.export ?? goodwe.e_export_day_kwh,
  };
  const source = hasCurrentDaily ? (Object.keys(values).length ? 'SDG' : 'GoodWe') : t('control_plan.historical');
  const metric = (labelKey, value, tone) => `<div class="control-plan-energy-metric" data-tone="${tone}"><span>${t(labelKey)}</span><strong>${controlPlanValue(value, (item) => `${num(item, 1)} ${t('unit.kwh')}`)}</strong></div>`;
  const hasData = Object.values(daily).some((value) => value !== null && value !== undefined);
  return `<article class="control-plan-daily-energy"><header><h3>${t('control_plan.daily_energy')}</h3><span class="meta">${t('control_plan.source_label')}: ${source}</span></header>
    <div class="control-plan-energy-grid">${hasData ? [
      metric('control_plan.production', daily.production, 'production'),
      metric('control_plan.house_load', daily.load, 'load'),
      metric('entity.grid_import', daily.import, 'import'),
      metric('entity.grid_export', daily.export, 'export'),
    ].join('') : `<p class="notice">${t('control_plan.no_daily_energy')}</p>`}</div></article>`;
}

function renderControlPlanOutlook(prices, prediction) {
  const days = [];
  const priceDays = [prices?.today || null, prices?.tomorrow || null];
  priceDays.forEach((day, index) => {
    const periods = (day?.periods || []).filter((period) => period.price_total_czk_kwh != null || period.price_czk_kwh != null);
    const pricesForDay = periods.map((period) => period.price_total_czk_kwh ?? period.price_czk_kwh);
    const min = pricesForDay.length ? Math.min(...pricesForDay) : null;
    const max = pricesForDay.length ? Math.max(...pricesForDay) : null;
    days.push(`<article class="control-plan-outlook-day"><h3>${t(index ? 'control_plan.tomorrow' : 'control_plan.today')}</h3>
      <p>${periods.length ? `${t('control_plan.price_range')}: ${num(min, 2)}–${num(max, 2)} ${t('unit.czk_kwh')}` : t('control_plan.no_price_data')}</p>
      <p class="meta">${day?.date ? escapeHtml(day.date) : t('control_plan.no_observation')}</p></article>`);
  });
  (prediction?.days || []).slice(0, 2).forEach((day) => {
    days.push(`<article class="control-plan-outlook-day"><h3>${escapeHtml(day.date || t('control_plan.tomorrow'))}</h3>
      <p>${t('entity.pv')}: ${controlPlanValue(day.pv_kwh, (value) => `${num(value, 1)} ${t('unit.kwh')}`)}</p>
      <p>${t('entity.house')}: ${controlPlanValue(day.consumption_kwh, (value) => `${num(value, 1)} ${t('unit.kwh')}`)}</p>
      <p class="meta">${day.confidence ? `${t('control_plan.confidence')}: ${escapeHtml(day.confidence)}` : t('control_plan.no_forecast_data')}</p></article>`);
  });
  return days.length ? days.join('') : `<p class="notice">${t('control_plan.no_outlook')}</p>`;
}

function renderControlPlanActivity(decisions) {
  const today = new Date().toLocaleDateString('en-CA');
  const rows = (decisions || []).filter((decision) => {
    const stamp = new Date(decision.timestamp);
    return !Number.isNaN(stamp.getTime()) && stamp.toLocaleDateString('en-CA') === today;
  }).slice(-12).reverse();
  if (!rows.length) return `<p class="notice">${t('control_plan.no_activity')}</p>`;
  return `<div class="table-wrap"><table class="data control-plan-activity"><thead><tr>
    <th>${t('control_plan.time')}</th><th>${t('control_plan.action')}</th><th>${t('control_plan.result')}</th><th>${t('control_plan.reason')}</th>
  </tr></thead><tbody>${rows.map((decision) => `<tr>
    <td>${dateTime(decision.timestamp)}</td><td>${escapeHtml(decision.action || decision.rule || '–')}</td>
    <td>${decision.applied ? controlPlanPill('ok', 'control_plan.applied') : controlPlanPill('neutral', 'control_plan.not_applied')}</td>
    <td>${translatedText(decision.reason_key, decision.reason_params)}</td>
  </tr>`).join('')}</tbody></table></div>`;
}

export async function controlPlan(view, { api }) {
  const [current, statusPayload, decisionsPayload, prices, prediction, appliances] = await Promise.all([
    api.current().catch(() => ({})), api.status().catch(() => ({})), api.decisions(2).catch(() => ({ decisions: [] })),
    api.prices().catch(() => ({})), api.prediction().catch(() => ({})), api.appliances(1).catch(() => ({ cycles: [] })),
  ]);
  const summaryPayload = await api.summaries(1).catch(() => ({ days: [] }));
  const sources = current.sources || {};
  const readers = statusPayload.readers || {};
  const controller = statusPayload.controller || decisionsPayload.state || {};
  const goodwe = sources.goodwe || {};
  const tng = sources.tng || {};
  const sdg = sources.sdg || sources.sdg_history || {};
  const shelly = Object.entries(sources).filter(([name]) => name.startsWith('shelly'));
  const writer = statusPayload.goodwe_writer_diagnostics || {};
  const tngReader = readers.tng;
  const goodweReader = readers.goodwe;
  const cards = [
    `${renderControlPlanMode('entity.heating', tng.heating_on, tngReader)}<dl class="control-plan-metrics">${deviceMetric('entity.outside', controlPlanValue(tng.outside_temperature, (value) => `${num(value, 1)} ${t('unit.celsius')}`))}${deviceMetric('entity.room', controlPlanValue(tng.room_temperature, (value) => `${num(value, 1)} ${t('unit.celsius')}`))}</dl></article>`,
    `${renderControlPlanMode('entity.dhw', tng.boiler_on, tngReader)}<dl class="control-plan-metrics">${deviceMetric('control_plan.current', controlPlanValue(tng.boiler_temperature, (value) => `${num(value, 1)} ${t('unit.celsius')}`))}${deviceMetric('control_plan.setpoint', controlPlanValue(tng.boiler_set_temperature, (value) => `${num(value, 1)} ${t('unit.celsius')}`))}</dl></article>`,
    renderControlPlanDevice('entity.pv', 'goodwe', `${deviceMetric('entity.pv', controlPlanValue(goodwe.pv_w, (value) => power(value).value + ' ' + power(value).unit))}${deviceMetric('entity.house', controlPlanValue(goodwe.house_w, (value) => power(value).value + ' ' + power(value).unit))}${deviceMetric('entity.battery_soc', controlPlanValue(goodwe.battery_soc, (value) => `${num(value, 0)} ${t('unit.percent')}`))}`, goodweReader),
    renderControlPlanDevice('entity.grid', 'goodwe', `${deviceMetric('entity.grid_import', controlPlanValue(goodwe.grid_import_w, (value) => power(value).value + ' ' + power(value).unit))}${deviceMetric('entity.grid_export', controlPlanValue(goodwe.grid_export_w, (value) => power(value).value + ' ' + power(value).unit))}${deviceMetric('entity.battery', controlPlanValue(goodwe.battery_charge_w ?? goodwe.battery_discharge_w, (value) => power(value).value + ' ' + power(value).unit))}`, goodweReader),
  ];
  const shellyCards = shelly.length ? shelly.map(([name, values]) => renderControlPlanDevice('entity.appliances', name, deviceMetric('entity.appliances', controlPlanValue(values.power_w, (value) => power(value).value + ' ' + power(value).unit)), readers[name])).join('') : `<p class="notice">${t('control_plan.no_appliances')}</p>`;
  view.innerHTML = `<div class="control-plan-page">
    <header class="control-plan-header"><div><span class="section-tab">${t('control_plan.title')}</span><p class="meta">${t('control_plan.subtitle')}</p></div><span id="control-plan-updated" class="meta">${t('app.updated', { time: time(new Date()) })}</span></header>
    <section class="panel control-plan-status" aria-labelledby="control-plan-status-title"><h2 id="control-plan-status-title">${t('control_plan.automation')}</h2><div class="control-plan-status-grid">
      <article><h3>${t('control_plan.planner')}</h3>${controlPlanPill('neutral', 'control_plan.not_exposed')}<p class="meta">${t('control_plan.planner_note')}</p></article>
      <article><h3>${t('settings.controller')}</h3>${controller.enabled ? controlPlanPill('ok', 'status.controller_running') : controlPlanPill('neutral', 'status.controller_disabled')}${controller.safe_mode ? controlPlanPill('warning', 'status.safe_mode') : ''}<p class="meta">${controller.last_run ? `${t('control_plan.last_run')}: ${dateTime(controller.last_run)}` : t('control_plan.no_run')}</p></article>
      <article><h3>${t('control_plan.writers')}</h3>${writer.enabled ? controlPlanPill('warning', 'control_plan.available_disabled') : controlPlanPill('neutral', 'status.write_disabled')}<p class="meta">${t('control_plan.read_only')}</p></article>
    </div></section>
    <section class="panel control-plan-devices" aria-labelledby="control-plan-devices-title"><h2 id="control-plan-devices-title">${t('control_plan.devices')}</h2><div class="control-plan-device-grid">${cards.join('')}${shellyCards}</div></section>
    <section class="panel control-plan-lower"><div><h2>${t('control_plan.today_activity')}</h2>${renderControlPlanActivity(decisionsPayload.decisions)}</div><div><h2>${t('control_plan.outlook')}</h2><div class="control-plan-outlook">${renderControlPlanOutlook(prices, prediction)}</div><p class="meta">${t('control_plan.appliance_cycles')}: ${num((appliances.cycles || []).length, 0)}</p></div></section>
    <section class="panel control-plan-daily-panel">${renderControlPlanDailyEnergy(goodwe, sdg, summaryPayload.days?.at(-1))}</section>
  </div>`;
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
            ${sources.map((source) => `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`).join('')}
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
      + days.slice().reverse().map((day) => `<option value="${escapeHtml(day)}">${escapeHtml(day)}</option>`).join('');
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

export async function finance(view, { api }) {
  const dashboard = await api.financeDashboard().catch(() => ({
    available: false, kpi: {}, monthly_net_costs: [], audit: { sources: {} },
  }));
  const kpi = dashboard.kpi || {};
  view.innerHTML = `
    <div>
      <span class="section-tab">${t('finance.title')}</span>
      <section class="panel">
        <div class="cards">
          ${card('finance.kpi.energy_costs_ytd', `<p class="value">${num(kpi.energy_costs_ytd ?? 0, 2)}</p>`)}
          ${card('finance.kpi.energy_income_ytd', `<p class="value">${num(kpi.energy_income_ytd ?? 0, 2)}</p>`)}
          ${card('finance.kpi.net_costs_ytd', `<p class="value">${num(kpi.net_costs_ytd ?? 0, 2)}</p>`)}
          ${card('finance.kpi.net_investment', `<p class="value">${num(kpi.net_investment ?? 0, 2)}</p>`)}
          ${card('finance.kpi.opportunity_cost', `<p class="value">${num(kpi.opportunity_cost ?? 0, 2)}</p>`)}
          ${card('finance.kpi.npv', `<p class="value">${kpi.npv == null ? '–' : num(kpi.npv, 2)}</p>`)}
        </div>
        <p class="meta">${t('finance.audit.records', { count: dashboard.audit?.sources?.finance_transactions ?? 0 })}</p>
      </section>
    </div>`;
}

export async function financeManual(view, { api }) {
  const payload = await api.financeManual({ limit: 100 }).catch(() => ({ items: [], count: 0 }));
  const rows = payload.items || [];
  view.innerHTML = `
    <div>
      <span class="section-tab">${t('finance_manual.title')}</span>
      <section class="panel">
        <p class="meta">${t('finance_manual.count', { count: payload.count ?? 0 })}</p>
        ${rows.length ? '<div id=\"finance-manual-table\"></div>' : `<p class="notice">${t('app.no_data')}</p>`}
      </section>
    </div>`;
  if (rows.length) {
    renderTable(view.querySelector('#finance-manual-table'), rows, [
      'timestamp', 'transaction_date', 'transaction_type', 'amount_total', 'currency', 'notes',
    ]);
  }
}

export const pages = {
  overview,
  history,
  prediction,
  flow,
  finance,
  'finance/manual': financeManual,
  'control-plan': controlPlan,
  status,
  logs: logsPage,
  settings,
};
export const helpers = { duration, availableLanguages, currentLanguage };
