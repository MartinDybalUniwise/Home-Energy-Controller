// Rozhodovací vrstva pro domovskou stránku. Pracuje výhradně s daty, která už
// rozhraní dostává z API: cenou, hodinovou předpovědí, predikcí a aktuálním
// stavem. Neovládá spotřebiče ani nedopočítává neznámé hodnoty.

import { dateTime, num, power, t, time, weekday } from './i18n.js';
import { applianceIcon, weatherIcon } from './icons.js';

const dateKey = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const values = (items, key) => items.map((item) => Number(item?.[key])).filter(Number.isFinite);
const percentile = (list, ratio) => {
  if (!list.length) return null;
  const sorted = [...list].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * ratio))];
};

function dayFor(date, prices) {
  return [prices?.today, prices?.tomorrow].find((day) => day?.date === date) || null;
}

function priceAt(stamp, priceDay) {
  if (!priceDay?.periods?.length) return null;
  const clock = `${String(stamp.getHours()).padStart(2, '0')}:${String(stamp.getMinutes()).padStart(2, '0')}`;
  return priceDay.periods.find((period) => period.start <= clock && period.end > clock) || null;
}

function rangeFor(periods, predicate) {
  const hits = periods.filter(predicate);
  if (!hits.length) return null;
  const longest = [];
  let current = [];
  for (const period of hits) {
    if (current.length && current[current.length - 1].end !== period.start) current = [];
    current.push(period);
    if (current.length > longest.length) longest.splice(0, longest.length, ...current);
  }
  return longest.length ? `${longest[0].start}–${longest[longest.length - 1].end}` : null;
}

function daylight(hour) {
  return Number(hour?.ghi_wm2) || 0;
}

function suitability(hour, period, thresholds) {
  if (!hour || !period) return 'unknown';
  const price = Number(period.price_total_czk_kwh);
  const sun = daylight(hour);
  if (sun >= 300 && price <= thresholds.priceLow) return 'best';
  if (sun >= 140 || price <= thresholds.priceLow) return 'ok';
  if (sun < 80 && price >= thresholds.priceHigh) return 'avoid';
  return 'neutral';
}

function timelineFor(date, weather, prices) {
  const hourly = (weather?.forecast_hourly || []).filter((hour) => dateKey(hour.time) === date);
  const priceDay = dayFor(date, prices);
  const priceValues = values(priceDay?.periods || [], 'price_total_czk_kwh');
  const thresholds = { priceLow: percentile(priceValues, .3), priceHigh: percentile(priceValues, .75) };
  const starts = [0, 3, 6, 9, 12, 15, 18, 21];
  return starts.map((start) => {
    const rows = hourly.filter((hour) => new Date(hour.time).getHours() >= start && new Date(hour.time).getHours() < start + 3);
    const hour = rows[Math.floor(rows.length / 2)] || null;
    const stamp = hour ? new Date(hour.time) : new Date(`${date}T${String(start).padStart(2, '0')}:00`);
    const period = priceAt(stamp, priceDay);
    return {
      start,
      hour,
      price: period?.price_total_czk_kwh ?? null,
      solar: hour ? daylight(hour) : null,
      level: suitability(hour, period, thresholds),
    };
  });
}

function bestAdvice(prediction, prices) {
  const day = prediction?.days?.find((item) => item.best_appliance_window) || prediction?.days?.[0] || null;
  const priceDay = dayFor(day?.date, prices);
  const priceValues = values(priceDay?.periods || [], 'price_total_czk_kwh');
  const high = percentile(priceValues, .8);
  return {
    day,
    best: day?.best_appliance_window || null,
    avoid: high === null || !priceDay?.periods ? null : rangeFor(priceDay.periods, (period) => Number(period.price_total_czk_kwh) >= high),
  };
}

function energyState(goodwe) {
  if (Number(goodwe?.grid_export_w) > 20) return 'export';
  if (Number(goodwe?.grid_import_w) > 20) return 'import';
  return 'balanced';
}

function adviceCopy(advice, goodwe) {
  if (advice.best) return { key: 'advisor.hero_best', params: { window: advice.best } };
  if (energyState(goodwe) === 'export') return { key: 'advisor.hero_export' };
  return { key: 'advisor.hero_wait' };
}

function translatedText(key, params, fallback = '') {
  if (!key) return fallback;
  const text = t(key, params);
  return text === key ? fallback : text;
}

