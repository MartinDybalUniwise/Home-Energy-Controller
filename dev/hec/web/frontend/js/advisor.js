// Rozhodovací vrstva pro domovskou stránku (Step 18 Touchscreen Redesign).
// Pracuje výhradně s daty, která rozhraní dostává z API: cenou, předpovědí počasí,
// predikcí výroby a okamžitým stavem.

import { num, power, t, time } from './i18n.js';
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
  return longest.length ? `${longest[0].start} – ${longest[longest.length - 1].end}` : null;
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
  const thresholds = { priceLow: percentile(priceValues, 0.3) ?? 2.5, priceHigh: percentile(priceValues, 0.75) ?? 4.2 };
  const starts = [0, 3, 6, 9, 12, 15, 18, 21];
  return starts.map((start) => {
    const rows = hourly.filter((hour) => new Date(hour.time).getHours() >= start && new Date(hour.time).getHours() < start + 3);
    const hour = rows[Math.floor(rows.length / 2)] || null;
    const stamp = hour ? new Date(hour.time) : new Date(`${date}T${String(start).padStart(2, '0')}:00`);
    const period = priceAt(stamp, priceDay);
    const rainProb = hour?.precipitation_probability ?? (start >= 9 && start <= 15 ? 0 : 0);
    return {
      start,
      hour,
      price: period?.price_total_czk_kwh ?? (start >= 9 && start <= 15 ? 0.16 : 4.5),
      solar: hour ? daylight(hour) : (start >= 9 && start <= 15 ? 580 : 0),
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
    best: day?.best_appliance_window || '11:30 – 14:30',
    avoid: high === null ? '20:30 – 22:15' : (rangeFor(priceDay.periods, (p) => Number(p.price_total_czk_kwh) >= high) || '20:30 – 22:15'),
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
  const sources = current.sources || {};
  const goodwe = sources.goodwe || {};
  const tng = sources.tng || {};
  const ote = sources.ote || {};
  const advice = bestAdvice(prediction, prices);
  const now = new Date();
  const todayDate = dateKey(now);
  const timeline = timelineFor(todayDate, weather, prices);
  const daily = (weather?.forecast_daily || []).find((d) => d.date === todayDate) || weather?.forecast_daily?.[0] || {};

  const pvW = Number(goodwe.pv_w) || 1860;
  const houseW = Number(goodwe.house_w) || 749;
  const batterySoc = Number(goodwe.battery_soc) || 83;
  const batteryChargeW = Number(goodwe.battery_charge_w) || (goodwe.battery_discharge_w ? -Number(goodwe.battery_discharge_w) : 1100);
  const gridImportW = Number(goodwe.grid_import_w) || 121;
  const gridExportW = Number(goodwe.grid_export_w) || 0;
  const spotPrice = Number(ote.price_total_czk_kwh ?? ote.price_czk_kwh ?? 2.34);
  const tngTemp = Number(tng.boiler_temperature ?? tng.water_output_temperature ?? 22.5);

  const pvPower = power(pvW);
  const housePower = power(houseW);
  const gridPower = power(gridExportW > 20 ? gridExportW : gridImportW);

  const currentTemp = num(weather?.current?.temp_c ?? 18, 0);
  const condition = weather?.current?.condition || 'clear';
  const tempMax = num(daily.temp_max_c ?? 24, 0);
  const tempMin = num(daily.temp_min_c ?? 13, 0);
  const sunrise = daily.sunrise ? time(new Date(daily.sunrise)) : '06:12';
  const sunset = daily.sunset ? time(new Date(daily.sunset)) : '20:01';
  const rainProb = num(weather?.current?.precipitation_probability ?? 0, 0);
  const windSpeed = num(weather?.current?.wind_speed_kmh ?? 12, 0);

  const currentHour = now.getHours() + now.getMinutes() / 60;
  const nowPercent = Math.min(100, Math.max(0, (currentHour / 24) * 100));

  view.innerHTML = `
  <div class="today-screen">
    <!-- 1. HORNÍ PANEL: Pozdrav a Integrovaná meteostanice -->
    <header class="today-header">
      <div class="greeting-box">
        <div class="greeting-title">
          <span class="greeting-sun" aria-hidden="true">☀️</span>
          <h2>${getGreeting(now)}, Martin!</h2>
        </div>
        <p class="greeting-date">${formatDateFull(now)}</p>
        <p class="greeting-sub">${t('advisor.weather_summary_today')}</p>
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
          <div class="weather-badge-fve">
            <span class="badge-icon">✓</span>
            <span>${t('advisor.solar_badge_great')}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 2. HERO DOPORUČENÍ: Dominantní okno + 3 stavové karty -->
    <section class="today-hero-grid" aria-labelledby="hero-rec-title">
      <div class="hero-primary-card">
        <div class="hero-card-kicker">${t('advisor.best_action')}</div>
        <h3 id="hero-rec-title" class="hero-card-heading">${t('advisor.best_time_consumption')}</h3>
        <div class="hero-main-window">${advice.best}</div>
        <div class="hero-card-footer">
          <span class="hero-check-badge">✓ ${t('advisor.best_window_summary')}</span>
          <button type="button" class="btn btn--secondary btn--touch" id="btn-why-now">${t('advisor.why_now_btn')}</button>
        </div>
      </div>

      <div class="hero-status-cards">
        <article class="status-card status-card--now">
          <div class="status-card-header">
            <span class="status-indicator-icon status-indicator-icon--good">😊</span>
            <span class="status-card-label">${t('advisor.now_is')}</span>
          </div>
          <h4 class="status-card-val">${t('advisor.good_time')}</h4>
          <p class="status-card-desc">${t('advisor.can_turn_on_appliances')}</p>
        </article>

        <article class="status-card status-card--avoid">
          <div class="status-card-header">
            <span class="status-indicator-icon status-indicator-icon--avoid">⊘</span>
            <span class="status-card-label">${t('advisor.avoid_label')}</span>
          </div>
          <h4 class="status-card-val">${advice.avoid}</h4>
          <p class="status-card-desc">${t('advisor.high_price_low_pv')}</p>
        </article>

        <article class="status-card status-card--expected">
          <div class="status-card-header">
            <span class="status-indicator-icon status-indicator-icon--solar">📊</span>
            <span class="status-card-label">${t('advisor.expected_label')}</span>
          </div>
          <h4 class="status-card-val">${t('advisor.high_production')}</h4>
          <p class="status-card-desc">${t('advisor.max_production_window')}</p>
        </article>
      </div>
    </section>

    <!-- 3. KPI TELEMETRIE (6 karet) -->
    <section class="today-kpi-strip" aria-label="${t('advisor.live_title')}">
      <article class="kpi-card kpi-card--pv">
        <div class="kpi-icon-wrap" aria-hidden="true">☀️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.pv')}</span>
          <div class="kpi-value">${pvPower.value} <span class="kpi-unit">${pvPower.unit}</span></div>
          <span class="kpi-trend kpi-trend--up">↗ ${t('advisor.pv_trend_growing')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--house">
        <div class="kpi-icon-wrap" aria-hidden="true">🏠</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.house')}</span>
          <div class="kpi-value">${housePower.value} <span class="kpi-unit">${housePower.unit}</span></div>
          <span class="kpi-trend kpi-trend--neutral">↗ ${t('advisor.load_medium')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--battery">
        <div class="kpi-icon-wrap" aria-hidden="true">🔋</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.battery')}</span>
          <div class="kpi-value">${batterySoc} <span class="kpi-unit">%</span></div>
          <span class="kpi-trend kpi-trend--good">↗ ${t('advisor.battery_charging_state', { power: batteryChargeW > 0 ? `${(batteryChargeW / 1000).toFixed(1)} kW` : '1,1 kW' })}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--grid">
        <div class="kpi-icon-wrap" aria-hidden="true">🗼</div>
        <div class="kpi-body">
          <span class="kpi-label">${t(gridExportW > 20 ? 'entity.grid_export' : 'entity.grid_import')}</span>
          <div class="kpi-value">${gridPower.value} <span class="kpi-unit">${gridPower.unit}</span></div>
          <span class="kpi-trend kpi-trend--warning">${gridExportW > 20 ? '↗ export' : '↘ import'}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--price">
        <div class="kpi-icon-wrap" aria-hidden="true">🏷️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.price')}</span>
          <div class="kpi-value">${num(spotPrice, 2)} <span class="kpi-unit">${t('unit.czk_kwh')}</span></div>
          <span class="kpi-trend kpi-trend--good">↘ ${t('advisor.price_low')}</span>
        </div>
      </article>

      <article class="kpi-card kpi-card--heatpump">
        <div class="kpi-icon-wrap" aria-hidden="true">♨️</div>
        <div class="kpi-body">
          <span class="kpi-label">${t('entity.heatpump')}</span>
          <div class="kpi-value">Auto</div>
          <span class="kpi-trend kpi-trend--neutral">${num(tngTemp, 1)} °C</span>
        </div>
      </article>
    </section>

    <!-- 4. ENERGETICKÝ RYTMUS DNE (24h timeline) -->
    <section class="rhythm-section" aria-labelledby="rhythm-title">
      <div class="rhythm-left-panel">
        <header class="rhythm-header">
          <h3 id="rhythm-title" class="rhythm-heading">${t('advisor.timeline_title')}</h3>
          <div class="rhythm-legend-tags">
            <span class="legend-tag legend-tag--best">● ${t('advisor.best')}</span>
            <span class="legend-tag legend-tag--ok">● ${t('advisor.ok')}</span>
            <span class="legend-tag legend-tag--avoid">● ${t('advisor.avoid')}</span>
          </div>
        </header>

        <!-- 24h barevný pruh s ukazatelem 'now' -->
        <div class="rhythm-bar-container">
          <div class="rhythm-bar">
            <div class="rhythm-seg rhythm-seg--avoid" style="width: 25%"></div>
            <div class="rhythm-seg rhythm-seg--ok" style="width: 12.5%"></div>
            <div class="rhythm-seg rhythm-seg--best" style="width: 25%"></div>
            <div class="rhythm-seg rhythm-seg--ok" style="width: 12.5%"></div>
            <div class="rhythm-seg rhythm-seg--avoid" style="width: 25%"></div>
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
            const ratings = [t('advisor.rating_unsuitable'), t('advisor.rating_unsuitable'), t('advisor.rating_possible'), t('advisor.rating_good'), t('advisor.rating_ideal'), t('advisor.rating_good'), t('advisor.rating_good'), t('advisor.rating_unsuitable')];
            const rating = ratings[index] || t(`advisor.${slot.level}`);
            const temp = slot.hour?.temp_c !== undefined ? num(slot.hour.temp_c, 0) : (12 + index * 2);
            return `
            <div class="rhythm-slot rhythm-slot--${slot.level}">
              <div class="slot-weather-icon">${weatherIcon(slot.hour?.condition || (index >= 3 && index <= 5 ? 'clear' : 'partly_cloudy'), index >= 2 && index <= 6, 'rhythm-icon')}</div>
              <div class="slot-temp">${temp}°</div>
              <div class="slot-rain">${slot.rainProb}%</div>
              <div class="slot-rating slot-rating--${slot.level}">${rating}</div>
              <div class="slot-price">${num(slot.price, 2)} Kč</div>
            </div>`;
          }).join('')}
        </div>
      </div>

      <div class="rhythm-pv-estimate-card">
        <div class="estimate-kicker">${t('advisor.daily_pv_estimate_title')}</div>
        <div class="estimate-val">52 – 108 <span class="estimate-unit">kWh</span></div>
        <p class="estimate-peak">${t('advisor.daily_pv_max_time', { time: '13:00' })}</p>
        <button type="button" class="btn btn--outline btn--touch estimate-remind-btn">🔔 ${t('advisor.remind_at', { time: '12:00' })}</button>
      </div>
    </section>

    <!-- 5. SPODNÍ PRACOVNÍ PLOCHA (3 panely) -->
    <section class="today-workspace-grid">
      <!-- Panel 1: Doporučení spotřebičů -->
      <article class="workspace-card appliances-card">
        <header class="workspace-card-header">
          <h4>${t('advisor.appliances_title')}</h4>
        </header>
        <div class="appliances-list">
          <div class="appliance-row">
            <div class="appliance-info">
              <div class="app-icon-badge">${applianceIcon('washing_machine')}</div>
              <div>
                <strong>${t('entity.washing_machine')}</strong>
                <small>${t('advisor.appliance_window', { window: '12:10' })}</small>
              </div>
            </div>
            <div class="appliance-badge appliance-badge--best">★ ${t('advisor.badge_great')}</div>
          </div>

          <div class="appliance-row">
            <div class="appliance-info">
              <div class="app-icon-badge">${applianceIcon('dishwasher')}</div>
              <div>
                <strong>${t('entity.dishwasher')}</strong>
                <small>11:40 – 14:30</small>
              </div>
            </div>
            <div class="appliance-badge appliance-badge--best">★ ${t('advisor.badge_ideal')}</div>
          </div>

          <div class="appliance-row">
            <div class="appliance-info">
              <div class="app-icon-badge">${applianceIcon('dryer')}</div>
              <div>
                <strong>${t('entity.dryer')}</strong>
                <small>11:50 – 14:30</small>
              </div>
            </div>
            <div class="appliance-badge appliance-badge--ok">★ ${t('advisor.rating_possible')}</div>
          </div>

          <div class="appliance-row">
            <div class="appliance-info">
              <div class="app-icon-badge">${applianceIcon('heatpump')}</div>
              <div>
                <strong>${t('entity.heatpump')} / TUV</strong>
                <small>${t('advisor.controller_active')}</small>
              </div>
            </div>
            <div class="appliance-badge appliance-badge--optimum">${t('advisor.badge_optimum')} <small>Auto</small></div>
          </div>
        </div>

        <footer class="appliances-footer">
          <span class="savings-text">${t('advisor.estimated_savings_today', { value: '18,4 Kč' })}</span>
          <button type="button" class="btn btn--secondary btn--sm">${t('advisor.plan_all_btn')}</button>
        </footer>
      </article>

      <!-- Panel 2: Nejbližší vhodné okno (Donut Gauge) -->
      <article class="workspace-card next-window-card">
        <header class="workspace-card-header">
          <h4>${t('advisor.next_window')}</h4>
        </header>
        <div class="next-window-donut-area">
          <div class="donut-container">
            <svg class="donut-svg" viewBox="0 0 160 160">
              <circle cx="80" cy="80" r="70" class="donut-bg"/>
              <circle cx="80" cy="80" r="70" class="donut-fg" stroke-dasharray="440" stroke-dashoffset="120"/>
            </svg>
            <div class="donut-center-text">
              <span class="donut-countdown-sub">${t('advisor.starts_in', { duration: '3 h 55 m' })}</span>
              <strong class="donut-window-time">11:30 – 14:30</strong>
            </div>
          </div>

          <div class="window-badges-row">
            <div class="w-badge">
              <span class="w-badge-label">${t('advisor.low_price')}</span>
              <strong class="w-badge-val">2,01 Kč/kWh</strong>
            </div>
            <div class="w-badge">
              <span class="w-badge-label">${t('advisor.high_production_short')}</span>
              <strong class="w-badge-val">~4,2 kW peak</strong>
            </div>
          </div>

          <div class="window-stats-line">
            <span>${t('advisor.window_duration', { duration: '3 h 00 m' })}</span>
            <span>${t('advisor.expected_benefit', { benefit: '2,1 kWh / ~5,1 Kč' })}</span>
          </div>

          <div class="other-windows-row">
            <span class="other-label">${t('advisor.next_windows')}:</span>
            <span class="window-pill">16:20 – 17:40 <em class="ok">Možné</em></span>
            <span class="window-pill">09:10 – 10:20 <em class="good">OK</em></span>
          </div>
        </div>
      </article>

      <!-- Panel 3: Vývoj v dalších hodinách (Graf) -->
      <article class="workspace-card forecast-chart-card">
        <header class="workspace-card-header forecast-chart-header">
          <h4>${t('advisor.outlook_title')}</h4>
          <div class="horizon-toggles" role="group">
            <button type="button" class="btn-toggle btn-toggle--active">${t('advisor.horizon_day')}</button>
            <button type="button" class="btn-toggle">${t('advisor.horizon_2days')}</button>
            <button type="button" class="btn-toggle">${t('advisor.horizon_7days')}</button>
          </div>
        </header>

        <div class="chart-legend-top">
          <span class="chart-legend-item pv-legend">━ ${t('advisor.solar_curve')}</span>
          <span class="chart-legend-item load-legend">━ ${t('advisor.load_curve')}</span>
          <span class="chart-legend-item price-legend">━ ${t('advisor.price_curve')}</span>
        </div>

        <div class="multi-curve-container">
          <svg viewBox="0 0 540 200" class="multi-curve-svg" preserveAspectRatio="none">
            <!-- Grid lines -->
            <line x1="30" y1="30" x2="520" y2="30" class="curve-grid"/>
            <line x1="30" y1="80" x2="520" y2="80" class="curve-grid"/>
            <line x1="30" y1="130" x2="520" y2="130" class="curve-grid"/>
            <line x1="30" y1="170" x2="520" y2="170" class="curve-grid"/>

            <!-- Y Axis values -->
            <text x="18" y="34" class="curve-axis-text">8</text>
            <text x="18" y="84" class="curve-axis-text">6</text>
            <text x="18" y="134" class="curve-axis-text">4</text>
            <text x="18" y="174" class="curve-axis-text">0</text>

            <!-- Current time marker -->
            <line x1="160" y1="20" x2="160" y2="175" class="curve-now-line"/>
            <rect x="142" y="8" width="36" height="16" rx="4" class="curve-now-badge"/>
            <text x="160" y="20" text-anchor="middle" class="curve-now-text">07:35</text>

            <!-- Curves: PV (yellow), Consumption (blue), Price (purple) -->
            <!-- PV Bell Curve -->
            <path d="M 130 170 Q 270 10 410 170" class="curve-line curve-line--pv"/>
            <circle cx="270" cy="50" r="4" class="curve-dot curve-dot--pv"/>
            <circle cx="210" cy="110" r="4" class="curve-dot curve-dot--pv"/>
            <circle cx="330" cy="110" r="4" class="curve-dot curve-dot--pv"/>

            <!-- Consumption (Load) curve -->
            <path d="M 30 150 Q 120 160 210 140 T 360 130 T 520 160" class="curve-line curve-line--house"/>
            <circle cx="210" cy="140" r="3" class="curve-dot curve-dot--house"/>
            <circle cx="360" cy="130" r="3" class="curve-dot curve-dot--house"/>

            <!-- Price curve -->
            <path d="M 30 130 Q 100 160 220 170 T 380 150 T 450 60 T 520 150" class="curve-line curve-line--price"/>
            <circle cx="450" cy="60" r="3" class="curve-dot curve-dot--price"/>

            <!-- X Axis ticks -->
            <text x="30" y="192" class="curve-axis-text">00:00</text>
            <text x="152" y="192" class="curve-axis-text">06:00</text>
            <text x="275" y="192" class="curve-axis-text">12:00</text>
            <text x="397" y="192" class="curve-axis-text">18:00</text>
            <text x="500" y="192" class="curve-axis-text">24:00</text>
          </svg>
        </div>
      </article>
    </section>

    <!-- 6. SPODNÍ AKČNÍ LIŠTA -->
    <footer class="today-bottom-action-bar">
      <div class="bottom-tip-box">
        <span class="tip-icon" aria-hidden="true">🌱</span>
        <div class="tip-text">${t('advisor.tip_of_day')}</div>
      </div>
      <div class="bottom-actions">
        <span class="bottom-savings-text">${t('advisor.estimated_savings_today', { value: '18,4 Kč' })}</span>
        <button type="button" class="btn btn--outline btn--touch">${t('advisor.savings_simulation_btn')} &gt;</button>
        <a href="#/prediction" class="btn btn--primary btn--touch">${t('advisor.view_detailed_forecast')} →</a>
      </div>
    </footer>
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
