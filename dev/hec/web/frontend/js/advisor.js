// Rozhodovací vrstva pro domovskou stránku. Pracuje výhradně s daty, která už
// rozhraní dostává z API: cenou, hodinovou předpovědí, predikcí a aktuálním
// stavem. Neovládá spotřebiče ani nedopočítává neznámé hodnoty.

import { num, power, t, time } from './i18n.js';
import { applianceIcon, weatherIcon } from './icons.js';

const dateKey = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const values = (items, key) => items.map((item) => Number(item?.[key])).filter(Number.isFinite);
const average = (items, key) => {
  const list = values(items, key);
  return list.length ? list.reduce((sum, value) => sum + value, 0) / list.length : null;
};
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
    avoid: high === null ? null : rangeFor(priceDay.periods, (period) => Number(period.price_total_czk_kwh) >= high),
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

function applianceCard(type, key, advice) {
  const window = advice.best;
  return `<article class="appliance-advice ${window ? 'is-recommended' : ''}">
    <div class="appliance-advice__icon">${applianceIcon(type)}</div>
    <div><p>${t(key)}</p><strong>${window ? t('advisor.appliance_window', { window }) : t('advisor.window_unavailable')}</strong>
    <small>${t('advisor.recommendation_only')}</small></div>
  </article>`;
}

