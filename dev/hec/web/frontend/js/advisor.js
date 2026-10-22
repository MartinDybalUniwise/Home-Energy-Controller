import { source, finite, batteryText, heatpumpText, heatingPermission } from './telemetry.js';
// Rozhodovací vrstva pro domovskou stránku (Step 18 Touchscreen Redesign).
// Pracuje výhradně s daty, která rozhraní dostává z API: cenou, předpovědí počasí,
// predikcí výroby a okamžitým stavem.

import { dateTime, formatCurrency, num, power, t, time, weekday } from './i18n.js';
import { applianceIcon, weatherIcon } from './icons.js';

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

function translatedText(key, params, fallback = '') {
  const text = t(key, escapeParams(params));
  return text === key ? escapeHtml(fallback) : text;
}

const dateKey = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const values = (items, key) => items.map(item => finite(item?.[key])).filter(value => value !== null);
const dayLabel = (value) => {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value || '–';
  return `${weekday(date)}, ${time(date, { day: '2-digit', month: '2-digit' })}`;
};
const formatRange = (low, high, digits, unitKey) => {
  if (finite(low) === null || finite(high) === null) return '–';
  return `${num(low, digits)}–${num(high, digits)} ${t(unitKey)}`;
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
  return longest.length ? `${longest[0].start} – ${longest[longest.length - 1].end}` : null;
}

function daylight(hour) {
  return finite(hour?.ghi_wm2);
}

function suitability(hour, period, thresholds) {
  if (!hour || !period || finite(hour.ghi_wm2) === null || finite(period.price_total_czk_kwh) === null) return 'unknown';
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
  const thresholds = { priceLow: percentile(priceValues, 0.3) ?? 2.5, priceHigh: percentile(priceValues, 0.75) ?? 4.2 };
  const starts = [0, 3, 6, 9, 12, 15, 18, 21];
  return starts.map((start) => {
    const rows = hourly.filter((hour) => new Date(hour.time).getHours() >= start && new Date(hour.time).getHours() < start + 3);
    const hour = rows[Math.floor(rows.length / 2)] || null;
    const stamp = hour ? new Date(hour.time) : new Date(`${date}T${String(start).padStart(2, '0')}:00`);
    const period = priceAt(stamp, priceDay);
    const rainProb = num(hour?.precipitation_probability, 0);
    return {
      start,
      hour,
      price: finite(period?.price_total_czk_kwh),
      solar: hour ? daylight(hour) : null,
      rainProb,
      level: suitability(hour, period, thresholds),
    };
  });
}

function bestAdvice(prediction, prices) {
  const day = prediction?.days?.find((item) => item.best_appliance_window) || prediction?.days?.[0] || null;
  const priceDay = dayFor(day?.date, prices);
  const priceValues = values(priceDay?.periods || [], 'price_total_czk_kwh');
  const high = percentile(priceValues, 0.8);
  return {
    day,
    best: day?.best_appliance_window || t('advisor.window_unavailable'),
    avoid: high === null ? '–' : (rangeFor(priceDay.periods, (p) => Number(p.price_total_czk_kwh) >= high) || '–'),
  };
}

function energyState(goodwe) {
  if (Number(goodwe?.grid_export_w) > 20) return 'export';
  if (Number(goodwe?.grid_import_w) > 20) return 'import';
  return 'balanced';
}

function getGreeting(now) {
  const h = now.getHours();
  if (h < 10) return t('advisor.greeting_morning');
  if (h < 18) return t('advisor.greeting_day');
  return t('advisor.greeting_evening');
}

function formatDateFull(now) {
  const monthsCs = ['ledna', 'února', 'března', 'dubna', 'května', 'června', 'července', 'srpna', 'září', 'října', 'listopadu', 'prosince'];
  const monthsEn = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const isEn = document.documentElement.lang === 'en';
  const month = isEn ? monthsEn[now.getMonth()] : monthsCs[now.getMonth()];
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  return isEn ? `${month} ${now.getDate()}, ${now.getFullYear()} • ${timeStr}` : `${now.getDate()}. ${month} ${now.getFullYear()} • ${timeStr}`;
}

