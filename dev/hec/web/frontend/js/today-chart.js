import {patchDOM} from './patch-dom.js?v=36';
import {batteryModel} from './battery-plan.js?v=45';
// Observations and published prices share a time axis, never a unit scale.
import { planSegments } from './day-plan.js?v=41';
import { finite } from './telemetry.js';
import { time, num, t } from './i18n.js';
import { mergeEnergyHistory } from './history-fallback.js?v=34';

const ZONE = 'Europe/Prague';
const clockFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
const parts = date => Object.fromEntries(clockFormatter.formatToParts(date).map(p => [p.type, p.value]));
export function siteDate(date = new Date()) {
  const p = parts(date);
  return `${p.year}-${p.month}-${p.day}`;
}
export function siteClock(date = new Date()) {
  const p = parts(date);
  return `${p.hour}:${p.minute}`;
}
export function siteMoment(day, clock = '00:00') {
  const wall = Date.parse(`${day}T${clock}:00Z`);
  let instant = wall;
  for (let n = 0; n < 3; n++) {
    const p = parts(new Date(instant));
    const represented = Date.parse(`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:00Z`);
    instant += wall - represented;
  }
  return new Date(instant);
}
export function siteTime(value) {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value)) {
    return siteMoment(value.slice(0,10), value.slice(11,16));
  }
  return value instanceof Date ? value : new Date(value);
}
export function siteDateTime(value) {
  return time(siteTime(value), {timeZone: ZONE, day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
}
// A local OTE clock without an offset cannot identify either repeated hour.
export function uniqueSiteMoment(day, clock) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day || '') || !/^([01]\d|2[0-3]):[0-5]\d$/.test(clock || '')) return null;
  const guess = siteMoment(day, clock);
  const candidates = [-3600000,0,3600000].map(delta=>new Date(+guess+delta))
    .filter(d=>siteDate(d)===day && siteClock(d)===clock);
  return candidates.length === 1 ? candidates[0] : null;
}