function dayLabel(value) {
  const stamp = new Date(`${value}T12:00:00`);
  if (Number.isNaN(stamp.getTime())) return value || '–';
  return `${weekday(stamp)}, ${time(stamp, { day: '2-digit', month: '2-digit' })}`;
}

function formatRange(low, high, digits, unitKey) {
  const a = Number(low);
  const b = Number(high);
  if (Number.isFinite(a) && Number.isFinite(b)) return `${num(a, digits)}–${num(b, digits)} ${t(unitKey)}`;
  if (Number.isFinite(a)) return `${num(a, digits)} ${t(unitKey)}`;
  if (Number.isFinite(b)) return `${num(b, digits)} ${t(unitKey)}`;
  return '–';
}

function formatPrice(value) {
  return Number.isFinite(Number(value)) ? `${num(value, 2)} ${t('unit.czk_kwh')}` : '–';
}

function formatCurrency(value) {
  return Number.isFinite(Number(value)) ? `${num(value, 0)} ${t('unit.czk')}` : '–';
}

function controllerSummary(controller) {
  if (controller?.safe_mode) {
    return translatedText(controller.safe_mode_reason?.reason_key, controller.safe_mode_reason?.reason_params, t('status.safe_mode_active'));
  }
  return controller?.enabled ? t('status.controller_running') : t('status.controller_disabled');
}

function latestDecisionSummary(decision) {
  if (!decision) return t('overview.no_decision');
  return translatedText(decision.reason_key, decision.reason_params, `${decision.rule} → ${decision.action}`);
}

function recommendationRow(type, window) {
  return `<div class="story-appliance-row${window ? ' is-recommended' : ''}">
    <div class="story-appliance-row__icon">${applianceIcon(type)}</div>
    <span>${t(`entity.${type}`)}</span>
    <strong>${window || t('advisor.window_unavailable')}</strong>
  </div>`;
}