export function renderToday(view, { current, weather, prices, prediction }) {
  const sources = current.sources || {};
  const goodwe = sources.goodwe || {};
  const tng = sources.tng || {};
  const ote = sources.ote || {};
  const advice = bestAdvice(prediction, prices);
  const headline = adviceCopy(advice, goodwe);
  // Today je živý plán aktuálního dne. Predikce začíná záměrně až D+1,
  // ale nesmí proto přepnout dnešní ceny a rytmus na zítřek.
  const todayDate = dateKey(new Date());
  const timeline = timelineFor(todayDate, weather, prices);
  const pv = power(goodwe.pv_w);
  const house = power(goodwe.house_w);
  const grid = power(Number(goodwe.grid_import_w) || Number(goodwe.grid_export_w));
  const condition = weather?.current?.condition || 'unknown';
  const solarPeak = Math.max(...timeline.map((slot) => Number(slot.solar) || 0));
  const lastMeasurement = current?.last_measurement_at ? time(new Date(current.last_measurement_at)) : '–';

  view.innerHTML = `<div class="advisor-dashboard">
    <section class="advisor-brief" aria-labelledby="advisor-title">
      <div class="advisor-brief__weather">${weatherIcon(condition, weather?.current?.is_day !== false, 'advisor-brief__weather-icon')}<div><strong>${num(weather?.current?.temp_c, 0)}°</strong><span>${t(`weather.${condition}`)}</span></div></div>
      <div class="advisor-brief__main"><p>${t('advisor.best_action')}</p><h2 id="advisor-title">${t(headline.key, headline.params)}</h2><span>${advice.best ? t('advisor.based_on', { date: advice.day.date }) : t('advisor.awaiting_forecast')}</span><a href="#/prediction">${t('advisor.open_forecast')} <b aria-hidden="true">→</b></a></div>
      <div class="advisor-brief__states">
        <article class="brief-state brief-state--now"><span>${t('advisor.now')}</span><strong>${t(`advisor.grid_${energyState(goodwe)}`)}</strong><small>${t('advisor.now_state_reason')}</small></article>
        <article class="brief-state brief-state--avoid"><span>${t('advisor.avoid')}</span><strong>${advice.avoid || '–'}</strong><small>${t('advisor.avoid_window_short')}</small></article>
        <article class="brief-state brief-state--solar"><span>${t('advisor.solar_outlook')}</span><strong>${advice.day ? `${num(advice.day.pv_kwh_low, 0)}–${num(advice.day.pv_kwh_high, 0)} ${t('unit.kwh')}` : '–'}</strong><small>${advice.day ? t('advisor.solar_peak', { value: num(solarPeak, 0) }) : t('advisor.awaiting_forecast')}</small></article>
      </div>
    </section>

    <section class="advisor-kpis" aria-label="${t('advisor.live_title')}">
      <article><span>${t('entity.pv')}</span><strong>${pv.value}<small>${pv.unit}</small></strong><em class="kpi-pv">↗</em></article>
      <article><span>${t('entity.house')}</span><strong>${house.value}<small>${house.unit}</small></strong><em class="kpi-house">⌂</em></article>
      <article><span>${t('entity.battery')}</span><strong>${num(goodwe.battery_soc, 0)}<small>%</small></strong><em class="kpi-battery">▣</em></article>
      <article><span>${t(`advisor.grid_${energyState(goodwe)}`)}</span><strong>${grid.value}<small>${grid.unit}</small></strong><em class="kpi-grid">⌁</em></article>
      <article><span>${t('entity.price')}</span><strong>${num(ote.price_total_czk_kwh ?? ote.price_czk_kwh, 2)}<small>${t('unit.czk_kwh')}</small></strong><em class="kpi-price">◆</em></article>
      <article><span>${t('overview.last_data_update')}</span><strong>${lastMeasurement}</strong><em class="kpi-time">◔</em></article>
      <article><span>${t('entity.heatpump')}</span><strong>${num(tng.boiler_temperature, 0)}<small>°C</small></strong><em class="kpi-heat">♨</em></article>
    </section>

    <section class="rhythm-panel" aria-labelledby="timeline-title">
      <header><div><p>${t('advisor.section_kicker')}</p><h2 id="timeline-title">${t('advisor.timeline_title')}</h2></div><div class="rhythm-legend"><span class="timeline-legend--best">${t('advisor.best')}</span><span class="timeline-legend--ok">${t('advisor.ok')}</span><span class="timeline-legend--avoid">${t('advisor.avoid')}</span></div></header>
      <div class="energy-timeline energy-timeline--dense" role="list" aria-label="${t('advisor.timeline_title')}">
        ${timeline.map((slot) => `<article class="timeline-slot timeline-slot--${slot.level}" role="listitem"><time>${String(slot.start).padStart(2, '0')}:00</time><div class="timeline-slot__weather">${slot.hour ? weatherIcon(slot.hour.condition, daylight(slot.hour) > 0, 'timeline-weather') : ''}<span>${slot.hour ? `${num(slot.hour.temp_c, 0)}°` : '–'}</span></div><span class="timeline-slot__state">${t(`advisor.${slot.level}`)}</span><strong class="timeline-slot__price">${slot.price === null ? '–' : `${num(slot.price, 2)} ${t('unit.czk_kwh')}`}</strong><small class="timeline-slot__solar">${slot.solar === null ? '–' : `${num(slot.solar, 0)} W/m²`}</small></article>`).join('')}
      </div>
    </section>

    <section class="advisor-workspace">
      <article class="workspace-card appliance-workspace"><header><p>${t('advisor.appliances_title')}</p><span>${t('advisor.recommendations_badge')}</span></header><div class="compact-appliances">
        ${['washing_machine', 'dishwasher', 'dryer'].map((type) => `<div>${applianceIcon(type)}<span>${t(`entity.${type}`)}</span><strong>${advice.best || '–'}</strong><i>★</i></div>`).join('')}
        <div>${applianceIcon('heatpump')}<span>${t('entity.heatpump')}</span><strong>${current.status?.controller?.enabled ? t('advisor.controller_active') : t('advisor.controller_observing')}</strong><i>•</i></div>
      </div></article>
      <article class="workspace-card next-window"><header><p>${t('advisor.next_window')}</p></header><div class="window-ring"><span>${t('advisor.best')}</span><strong>${advice.best || '–'}</strong><small>${t('advisor.window_reason_short')}</small></div><p>${t('advisor.window_value', { value: advice.day ? `${num(advice.day.pv_kwh_low, 0)}–${num(advice.day.pv_kwh_high, 0)} ${t('unit.kwh')}` : '–' })}</p></article>
      <article class="workspace-card outlook-workspace"><header><p>${t('advisor.outlook_title')}</p><span>${t('advisor.outlook_subtitle')}</span></header>${renderOutlookChart(timeline)}</article>
    </section>
  </div>`;
}