export function priceInterval(day, period) {
  const start = uniqueSiteMoment(day,period.start);
  const end = period.end === '24:00' ? uniqueSiteMoment(shiftDate(day,1),'00:00') : uniqueSiteMoment(day,period.end);
  if (!start || !end || +end <= +start || +end-+start > 3600000) return null;
  return {start,end};
}
export function shiftDate(day, count) {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + count);
  return d.toISOString().slice(0, 10);
}
export function chartRange(days, now = new Date()) {
  const day = siteDate(now);
  return {from: siteMoment(shiftDate(day, 1 - days)), to: siteMoment(shiftDate(day, 1))};
}
const escape = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export function chartRows(history, prices, range, now = new Date()) {
  const rows = (history?.rows || []).filter(r => {
    const stamp = Date.parse(r.timestamp);
    return stamp >= +range.from && stamp <= Math.min(+now, +range.to);
  }).map(r => ({timestamp: r.timestamp,
    pv: finite(r.pv_w) !== null && finite(r.pv_w) >= 0 ? Number(r.pv_w) / 1000 : null,
    house: finite(r.house_w) !== null && finite(r.house_w) >= 0 ? Number(r.house_w) / 1000 : null,
    price: null, kind: 'measured', sources:r.sources || {pv_w:'goodwe',house_w:'goodwe'}}));
  for (const day of [prices?.today, prices?.tomorrow]) {
    for (const period of day?.periods || []) {
      const interval = priceInterval(day.date,period);
      if (!interval) continue;
      const stamp = interval.start;
      if (+stamp < +range.from || +stamp >= +range.to) continue;
      rows.push({timestamp: stamp.toISOString(), pv: null, house: null,
        price: finite(period.price_total_czk_kwh), kind: 'published_price', end_at: interval.end.toISOString()});
    }
  }
  return rows.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

function panel(rows, fields, unit, range, now, gap, width, offset) {
  const W = width, H = 230, left = 54, right = 18, top = 24, bottom = 36;
  const x = stamp => left + (Date.parse(stamp) - +range.from) / (+range.to - +range.from) * (W - left - right);
  const vals = rows.flatMap(r => fields.map(f => r[f.field])).filter(v => v !== null);
  let min = Math.min(0, ...vals), max = Math.max(1, ...vals);
  if (max === min) max = min + 1;
  max += (max - min) * .08;
  const y = value => H - bottom - (value - min) / (max - min) * (H - top - bottom);
  let markup = `<text x="${left}" y="16" class="today-axis-unit">${escape(unit)}</text>`;
  for (let i = 0; i <= 4; i++) {
    const value = min + (max - min) * i / 4;
    markup += `<line class="today-gridline" x1="${left}" x2="${W-right}" y1="${y(value)}" y2="${y(value)}"/><text class="axis-label" x="${left-8}" y="${y(value)+4}" text-anchor="end">${num(value, 1)}</text>`;
  }
  for (const f of fields) {
    let path = '', previous = null;
    const series = rows.filter(r => r.kind === (f.field === 'price' ? 'published_price' : 'measured'));
    for (const row of series) {
      const value = row[f.field], stamp = Date.parse(row.timestamp);
      if (value === null) {previous = null; continue;}
      const connect = previous !== null && stamp - previous <= gap;
      if (f.field === 'price') {
        // Prices are interval values, not a smooth forecast curve.
        const end = new Date(row.end_at);
        path += `M${x(row.timestamp)} ${y(value)}H${x(new Date(Math.min(+end,+range.to)).toISOString())}`;
      } else path += `${connect?'L':'M'}${x(row.timestamp)} ${y(value)}`;
      markup += `<circle cx="${x(row.timestamp)}" cy="${y(value)}" r="2" fill="${f.color}"/>`;
      previous = stamp;
    }
    markup += `<path data-series="${f.field}" d="${path}" fill="none" stroke="${f.color}" stroke-width="2.5"/>`;
  }
  return `<g transform="translate(0 ${offset})">${markup}</g>`;
}

export function timeline(rows, measured, price, range, now, gap, width, config, status) {
  const left=54, right=18, plotWidth=width-left-right;
  const x=stamp=>left+(+stamp-+range.from)/(+range.to-+range.from)*plotWidth;
  const segments=planSegments(config,now);
  const hasPlan=segments.length>0;
  const battery=batteryModel(status,siteDate(now),siteClock(now),now);
  const hasBattery=battery.drawable;
  const bottom=hasBattery?(hasPlan?588:472):hasPlan?530:410, height=bottom+42;
  let body=panel(rows,measured,t('unit.kw'),range,now,gap,width,0)
    +panel(rows,price,t('unit.czk_kwh'),range,now,gap,width,205);
  if (hasPlan) {
    const day=siteDate(now);
    for (const [mode,key,field,y] of [['heating','plan.heating','heat',444],['boiler','entity.dhw','boiler',502]]) {
      body+=`<text class="axis-label" x="${left}" y="${y-8}">${escape(t('today_chart.plan_label'))}: ${escape(t(key))}</text><rect x="${left}" y="${y}" width="${plotWidth}" height="28" fill="var(--bg-card-subtle)" rx="4"/>`;
      for (const block of segments) {
        if (block.mode!==mode) continue;
        const moment=minute=>minute===1440?siteMoment(shiftDate(day,1)):siteMoment(day,`${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`);
        const from=moment(block.from),to=moment(block.to);
        const bx=x(from),bw=x(to)-bx;
        const detail=`${siteClock(from)}–${block.to===1440?'24:00':siteClock(to)} · ${t(key)}: ${num(block[field],0)} °C · ${t('plan.saved')}`;
        body+=`<g class="timeline-plan-block" data-detail="${escape(detail)}" tabindex="0" role="button" aria-label="${escape(detail)}"><title>${escape(detail)}</title><rect x="${bx}" y="${y}" width="${bw}" height="28" fill="var(--series-${mode==='heating'?'heatpump':'grid-import'})" opacity=".7"/>${bw>40?`<text x="${bx+bw/2}" y="${y+19}" text-anchor="middle" fill="var(--ink-primary)" font-size="12">${num(block[field],0)}°</text>`:''}</g>`;
      }
    }
  }
  // One set of time coordinates spans measurements, published price and saved plan.
  if(hasBattery){
    const y=hasPlan?560:444,day=siteDate(now);
    body+=`<text class="axis-label" x="${left}" y="${y-8}">${escape(t('battery_plan.timeline'))}</text><rect x="${left}" y="${y}" width="${plotWidth}" height="28" fill="var(--bg-card-subtle)" rx="4"/>`;
    for(const window of battery.windows){
      const from=siteMoment(day,`${String(Math.floor(window.start/60)).padStart(2,'0')}:${String(window.start%60).padStart(2,'0')}`),to=siteMoment(day,window.to);
      const bx=x(from),bw=x(to)-bx,detail=`${window.from}–${window.to} · ${t('battery_plan.conditional_charge')} · ≤${num(battery.plan.grid_target_soc_pct,0)} %`;
      body+=`<g class="timeline-plan-block timeline-battery-block" data-detail="${escape(detail)}" tabindex="0" role="button" aria-label="${escape(detail)}"><title>${escape(detail)}</title><rect x="${bx}" y="${y}" width="${bw}" height="28" fill="var(--series-battery)" opacity=".75"/>${bw>45?`<text x="${bx+bw/2}" y="${y+19}" text-anchor="middle" fill="var(--ink-primary)" font-size="12">≤${num(battery.plan.grid_target_soc_pct,0)} %</text>`:''}</g>`;
    }
  }
  let grid='';
  const days=Math.round((+range.to-+range.from)/86400000);
  const step=days<=1?(width<500?6:3):days<=2?(width<500?24:12):(width<500?72:24);
  for(let stamp=+range.from;stamp<=+range.to;stamp+=step*3600000) {
    const at=x(stamp),last=stamp===+range.to;
    const label=days<=1?(last?'24:00':siteClock(new Date(stamp))):days>2?time(new Date(stamp),{timeZone:ZONE,day:'2-digit',month:'2-digit'}):siteDateTime(new Date(stamp));
    grid+=`<line class="today-gridline" x1="${at}" x2="${at}" y1="24" y2="${bottom}" opacity=".6"/>`;
    body+=`<text class="axis-label timeline-hour" x="${at}" y="${bottom+27}" text-anchor="${width<500?'middle':stamp===+range.from?'start':last?'end':'middle'}">${escape(label)}</text>`;
  }
  if (+now>=+range.from&&+now<=+range.to) {
    const at=x(now);
    body+=`<line class="today-now" x1="${at}" x2="${at}" y1="24" y2="${bottom}"/><text class="axis-label" x="${Math.max(left+18,Math.min(width-right-18,at))}" y="16" text-anchor="middle">${escape(t('today_chart.now'))}</text>`;
  }
  return `<svg class="today-plot today-timeline" viewBox="0 0 ${width} ${height}" role="group" aria-label="${escape(t('today_chart.title'))}">${grid}${body}<line class="today-crosshair" y1="24" y2="${bottom}" hidden/></svg>`;
}

let selectedDays = 1;
let tableOpen = false;
const historyCache = new Map();
const rangeLabels = {1:'today_chart.days_1',2:'today_chart.days_2',7:'today_chart.days_7'};

function origin(row) {
  if (row.kind !== 'measured') return t('today_chart.'+row.kind);
  const sources = row.sources || {};
  const pv = row.pv !== null ? sources.pv_w : null;
  const house = row.house !== null ? sources.house_w : null;
  const label = source => source === 'sdg_history' ? t('today_chart.measured_sdg') : t('today_chart.measured');
  if (!pv && !house) return t('meter.missing');
  if (!pv || !house || pv === house) return label(pv || house);
  return `${t('entity.pv')}: ${label(pv)} · ${t('entity.house')}: ${label(house)}`;
}

export async function mountTodayChart(container, {api, prices, config, status, now = new Date()}) {
  let generation = 0;
  const draw = async (days, background = false) => {
    selectedDays = days;
    const ticket = ++generation;
    const range = chartRange(days, now);
    if (!background) container.innerHTML = `<p role="status">${t('today_chart.loading')}</p>`;
    let history, failed = false, partial = false;
    try {
      const key = `${range.from.toISOString()}/${days}`;
      const cached = historyCache.get(key);
      if (cached && Date.now() - cached.fetched < 60000) history = cached.history;
      else {
        const bucket = days === 1 ? 300 : days === 2 ? 600 : 1800;
        const params = {from:range.from.toISOString(), to:new Date(Math.min(+now,+range.to)).toISOString(), bucket};
        const results = await Promise.allSettled([
          api.history({...params,source:'goodwe',fields:'pv_w,house_w'}),
          api.history({...params,source:'sdg_history',fields:'ppvcelkem,total__w'}),
        ]);
        const [goodwe, sdg] = results.map(result=>result.status === 'fulfilled' ? result.value : null);
        if (!goodwe && !sdg) throw new Error('History unavailable');
        partial = results.some(result=>result.status === 'rejected');
        history = mergeEnergyHistory(goodwe,sdg,bucket);
        if (historyCache.size > 6) historyCache.clear();
        if (!partial) historyCache.set(key,{history,fetched:Date.now()});
      }
    } catch {history = {rows:[]}; failed = true;}
    if (ticket !== generation || !container.isConnected) return;
    const rows = chartRows(history, prices, range, now);
    const measured = [{field:'pv',label:t('entity.pv'),color:'var(--series-pv)'},
      {field:'house',label:t('entity.house'),color:'var(--series-house)'}];
    const price = [{field:'price',label:t('entity.price'),color:'var(--series-appliances)'}];
    const gap = Math.max(300, Number(history.bucket_seconds) || (days === 1 ? 300 : days === 2 ? 600 : 1800)) * 1500;
    const width = Math.max(240,container.clientWidth);
    const missingPrices = [prices?.today,prices?.tomorrow].some(day=>
      (day?.periods || []).some(period=>!priceInterval(day.date,period)));
    const target = background ? document.createElement('div') : container;
    target.innerHTML = `<div class="today-chart-controls" role="group" aria-label="${t('today_chart.range')}">${[1,2,7].map(d=>`<button type="button" data-days="${d}" aria-pressed="${days===d}">${t(rangeLabels[d])}</button>`).join('')}<button type="button" data-table aria-expanded="false">${t('history.table')}</button></div>
      <details class="explanation-info"><summary aria-label="${t('today_chart.info')}">ⓘ</summary><p class="today-chart-note">${t('today_chart.note')}</p><p>${t('today_chart.inspect')}</p></details>
      ${missingPrices?`<p class="today-chart-note">${t('today_chart.ambiguous_price')}</p>`:''}
      ${failed?`<p role="alert">${t('today_chart.failed')}</p>`:''}
      ${partial?`<p role="alert">${t('today_chart.partial')}</p>`:''}
      ${!rows.some(r=>r.pv!==null||r.house!==null)?`<p>${t('today_chart.no_measurements')}</p>`:''}
      <div class="today-chart-legend">${[...measured,...price].map(f=>`<span style="--series:${f.color}">${f.label}</span>`).join('')}</div>
      <div class="today-chart-panels">${timeline(rows,measured,price,range,now,gap,width,config,status)}</div>
      <output class="today-chart-tooltip" aria-live="polite"></output>
      <div class="today-chart-table table-wrap" hidden><table><thead><tr><th>${t('history.time')}</th><th>${t('entity.pv')} (kW)</th><th>${t('entity.house')} (kW)</th><th>${t('entity.price')} (${t('unit.czk_kwh')})</th><th>${t('today_chart.origin')}</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${siteDateTime(r.timestamp)}</td><td>${num(r.pv,2)}</td><td>${num(r.house,2)}</td><td>${num(r.price,2)}</td><td>${origin(r)}</td></tr>`).join('')}</tbody></table></div>`;
    if (background) {
      for (const selector of ['.today-chart-panels','.today-chart-table']) {
        patchDOM(container.querySelector(selector),target.querySelector(selector));
      }
      const oldAlerts=[...container.querySelectorAll('[role="alert"]')];
      oldAlerts.forEach(alert=>alert.remove());
      target.querySelectorAll('[role="alert"]').forEach(alert=>container.prepend(alert));
    }
    container.querySelectorAll('[data-days]').forEach(b=>{b.onclick=()=>draw(Number(b.dataset.days));});
    container.querySelector('.today-chart-table').hidden = !tableOpen;
    container.querySelector('[data-table]').setAttribute('aria-expanded',String(tableOpen));
    container.querySelector('[data-table]').onclick=event=>{
      const table = container.querySelector('.today-chart-table');
      table.hidden = !table.hidden;
      tableOpen = !table.hidden;
      event.currentTarget.setAttribute('aria-expanded',String(!table.hidden));
    };
    const panels = container.querySelector('.today-chart-panels');
    panels.tabIndex = 0;
    panels.setAttribute('role','group');
    panels.setAttribute('aria-label',t('today_chart.inspect'));
    let selected = 0;
    const inspect = stamp => {
      if (!rows.length) return;
      const observations = rows.filter(r=>r.kind==='measured');
      const nearest = observations.reduce((best,r)=>Math.abs(Date.parse(r.timestamp)-stamp)<Math.abs(Date.parse(best.timestamp)-stamp)?r:best,observations[0]);
      const near = nearest && Math.abs(Date.parse(nearest.timestamp)-stamp)<=gap/2 ? nearest : null;
      const tariff = rows.find(r=>r.kind==='published_price' && Date.parse(r.timestamp)<=stamp && Date.parse(r.end_at)>stamp);
      container.querySelector('output').textContent = `${siteDateTime(new Date(stamp))} · ${t('entity.pv')}: ${num(near?.pv,2)} kW · ${t('entity.house')}: ${num(near?.house,2)} kW · ${t('entity.price')}: ${num(tariff?.price,2)} ${t('unit.czk_kwh')}`;
      panels.querySelectorAll('.today-crosshair').forEach(line=>{
        line.removeAttribute('hidden');
        const x = 54 + (stamp-+range.from)/(+range.to-+range.from)*(width-72);
        line.setAttribute('x1',x);line.setAttribute('x2',x);
      });
    };
    panels.querySelectorAll('[data-detail]').forEach(block=>{
      const show=()=>{container.querySelector('output').textContent=block.dataset.detail;};
      block.onclick=show;
      block.onkeydown=event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();event.stopPropagation();show();}};
    });
    panels.onpointermove=event=>{
      const svg = event.target.closest('svg'); if (!svg) return;
      const b = svg.getBoundingClientRect();
      inspect(+range.from+Math.max(0,Math.min(1,((event.clientX-b.left)/b.width*width-54)/(width-72)))*(+range.to-+range.from));
    };
    panels.onkeydown=event=>{
      if (!['ArrowLeft','ArrowRight'].includes(event.key)||!rows.length) return;
      event.preventDefault(); selected=Math.max(0,Math.min(rows.length-1,selected+(event.key==='ArrowRight'?1:-1)));
      inspect(Date.parse(rows[selected].timestamp));
    };
  };
  await draw(selectedDays);
  return async (nextPrices,nextConfig,nextStatus) => { prices=nextPrices || prices; config=nextConfig || config; status=nextStatus || status; now=new Date(); await draw(selectedDays,true); };
}
