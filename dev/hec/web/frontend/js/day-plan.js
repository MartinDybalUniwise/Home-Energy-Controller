import { t, num } from './i18n.js';

const minutes = clock => Number(clock.slice(0,2))*60+Number(clock.slice(3,5));
const clock = minute => `${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`;
const effective = (section,date) => ({...section,...section?.date_overrides?.[date]});
function value(section, minute, field, fallback) {
  let result=fallback;
  for (const block of section?.schedule || []) {
    const from=minutes(block.from),to=minutes(block.to);
    if (from<to ? minute>=from&&minute<to : minute>=from||minute<to) result=block[field];
  }
  return result;
}
export function planSegments(config, now = new Date()) {
  if (!config?.tng) return [];
  const date = new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Prague'}).format(now);
  const heating=effective(config.tng.heating,date),boiler=effective(config.tng.boiler,date);
  const operation=effective(config.tng.operation,date);
  const edges=new Set([0,1440]);
  for (const section of [heating,boiler,operation]) for (const b of section.schedule||[]) {
    edges.add(minutes(b.from));edges.add(minutes(b.to));
  }
  const sorted=[...edges].sort((a,b)=>a-b);
  return sorted.slice(0,-1).map((from,i)=>({from,to:sorted[i+1],
    mode:value(operation,from,'mode',operation.default_mode || 'unknown'),
    heat:value(heating,from,'temperature',heating.default_temperature),
    boiler:value(boiler,from,'temperature',boiler.default_temperature)}));
}
export function renderDayPlan(container, config, now = new Date(), prediction = {}, current = {}) {
  const segments=planSegments(config,now);
  container.replaceChildren();
  if (!segments.length) { container.textContent=t('app.no_data'); return; }
  const local=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit'}).format(now);
  const at=minutes(local);
  const axis=document.createElement('div');axis.className='plan-axis';
  for (const hour of ['00','06','12','18','24']) {const label=document.createElement('span');label.textContent=hour;axis.append(label);}
  container.append(axis);
  for (const [mode,key,field] of [['heating','entity.heatpump','heat'],['boiler','entity.dhw','boiler']]) {
    const label=document.createElement('div');label.className='meta';label.textContent=t(key);container.append(label);
    const lane=document.createElement('div');lane.className=`plan-lane plan-lane--${mode}`;
    for (const block of segments) {
      const button=document.createElement('button');button.type='button';button.className='plan-block';
      button.style.left=`${block.from/14.4}%`;button.style.width=`${(block.to-block.from)/14.4}%`;
      button.dataset.detail=`${clock(block.from)}–${clock(block.to)} · ${t(key)}: ${block.mode===mode?num(block[field],0)+' °C':t('plan.inactive')}`;
      button.setAttribute('aria-label',button.dataset.detail);
      button.dataset.active=String(block.mode===mode);
      const temperature=Number(block[field]);
      button.style.setProperty('--plan-strength',`${Math.max(20,Math.min(95,20+(temperature-20)/35*75))}%`);
      if (block.mode===mode && block.to-block.from>=90) button.textContent=`${num(block[field],0)}°`;
      lane.append(button);
    }
    const marker=document.createElement('span');marker.className='plan-now';marker.style.left=`${at/14.4}%`;marker.setAttribute('aria-hidden','true');lane.append(marker);container.append(lane);
  }
  const detail=document.createElement('p');detail.className='meta plan-detail';detail.setAttribute('aria-live','polite');
  const currentSegment=segments.find(b=>at>=b.from&&at<b.to);
  detail.textContent=`${t('plan.now')}: ${t(currentSegment?.mode==='boiler'?'entity.dhw':'entity.heatpump')} · ${t('plan.saved')}`;
  container.append(detail);
  const date = new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Prague'}).format(now);
  const day=(prediction.days||[]).find(day=>day.date===date);
  const forecast=day?.forecast_consumption;
  const middle=forecast?.value;
  if (typeof middle==='number' && Number.isFinite(middle)) {
    const heading=document.createElement('h4');heading.textContent=t('plan.consumption');container.append(heading);
    const actualSource=current.sources?.goodwe;
    const stamp=new Date(actualSource?.timestamp);
    const age=now-stamp;
    const actual=age>=-60000&&age<=120000&&Number.isFinite(actualSource?.e_load_day_kwh)?actualSource.e_load_day_kwh:null;
    const [low,high]=forecast.range||[middle,middle];
    const maximum=Math.max(high,middle,actual||0)*1.1 || 1;
    const scale=value=>20+value/maximum*260;
    const ns='http://www.w3.org/2000/svg';
    const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 300 50');
    svg.setAttribute('role','img');svg.setAttribute('aria-label',`${t('plan.middle')}: ${num(middle,1)} kWh; ${num(low,1)}–${num(high,1)} kWh`);
    const mark=(tag,attrs)=>{const node=document.createElementNS(ns,tag);for(const[key,value]of Object.entries(attrs))node.setAttribute(key,value);svg.append(node);return node;};
    mark('line',{x1:20,x2:280,y1:28,y2:28,stroke:'var(--divider)','stroke-width':6});
    mark('line',{x1:scale(low),x2:scale(high),y1:28,y2:28,stroke:'var(--series-house)','stroke-width':10,opacity:.25});
    if(actual!==null)mark('line',{x1:20,x2:scale(actual),y1:28,y2:28,stroke:'var(--series-house)','stroke-width':4});
    mark('line',{x1:scale(middle),x2:scale(middle),y1:17,y2:39,stroke:'var(--ink-primary)','stroke-width':2});
    const label=mark('text',{x:150,y:12,'text-anchor':'middle',fill:'var(--ink-primary)','font-size':12});label.textContent=`${t('plan.middle')} ${num(middle,1)} kWh`;
    container.append(svg);
    const summary=document.createElement('p');summary.className='meta';
    summary.textContent=`${t('plan.range')}: ${num(low,1)}–${num(high,1)} kWh · ${t('plan.measured')}: ${actual===null?'—':num(actual,1)+' kWh'}`;
    container.append(summary);
    const info=document.createElement('details');info.className='explanation-info';
    const caption=document.createElement('summary');caption.textContent='ⓘ';caption.setAttribute('aria-label',t('plan.estimate_info'));
    const explanation=document.createElement('p');explanation.className='meta';explanation.textContent=t('plan.estimate_info');
    if(actual!==null)explanation.textContent+=` ${t('plan.remaining')}: ${num(Math.max(0,middle-actual),1)} kWh.`;
    info.append(caption,explanation);container.append(info);
  }
  container.onclick=event=>{const button=event.target.closest('[data-detail]');if(button) container.querySelector('.plan-detail').textContent=button.dataset.detail;};
}