function linePath(values, width, height, pad) {
  const max = Math.max(...values, 1);
  return values.map((value, index) => {
    const x = pad + index * ((width - pad * 2) / Math.max(values.length - 1, 1));
    const y = height - pad - (Math.max(0, value) / max) * (height - pad * 2);
    return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
}

function renderOutlookChart(timeline) {
  const solar = timeline.map((slot) => Number(slot.solar) || 0);
  const price = timeline.map((slot) => Number(slot.price) || 0);
  const width = 500; const height = 166; const pad = 20;
  return `<div class="outlook-chart"><div class="outlook-chart__legend"><span class="solar">${t('advisor.solar_curve')}</span><span class="price">${t('advisor.price_curve')}</span></div><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${t('advisor.outlook_title')}"><path class="outlook-grid" d="M${pad} 40H${width - pad}M${pad} 82H${width - pad}M${pad} 124H${width - pad}"/><path class="outlook-solar" d="${linePath(solar, width, height, pad)}"/><path class="outlook-price" d="${linePath(price, width, height, pad)}"/>${timeline.map((slot, index) => `<text x="${pad + index * ((width - pad * 2) / 7)}" y="157" text-anchor="middle">${String(slot.start).padStart(2, '0')}</text>`).join('')}</svg></div>`;
}

export function renderForecastStory(view, { prediction, weather, prices }) {
  const days = prediction?.days || [];
  view.innerHTML = `<section class="forecast-hero"><div><p>${t('forecast.eyebrow')}</p><h2>${t('forecast.title')}</h2><span>${t('forecast.subtitle')}</span></div><div class="forecast-hero__metric"><span>${t('forecast.best_window')}</span><strong>${days.find((day) => day.best_appliance_window)?.best_appliance_window || '–'}</strong></div></section>
    <section class="forecast-grid" id="forecast-grid"></section>`;
  const grid = view.querySelector('#forecast-grid');
  if (!days.length) { grid.innerHTML = `<p class="notice">${t('prediction.not_enough_data')}</p>`; return; }
  grid.innerHTML = days.map((day) => {
    const weatherDay = (weather?.forecast_daily || []).find((item) => item.date === day.date) || {};
    const priceDay = dayFor(day.date, prices);
    const periods = values(priceDay?.periods || [], 'price_total_czk_kwh');
    return `<article class="forecast-day-card">
      <header><div><p>${day.date}</p><h3>${weatherIcon(weatherDay.condition || 'unknown', true, 'forecast-weather-icon')} ${t(`weather.${weatherDay.condition || 'unknown'}`)}</h3></div><span class="confidence confidence--${day.confidence || 'low'}">${t('forecast.confidence', { value: t(`prediction.confidence_${day.confidence || 'low'}`) })}</span></header>
      <div class="forecast-day-card__main"><span>${t('forecast.pv_expected')}</span><strong>${num(day.pv_kwh_low, 0)}–${num(day.pv_kwh_high, 0)} <small>${t('unit.kwh')}</small></strong><p>${t('forecast.irradiation', { value: num(day.irradiation_kwh_m2, 1) })}</p></div>
      <dl><div><dt>${t('forecast.consumption')}</dt><dd>${num(day.consumption_kwh, 1)} ${t('unit.kwh')}</dd></div><div><dt>${t('forecast.battery_floor')}</dt><dd>${num(day.battery_soc_min_pct, 0)} %</dd></div><div><dt>${t('forecast.price_range')}</dt><dd>${periods.length ? `${num(Math.min(...periods), 2)}–${num(Math.max(...periods), 2)} ${t('unit.czk_kwh')}` : '–'}</dd></div></dl>
      <footer>${day.best_appliance_window ? `<span>${t('forecast.recommendation')}</span><strong>${t('advisor.appliance_window', { window: day.best_appliance_window })}</strong>` : `<span>${t('advisor.window_unavailable')}</span>`}</footer>
    </article>`;
  }).join('');
}