export function renderToday(view, { current, weather, prices, prediction }) {
  const sources = current.sources || {};
  const goodwe = sources.goodwe || {};
  const tng = sources.tng || {};
  const ote = sources.ote || {};
  const controller = current?.status?.controller || {};
  const staleSources = current?.status?.stale_sources || [];
  const advice = bestAdvice(prediction, prices);
  const headline = adviceCopy(advice, goodwe);
  const todayDate = dateKey(new Date());
  const timeline = timelineFor(todayDate, weather, prices);
  const pv = power(goodwe.pv_w);
  const house = power(goodwe.house_w);
  const priceNow = ote.price_total_czk_kwh ?? ote.price_czk_kwh;
  const condition = weather?.current?.condition || 'unknown';
  const solarPeak = Math.max(...timeline.map((slot) => Number(slot.solar) || 0), 0);
  const lastMeasurement = current?.last_measurement_at ? dateTime(current.last_measurement_at) : '–';
  const decision = controller.last_decision || null;
  const heroSummary = advice.best ? t('advisor.based_on', { date: dayLabel(advice.day?.date) }) : t('advisor.awaiting_forecast');
  const liveBadges = [
    controller.enabled
      ? `<span class="pill" data-level="ok">${t('status.controller_running')}</span>`
      : `<span class="pill" data-level="neutral">${t('status.controller_disabled')}</span>`,
    controller.safe_mode ? `<span class="pill" data-level="warning">${t('status.safe_mode')}</span>` : '',
    controller.write_enabled === false ? `<span class="pill" data-level="neutral">${t('status.write_disabled')}</span>` : '',
    staleSources.length ? `<span class="pill" data-level="critical">${t('status.stale')}: ${staleSources.join(', ')}</span>` : '',
  ].filter(Boolean).join('');

  view.innerHTML = `<div class="story-page story-page--today">
    <section class="story-hero story-hero--today" aria-labelledby="advisor-title">
      <div class="story-hero__main">
        <p class="story-hero__eyebrow">${t('advisor.eyebrow')}</p>
        <h2 id="advisor-title">${t(headline.key, headline.params)}</h2>
        <p class="story-hero__summary">${heroSummary}</p>
        <div class="story-hero__actions">
          <a class="story-link" href="#/prediction">${t('advisor.open_forecast')} <b aria-hidden="true">→</b></a>
          <a class="story-link story-link--secondary" href="#/flow">${t('advisor.open_flow')} <b aria-hidden="true">→</b></a>
        </div>
      </div>
      <div class="story-hero__aside">
        <div class="story-weather">
          ${weatherIcon(condition, weather?.current?.is_day !== false, 'story-weather__icon')}
          <div>
            <strong>${num(weather?.current?.temp_c, 0)}<small>${t('unit.celsius')}</small></strong>
            <span>${t(`weather.${condition}`)}</span>
          </div>
        </div>
        <dl class="story-hero__stats">
          <div><dt>${t('entity.pv')}</dt><dd>${pv.value}<small>${pv.unit}</small></dd></div>
          <div><dt>${t('entity.house')}</dt><dd>${house.value}<small>${house.unit}</small></dd></div>
          <div><dt>${t('entity.battery_soc')}</dt><dd>${num(goodwe.battery_soc, 0)}<small>${t('unit.percent')}</small></dd></div>
          <div><dt>${t('entity.price')}</dt><dd>${formatPrice(priceNow)}</dd></div>
        </dl>
      </div>
    </section>

    <section class="story-card-grid story-card-grid--three" aria-label="${t('advisor.plan_title')}">
      <article class="story-card story-card--accent-good">
        <p class="story-card__eyebrow">${t('advisor.best')}</p>
        <strong class="story-card__value">${advice.best || '–'}</strong>
        <p class="story-card__meta">${advice.best ? t('advisor.best_window_reason') : t('advisor.no_window_reason')}</p>
      </article>
      <article class="story-card story-card--accent-warm">
        <p class="story-card__eyebrow">${t('advisor.avoid')}</p>
        <strong class="story-card__value">${advice.avoid || '–'}</strong>
        <p class="story-card__meta">${advice.avoid ? t('advisor.avoid_window_reason') : t('advisor.no_avoid_reason')}</p>
      </article>
      <article class="story-card story-card--accent-solar">
        <p class="story-card__eyebrow">${t('advisor.solar_outlook')}</p>
        <strong class="story-card__value">${advice.day ? formatRange(advice.day.pv_kwh_low, advice.day.pv_kwh_high, 0, 'unit.kwh') : '–'}</strong>
        <p class="story-card__meta">${advice.day ? t('advisor.solar_peak', { value: num(solarPeak, 0) }) : t('advisor.awaiting_forecast')}</p>
      </article>
    </section>

    <section class="story-surface story-surface--timeline" aria-labelledby="timeline-title">
      <header class="story-surface__header">
        <div>
          <p>${t('advisor.section_kicker')}</p>
          <h3 id="timeline-title">${t('advisor.timeline_title')}</h3>
        </div>
        <div class="rhythm-legend">
          <span class="timeline-legend--best">${t('advisor.best')}</span>
          <span class="timeline-legend--ok">${t('advisor.ok')}</span>
          <span class="timeline-legend--avoid">${t('advisor.avoid')}</span>
        </div>
      </header>
      <div class="energy-timeline energy-timeline--dense" role="list" aria-label="${t('advisor.timeline_title')}">
        ${timeline.map((slot) => `<article class="timeline-slot timeline-slot--${slot.level}" role="listitem"><time>${String(slot.start).padStart(2, '0')}:00</time><div class="timeline-slot__weather">${slot.hour ? weatherIcon(slot.hour.condition, daylight(slot.hour) > 0, 'timeline-weather') : ''}<span>${slot.hour ? `${num(slot.hour.temp_c, 0)}${t('unit.celsius')}` : '–'}</span></div><span class="timeline-slot__state">${t(`advisor.${slot.level}`)}</span><strong class="timeline-slot__price">${formatPrice(slot.price)}</strong><small class="timeline-slot__solar">${slot.solar === null ? '–' : `${num(slot.solar, 0)} ${t('unit.wm2')}`}</small></article>`).join('')}
      </div>
      <p class="timeline-note">${t('advisor.timeline_note')}</p>
    </section>

    <section class="story-card-grid story-card-grid--support">
      <article class="story-card story-card--soft">
        <div class="story-card__header-row">
          <p class="story-card__eyebrow">${t('advisor.live_title')}</p>
        </div>
        <div class="story-card__status">${liveBadges}</div>
        <div class="story-data-rows">
          <div class="story-data-row"><span>${t('advisor.now')}</span><strong>${t(`advisor.grid_${energyState(goodwe)}`)}</strong></div>
          <div class="story-data-row"><span>${t('overview.last_data_update')}</span><strong>${lastMeasurement}</strong></div>
          <div class="story-data-row"><span>${t('settings.controller')}</span><strong>${controllerSummary(controller)}</strong></div>
          <div class="story-data-row"><span>${t('entity.heatpump')}</span><strong>${Number.isFinite(Number(tng.boiler_temperature)) ? t('advisor.dhw_temperature', { value: num(tng.boiler_temperature, 0) }) : t('advisor.tng_no_data')}</strong></div>
        </div>
      </article>
      <article class="story-card story-card--soft">
        <p class="story-card__eyebrow">${t('overview.last_decision')}</p>
        <strong class="story-card__value story-card__value--copy">${latestDecisionSummary(decision)}</strong>
        <p class="story-card__meta">${decision?.timestamp ? dateTime(decision.timestamp) : '–'}</p>
      </article>
      <article class="story-card story-card--soft">
        <div class="story-card__header-row">
          <p class="story-card__eyebrow">${t('advisor.appliances_title')}</p>
          <span class="story-card__hint">${t('advisor.recommendations_badge')}</span>
        </div>
        <div class="story-appliance-list">
          ${['washing_machine', 'dishwasher', 'dryer'].map((type) => recommendationRow(type, advice.best)).join('')}
        </div>
        <p class="story-card__meta">${t('advisor.recommendation_only')}</p>
      </article>
    </section>
  </div>`;
}