export function renderToday(view, { current, weather, prices, prediction }) {
  const goodwe = source(current, 'goodwe');
  const tng = source(current, 'tng');
  const controller = current?.status?.controller || {};
  const advice = bestAdvice(prediction, prices);
  const now = new Date();
  const todayDate = dateKey(now);
  const timeline = timelineFor(todayDate, weather, prices);
  const daily = (weather?.forecast_daily || []).find((d) => d.date === todayDate) || weather?.forecast_daily?.[0] || {};

  const pvW = finite(goodwe.pv_w);
  const houseW = finite(goodwe.house_w);
  const batterySoc = num(finite(goodwe.battery_soc), 0);
  const gridImportW = finite(goodwe.grid_import_w);
  const gridExportW = finite(goodwe.grid_export_w);
  const spotPrice = finite(priceAt(now, dayFor(todayDate, prices))?.price_total_czk_kwh);

  const pvPower = power(pvW);
  const housePower = power(houseW);
  const gridState = gridImportW === null || gridExportW === null ? 'unknown' : gridExportW > 20 ? 'export' : gridImportW > 20 ? 'import' : 'balanced';
  const gridPower = power(gridState === 'unknown' ? null : Math.max(gridExportW, gridImportW));

  const currentTemp = num(weather?.current?.temp_c, 0);
  const condition = weather?.current?.condition || 'unknown';
  const tempMax = num(daily.temp_max_c, 0);
  const tempMin = num(daily.temp_min_c, 0);
  const sunrise = daily.sunrise ? time(new Date(daily.sunrise)) : '–';
  const sunset = daily.sunset ? time(new Date(daily.sunset)) : '–';
  const rainProb = num(weather?.current?.precipitation_probability, 0);
  const windSpeed = num(weather?.current?.wind_speed_kmh, 0);

  const currentHour = now.getHours() + now.getMinutes() / 60;
  const nowPercent = Math.min(100, Math.max(0, (currentHour / 24) * 100));

  view.innerHTML = `
  <div class="today-screen">
    <!-- 1. HORNÍ PANEL: Pozdrav a Integrovaná meteostanice -->
    <header class="today-header">
      <div class="greeting-box">
        <div class="greeting-title">
          <span class="greeting-sun" aria-hidden="true">☀️</span>
          <h2>${getGreeting(now)}</h2>
        </div>
        <p class="greeting-date">${formatDateFull(now)}</p>
        <p class="greeting-sub">${t('overview.last_data_update')}: ${current.last_measurement_at ? dateTime(current.last_measurement_at) : '–'}</p>
      </div>

      <div class="weather-station-widget">
        <div class="weather-main-temp">
          <div class="weather-temp-val">
            <span class="temp-num">${currentTemp}°</span>
            <span class="temp-cond">${t(`weather.${condition}`)}</span>
          </div>
          <div class="weather-sun-times">
            <span>↑ ${tempMax}° ↓ ${tempMin}°</span>
            <span>☀️ ${sunrise} 🌙 ${sunset}</span>
          </div>
        </div>
        <div class="weather-details">
          <div class="weather-detail-item">
            <span class="detail-label">${t('advisor.rain_prob')}</span>
            <span class="detail-val">${rainProb} %</span>
          </div>
          <div class="weather-detail-item">
            <span class="detail-label">${t('advisor.wind_speed')}</span>
            <span class="detail-val">${windSpeed} km/h</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 2. KOMPAKTNÍ DOPORUČENÍ DNE -->
    <section class="today-recommendation-panel" aria-labelledby="hero-rec-title">
      <div class="hero-primary-card">
        <div class="hero-card-kicker">${t('advisor.best_action')}</div>
        <h3 id="hero-rec-title" class="hero-card-heading">${t('advisor.best_time_consumption')}</h3>
        <div class="hero-main-window${advice.day?.best_appliance_window ? '' : ' hero-main-window--unavailable'}">${advice.best}</div>
        <div class="hero-card-footer">
          <span class="hero-check-badge">${t('prediction.confidence')}: ${advice.day ? t(`prediction.confidence_${advice.day.confidence || 'low'}`) : '–'}</span>
          <button type="button" class="btn btn--secondary btn--touch" id="btn-why-now">${t('advisor.why_now_btn')}</button>
        </div>
      </div>

      <div class="recommendation-statuses">
        <div class="recommendation-status recommendation-status--now">
          <span>${t('advisor.now_is')}</span><strong>${t('advisor.' + (timeline.find(slot => now.getHours() >= slot.start && now.getHours() < slot.start + 3)?.level || 'unknown'))}</strong>
        </div>
        <div class="recommendation-status recommendation-status--avoid">
          <span>${t('advisor.avoid_label')}</span><strong>⚠ ${advice.avoid}</strong>
        </div>
        <div class="recommendation-status recommendation-status--solar">
          <span>${t('advisor.expected_label')}</span><strong>${formatRange(advice.day?.pv_kwh_low, advice.day?.pv_kwh_high, 1, 'unit.kwh')}</strong>
        </div>
      </div>
    </section>

    <!-- 3. KPI TELEMETRIE (6 karet) -->
    <section class="today-kpi-strip" aria-label="${t('advisor.live_title')}">
      <article class="kpi-card kpi-card--pv">
        <div class="kpi-icon-wrap" aria-hidden="true">☀️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.pv')}</span>
          <div class="kpi-value">${pvPower.value} <span class="kpi-unit">${pvPower.unit}</span></div>
          <span class="kpi-trend kpi-trend--up">${current.last_measurement_at ? dateTime(current.last_measurement_at) : t('meter.missing')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--house">
        <div class="kpi-icon-wrap" aria-hidden="true">🏠</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.house')}</span>
          <div class="kpi-value">${housePower.value} <span class="kpi-unit">${housePower.unit}</span></div>
          <span class="kpi-trend kpi-trend--neutral">${current.last_measurement_at ? dateTime(current.last_measurement_at) : t('meter.missing')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--battery">
        <div class="kpi-icon-wrap" aria-hidden="true">🔋</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.battery')}</span>
          <div class="kpi-value">${batterySoc} <span class="kpi-unit">%</span></div>
          <span class="kpi-trend kpi-trend--good">${batteryText(goodwe)}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--grid">
        <div class="kpi-icon-wrap" aria-hidden="true">🗼</div>
        <div class="kpi-body">
          <span class="kpi-label">${t(gridState === 'export' ? 'entity.grid_export' : gridState === 'import' ? 'entity.grid_import' : 'entity.grid')}</span>
          <div class="kpi-value">${gridPower.value} <span class="kpi-unit">${gridPower.unit}</span></div>
          <span class="kpi-trend kpi-trend--warning">${t(`flow.grid_${gridState}`)}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--price">
        <div class="kpi-icon-wrap" aria-hidden="true">🏷️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.price')}</span>
          <div class="kpi-value">${num(spotPrice, 2)} <span class="kpi-unit">${t('unit.czk_kwh')}</span></div>
          <span class="kpi-trend kpi-trend--good">${current.last_measurement_at ? dateTime(current.last_measurement_at) : t('meter.missing')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--heatpump">
        <div class="kpi-icon-wrap" aria-hidden="true">♨️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.heatpump')}</span>
          <div class="kpi-value">${power(source(current, 'shelly').heatpump_power_w).value} <span class="kpi-unit">${power(source(current, 'shelly').heatpump_power_w).unit}</span></div>
          <span class="kpi-trend kpi-trend--neutral">${heatpumpText(source(current, 'shelly'))}</span>
        </div>
      </article>
    </section>

    <!-- 4. ENERGETICKÝ RYTMUS DNE (24h timeline) -->
    <section class="rhythm-section" aria-labelledby="rhythm-title">
      <div class="rhythm-left-panel">
        <header class="rhythm-header">
          <h3 id="rhythm-title" class="rhythm-heading">${t('advisor.timeline_title')}</h3>
          <div class="rhythm-production-summary">
            <span>${t('advisor.daily_pv_estimate_title')}</span>
            <strong>${formatRange(advice.day?.pv_kwh_low, advice.day?.pv_kwh_high, 1, 'unit.kwh')}</strong>
            <small>${prediction.generated_at ? dateTime(prediction.generated_at) : '–'}</small>
          </div>
          <div class="rhythm-legend-tags">
            <span class="legend-tag legend-tag--best">● ${t('advisor.best')}</span>
            <span class="legend-tag legend-tag--ok">● ${t('advisor.ok')}</span>
            <span class="legend-tag legend-tag--avoid">● ${t('advisor.avoid')}</span>
          </div>
        </header>

        <!-- 24h barevný pruh s ukazatelem 'now' -->
        <div class="rhythm-bar-container">
          <div class="rhythm-bar">
            ${timeline.map(slot => `<div class="rhythm-seg rhythm-seg--${slot.level}" style="width:12.5%"></div>`).join('')}
          </div>
          <div class="rhythm-now-marker" style="left: ${nowPercent.toFixed(1)}%">
            <span class="now-badge">${time(now)}</span>
            <div class="now-line"></div>
          </div>
        </div>

        <div class="rhythm-hours-row">
          <span>00:00</span><span>03:00</span><span>06:00</span><span>09:00</span>
          <span>12:00</span><span>15:00</span><span>18:00</span><span>21:00</span><span>24:00</span>
        </div>

        <!-- 8 slotů s počasím, hodnocením a cenou -->
        <div class="rhythm-slots-grid">
          ${timeline.map((slot, index) => {
            const rating = t(`advisor.${slot.level}`);
            const temp = num(slot.hour?.temp_c, 0);
            return `
            <div class="rhythm-slot rhythm-slot--${slot.level}">
              <div class="slot-weather-icon">${weatherIcon(slot.hour?.condition || 'unknown', index >= 2 && index <= 6, 'rhythm-icon')}</div>
              <div class="slot-temp">${temp}°</div>
              <div class="slot-rain">${slot.rainProb}%</div>
              <div class="slot-rating slot-rating--${slot.level}">${rating}</div>
              <div class="slot-price">${num(slot.price, 2)} Kč</div>
            </div>`;
          }).join('')}
        </div>
      </div>

    </section>

    <!-- 5. SPODNÍ PRACOVNÍ PLOCHA: spotřebiče + graf -->
    <section class="today-workspace-grid">
      <!-- Panel 1: Doporučení spotřebičů -->
      <article class="workspace-card appliances-card">
        <header class="workspace-card-header">
          <h4>${t('advisor.appliances_title')}</h4>
        </header>
        <div class="appliances-list">${['washing_machine','dishwasher','dryer'].map(type => `<div class="appliance-row"><div class="appliance-info"><div class="app-icon-badge">${applianceIcon(type)}</div><div><strong>${t('entity.'+type)}</strong><small>${escapeHtml(advice.best)}</small></div></div></div>`).join('')}
          <p>${heatingPermission(tng)} · ${heatpumpText(source(current,'shelly'))}</p>
          <p>${t(controller.enabled ? 'status.controller_running' : 'status.controller_disabled')}</p>
        </div>
      </article>

      <article class="workspace-card forecast-chart-card"><header class="workspace-card-header"><h4>${t('advisor.outlook_title')}</h4></header>
        <p>${t('flow.forecast_table_note')}</p><div class="forecast-observed-table"><table><thead><tr><th>${t('history.time')}</th><th>${t('advisor.solar_curve')}</th><th>${t('entity.price')}</th></tr></thead><tbody>${timeline.map(slot => `<tr><td>${String(slot.start).padStart(2,'0')}:00</td><td>${num(slot.solar,0)} W/m²</td><td>${num(slot.price,2)} ${t('unit.czk_kwh')}</td></tr>`).join('')}</tbody></table></div>
      </article>
    </section>
  </div>`;

  const btnWhyNow = view.querySelector('#btn-why-now');
  if (btnWhyNow) {
    btnWhyNow.addEventListener('click', () => {
      const dlg = document.getElementById('why-now-dialog');
      if (dlg) dlg.showModal();
    });
  }
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
          <div><dt>${t('prediction.best_appliance_window')}</dt><dd>${bestDay?.best_appliance_window ? escapeHtml(bestDay.best_appliance_window) : '–'}</dd></div>
          <div><dt>${t('prediction.best_dhw_window')}</dt><dd>${dhwDay?.best_dhw_window ? escapeHtml(dhwDay.best_dhw_window) : '–'}</dd></div>
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
        <strong class="story-card__value">${bestDay?.best_appliance_window ? escapeHtml(bestDay.best_appliance_window) : '–'}</strong>
        <div class="story-data-rows">
          <div class="story-data-row"><span>${t('prediction.best_appliance_window')}</span><strong>${bestDay?.best_appliance_window ? escapeHtml(bestDay.best_appliance_window) : '–'}</strong></div>
          <div class="story-data-row"><span>${t('prediction.best_dhw_window')}</span><strong>${dhwDay?.best_dhw_window ? escapeHtml(dhwDay.best_dhw_window) : '–'}</strong></div>
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
      <footer>${day.best_appliance_window ? `<span>${t('forecast.recommendation')}</span><strong>${translatedText('advisor.appliance_window', { window: day.best_appliance_window }, day.best_appliance_window)}</strong>` : `<span>${t('advisor.window_unavailable')}</span>`}</footer>
    </article>`;
  }).join('');
}
