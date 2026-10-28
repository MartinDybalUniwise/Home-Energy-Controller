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
export function renderDayPlan(container, config, now = new Date()) {
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
      if (block.mode===mode && block.to-block.from>=90) button.textContent=`${num(block[field],0)}°`;
      lane.append(button);
    }
    const marker=document.createElement('span');marker.className='plan-now';marker.style.left=`${at/14.4}%`;marker.setAttribute('aria-hidden','true');lane.append(marker);container.append(lane);
  }
  const detail=document.createElement('p');detail.className='meta plan-detail';detail.setAttribute('aria-live','polite');
  const current=segments.find(b=>at>=b.from&&at<b.to);
  detail.textContent=`${t('plan.now')}: ${t(current?.mode==='boiler'?'entity.dhw':'entity.heatpump')} · ${t('plan.saved')}`;
  container.append(detail);
  container.onclick=event=>{const button=event.target.closest('[data-detail]');if(button) container.querySelector('.plan-detail').textContent=button.dataset.detail;};
}