export function renderForecastStory(view, { prediction, weather, prices }) {
  const days = prediction?.days || [];
  const bestDay = days.find((day) => day.best_appliance_window) || days[0] || null;
  const dhwDay = days.find((day) => day.best_dhw_window) || days[0] || null;
  const costDay = days.find((day) => Number.isFinite(Number(day.cost_czk))) || days[0] || null;
  const accuracy = prediction?.accuracy || null;
  const hasWeatherDetails = Boolean(weather?.forecast_hourly?.length);

  view.innerHTML = `<div class="story-page story-page--forecast">
    <section class="story-hero story-hero--forecast">
      <div class="story-hero__main">
        <p class="story-hero__eyebrow">${t('forecast.eyebrow')}</p>
        <h2>${t('forecast.title')}</h2>
        <p class="story-hero__summary">${t('forecast.subtitle')}</p>
      </div>
      <div class="story-hero__aside">
        <dl class="story-hero__stats">
          <div><dt>${t('prediction.best_appliance_window')}</dt><dd>${bestDay?.best_appliance_window || '–'}</dd></div>
          <div><dt>${t('prediction.best_dhw_window')}</dt><dd>${dhwDay?.best_dhw_window || '–'}</dd></div>
          <div><dt>${t('prediction.confidence')}</dt><dd>${bestDay ? t(`prediction.confidence_${bestDay.confidence || 'low'}`) : '–'}</dd></div>
          <div><dt>${t('prediction.accuracy')}</dt><dd>${accuracy ? `${num(accuracy.pv_mape_pct, 1)}<small>${t('unit.percent')}</small>` : '–'}</dd></div>
        </dl>
      </div>
    </section>

    <section class="story-surface story-surface--forecast">
      <header class="story-surface__header">
        <div>
          <p>${t('nav.forecast')}</p>
          <h3>${t('forecast.title')}</h3>
        </div>
        <span class="story-surface__meta">${prediction?.generated_at ? t('app.updated', { time: dateTime(prediction.generated_at) }) : ''}</span>
      </header>
      <div class="forecast-grid" id="forecast-grid"></div>
    </section>

    <section class="story-card-grid story-card-grid--support">
      <article class="story-card story-card--accent-good">
        <p class="story-card__eyebrow">${t('forecast.recommendation')}</p>
        <strong class="story-card__value">${bestDay?.best_appliance_window || '–'}</strong>
        <div class="story-data-rows">
          <div class="story-data-row"><span>${t('prediction.best_appliance_window')}</span><strong>${bestDay?.best_appliance_window || '–'}</strong></div>
          <div class="story-data-row"><span>${t('prediction.best_dhw_window')}</span><strong>${dhwDay?.best_dhw_window || '–'}</strong></div>
          <div class="story-data-row"><span>${t('overview.last_data_update')}</span><strong>${prediction?.generated_at ? dateTime(prediction.generated_at) : '–'}</strong></div>
        </div>
      </article>
      <article class="story-card story-card--soft">
        <p class="story-card__eyebrow">${t('prediction.confidence')}</p>
        <strong class="story-card__value">${bestDay ? t(`prediction.confidence_${bestDay.confidence || 'low'}`) : '–'}</strong>
        <div class="story-data-rows">
          <div class="story-data-row"><span>${t('prediction.accuracy')}</span><strong>${accuracy ? `${num(accuracy.pv_mape_pct, 1)} ${t('unit.percent')}` : '–'}</strong></div>
          <div class="story-data-row"><span>${t('nav.forecast')}</span><strong>${days.length ? `${days.length}` : '–'}</strong></div>
        </div>
      </article>
      <article class="story-card story-card--soft">
        <p class="story-card__eyebrow">${t('prediction.expected_cost')}</p>
        <strong class="story-card__value">${formatCurrency(costDay?.cost_czk)}</strong>
        <div class="story-data-rows">
          <div class="story-data-row"><span>${t('prediction.expected_grid')}</span><strong>${Number.isFinite(Number(costDay?.grid_balance_kwh)) ? `${num(costDay.grid_balance_kwh, 1)} ${t('unit.kwh')}` : '–'}</strong></div>
          <div class="story-data-row"><span>${t('prediction.expected_consumption')}</span><strong>${Number.isFinite(Number(costDay?.consumption_kwh)) ? `${num(costDay.consumption_kwh, 1)} ${t('unit.kwh')}` : '–'}</strong></div>
        </div>
      </article>
    </section>

    ${hasWeatherDetails ? `<section class="story-surface story-surface--details"><header class="story-surface__header"><div><p>${t('nav.forecast')}</p><h3>${t('entity.weather')}</h3></div></header><div id="forecast-details"></div></section>` : ''}
  </div>`;

  const grid = view.querySelector('#forecast-grid');
  if (!days.length) {
    grid.innerHTML = `<p class="notice">${t('prediction.not_enough_data')}</p>`;
    return;
  }

  grid.innerHTML = days.map((day) => {
    const weatherDay = (weather?.forecast_daily || []).find((item) => item.date === day.date) || {};
    const priceDay = dayFor(day.date, prices);
    const periods = values(priceDay?.periods || [], 'price_total_czk_kwh');
    return `<article class="forecast-day-card">
      <header><div><p>${dayLabel(day.date)}</p><h3>${weatherIcon(weatherDay.condition || 'unknown', true, 'forecast-weather-icon')} ${t(`weather.${weatherDay.condition || 'unknown'}`)}</h3></div><span class="confidence confidence--${day.confidence || 'low'}">${t('forecast.confidence', { value: t(`prediction.confidence_${day.confidence || 'low'}`) })}</span></header>
      <div class="forecast-day-card__main"><span>${t('forecast.pv_expected')}</span><strong>${formatRange(day.pv_kwh_low, day.pv_kwh_high, 0, 'unit.kwh')}</strong><p>${t('forecast.irradiation', { value: num(day.irradiation_kwh_m2, 1) })}</p></div>
      <dl>
        <div><dt>${t('forecast.consumption')}</dt><dd>${Number.isFinite(Number(day.consumption_kwh)) ? `${num(day.consumption_kwh, 1)} ${t('unit.kwh')}` : '–'}</dd></div>
        <div><dt>${t('forecast.battery_floor')}</dt><dd>${Number.isFinite(Number(day.battery_soc_min_pct)) ? `${num(day.battery_soc_min_pct, 0)} ${t('unit.percent')}` : '–'}</dd></div>
        <div><dt>${t('forecast.price_range')}</dt><dd>${periods.length ? `${num(Math.min(...periods), 2)}–${num(Math.max(...periods), 2)} ${t('unit.czk_kwh')}` : '–'}</dd></div>
        <div><dt>${t('prediction.expected_cost')}</dt><dd>${formatCurrency(day.cost_czk)}</dd></div>
      </dl>
      <footer>${day.best_appliance_window ? `<span>${t('forecast.recommendation')}</span><strong>${t('advisor.appliance_window', { window: day.best_appliance_window })}</strong>` : `<span>${t('advisor.window_unavailable')}</span>`}</footer>
    </article>`;
  }).join('');
}
