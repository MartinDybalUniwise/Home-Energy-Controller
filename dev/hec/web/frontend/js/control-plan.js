import {t,num,time} from './i18n.js';
import {finite,source,energySnapshot,heatpumpReportedPower,heatpumpQuality} from './telemetry.js';
import {siteDate,siteClock,siteDateTime} from './today-chart.js?v=41';
import {patchDOM} from './patch-dom.js?v=36';

const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=(key,params)=>t(`control_live.${key}`,params);
const temp=value=>finite(value)===null?'—':`${num(value,1)} °C`;
const kw=value=>finite(value)===null?'—':`${num(value/1000,2)} kW`;
const clock=minute=>`${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`;
const minute=value=>/^([01]\d|2[0-3]):[0-5]\d$/.test(value||'')?Number(value.slice(0,2))*60+Number(value.slice(3)):value==='24:00'?1440:null;
const effective=(section,date)=>({...section,...section?.date_overrides?.[date]});
const at=(section,when,key,fallback)=>{
  let result=fallback;
  for(const block of section?.schedule||[]){
    const from=minute(block.from),to=minute(block.to);
    if(from===null||to===null)continue;
    if(from<to?when>=from&&when<to:when>=from||when<to)result=block[key];
  }
  return result;
};
const tone=(text,level='neutral')=>`<span class="pill" data-level="${level}">${esc(text)}</span>`;
const metric=(label,value)=>`<div class="control-plan-metric"><dt>${esc(label)}</dt><dd>${value}</dd></div>`;
const card=(id,title,body)=>`<article class="control-plan-device" data-process="${id}"><h3>${esc(title)}</h3>${body}</article>`;

export function savedSegments(config,now=new Date()){
  const date=siteDate(now),tng=config?.tng;
  if(!tng)return [];
  const sections=Object.fromEntries(['heating','boiler','thermostat','operation'].map(key=>[key,effective(tng[key],date)]));
  const edges=new Set([0,1440]);
  for(const section of Object.values(sections))for(const block of section.schedule||[]){
    for(const value of [block.from,block.to]){const m=minute(value);if(m!==null)edges.add(m);}
  }
  const sorted=[...edges].sort((a,b)=>a-b);
  return sorted.slice(0,-1).map((from,i)=>({from,to:sorted[i+1],
    mode:at(sections.operation,from,'mode',sections.operation.default_mode||'unknown'),
    heat:sections.heating.enabled===true?at(sections.heating,from,'temperature',sections.heating.default_temperature):null,
    boiler:sections.boiler.enabled===true?at(sections.boiler,from,'temperature',sections.boiler.default_temperature):null,
    room:sections.thermostat.enabled===true?at(sections.thermostat,from,'temperature',sections.thermostat.default_temperature):null}));
}

export function gateState(gate,now=new Date(),minimum=900,pending=false){
  if(!gate)return {phase:'unknown',remaining:null};
  const stamp=Date.parse(gate.last_post_at);
  const remaining=Number.isFinite(stamp)?Math.max(0,Math.ceil((stamp+Math.max(900,minimum)*1000-+now)/1000)):0;
  return {phase:gate.awaiting_confirmation===true?(gate.seen_pending?'waiting_false':'waiting_true'):
    pending?'pending':remaining>0?'guard':gate.last_post_at?'confirmed':'no_command',remaining};
}

export function liveModel(current,status,config,now=new Date()){
  const raw=current?.sources?.tng||{},reader=status?.readers?.tng;
  const age=(+now-Date.parse(raw.sample_time||raw.timestamp))/1000;
  const fresh=!!reader&&reader.enabled===true&&!reader.stale&&reader.state==='ok'&&!reader.last_error&&age>=-60&&age<=900;
  const tng=fresh?raw:{};
  const segments=savedSegments(config,now),atMinute=minute(siteClock(now));
  const saved=segments.find(s=>atMinute>=s.from&&atMinute<s.to);
  const controller=status?.controller||{},unified=controller.planner==='unified';
  const enabled=unified?controller.enabled:config?.tng?.enabled;
  const writes=fresh&&enabled===true&&config?.tng?.write_enabled===true&&tng.write_enabled===true&&(!unified||controller.tng_write_enabled===true);
  const comfort=tng.comfort_guard_active===true;
  let mode=fresh&&saved?(comfort&&saved.mode!=='off'?'heating':saved.mode):'unknown';
  if((mode==='heating'&&config?.tng?.heating?.enabled!==true)||(mode==='boiler'&&config?.tng?.boiler?.enabled!==true))mode='off';
  const shift=tng.price_shift;
  // Runtime vetoes and solar overrides come from the active process, not an estimate.
  let targets=fresh&&saved?{
    heat:config?.tng?.heating?.enabled===true?(mode==='heating'?(comfort?42:shift?.heating_temperature??saved.heat):tng.heating_set_temperature):null,
    boiler:config?.tng?.boiler?.enabled===true?(mode==='boiler'?saved.boiler:tng.boiler_set_temperature):null,
    room:config?.tng?.thermostat?.enabled===true?(comfort?Math.max(21.5,shift?.room_target??saved.room??21.5):shift?.room_target??saved.room):null}:{};
  const candidate=controller.thermal_plan,planAge=(+now-Date.parse(candidate?.planned_at))/1000;
  const plan=unified&&fresh&&enabled===true&&planAge>=-60&&planAge<=900?candidate:null;
  if(unified){
    mode=plan?.mode||'unknown';
    targets=plan?{heat:config?.tng?.heating?.enabled===true?plan.heating_temperature:null,
      boiler:config?.tng?.boiler?.enabled===true?plan.boiler_temperature:null,
      room:config?.tng?.thermostat?.enabled===true?plan.room_target:null}:{};
  }
  return {fresh,tng,reader,segments,saved,writes,enabled,comfort,mode,shift,targets,unified,plan};
}

function requestText(row){
  const r=row.requested||{},parts=[];
  if(typeof r.HeatSet?.Heat==='boolean')parts.push(`${t('entity.heating')}: ${tr(r.HeatSet.Heat?'on':'off')}`);
  if(typeof r.BoilerSet?.Boiler==='boolean')parts.push(`${t('entity.dhw')}: ${tr(r.BoilerSet.Boiler?'on':'off')}`);
  for(const [label,keys] of [['heat',['HeatTemp_Const','heating_temperature']],['boiler',['BoilerTemp','boiler_temperature']],['room',['DayTemperature','day_temperature']]]){
    const value=keys.map(k=>r[k]).find(v=>finite(v)!==null);
    if(value!==undefined)parts.push(`${tr(label)}: ${temp(value)}`);
  }
  if(row.effective)parts.push(tr(`phase_${row.effective.phase}`));
  if(row.plan)parts.push(`${tr(`mode_${row.plan.mode||'unknown'}`)} · ${tr('heat')}: ${temp(row.plan.heating_temperature)} · ${tr('boiler')}: ${temp(row.plan.boiler_temperature)} · ${tr('room')}: ${temp(row.plan.room_target)}`);
  if(row.phase==='comfort_guard')parts.push(tr(row.active?'comfort_on':'comfort_off'));
  return parts.join(' · ')||tr('no_parameters');
}

export function commandEvents(rows,current,now=new Date()){
  const events=[...(rows||[])];
  const latest=current?.sources?.tng_command;
  if(latest&&!events.some(r=>r.command_id===latest.command_id&&r.phase===latest.phase&&r.timestamp===latest.timestamp))events.push(latest);
  const grouped=new Map();
  events.filter(r=>Number.isFinite(Date.parse(r.timestamp))&&siteDate(new Date(r.timestamp))===siteDate(now))
    .sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp)).forEach((row,i)=>grouped.set(row.command_id||`event-${i}`,row));
  return [...grouped.values()].sort((a,b)=>Date.parse(b.timestamp)-Date.parse(a.timestamp)).slice(0,16);
}

function eventList(events){
  return events.length?`<ol class="control-live-events">${events.map(row=>{
    const phase=['requested','sent','failed','dry_run','confirmed','confirmed_cycle','confirmed_recovery','pending_seen','price_shift','price_plan_saved','comfort_guard','resolved_plan'].includes(row.phase)?row.phase:'other';
    return `<li><details><summary><time>${esc(time(new Date(row.timestamp),{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit'}))}</time>${tone(tr(`event_${phase}`),phase==='failed'?'critical':phase.startsWith('confirmed')?'ok':'neutral')}<span>${esc(requestText(row))}</span></summary><p class="meta">${esc(siteDateTime(row.timestamp))} · ${esc(row.kind||tr('planner'))}</p>${row.error?`<p>${esc(String(row.error))}</p>`:''}</details></li>`;
  }).join('')}</ol>`:`<p class="notice">${tr('no_events')}</p>`;
}

export function renderControlLive({current={},status={},config={},commands={},decisions={},prediction={},prices={},failures=[]},now=new Date()){
  const m=liveModel(current,status,config,now),s=current.sources||{},ctrl=status.controller||{};
  const writer=status.goodwe_writer_diagnostics||{},goodwe=energySnapshot({...current,status});
  const shelly=source({...current,status},'shelly'),power=heatpumpReportedPower(shelly),quality=heatpumpQuality(shelly);
  const gate=s.tng_gate||{},minimum=Math.max(900,Number(config?.tng?.minimum_change_interval_seconds)||900);
  const resolved=(decisions.decisions||[]).filter(d=>d.action==='plan_tng'&&d.value&&typeof d.value==='object').map(d=>({timestamp:d.timestamp,phase:'resolved_plan',plan:d.value,kind:tr('unified_controller')}));
  const events=commandEvents([...(commands.rows||[]),...resolved],current,now);
  const future=m.segments.filter(block=>block.to>minute(siteClock(now)));
  const phase=m.fresh?(m.unified?m.plan?.phase:m.shift?.phase):null;
  const shiftLabel=m.unified&&!m.enabled?tr('disabled'):phase?tr(`phase_${phase}`):!m.fresh||m.unified?tr('unavailable'):tr(config?.tng?.price_shift?.enabled?'manual_plan':'disabled');
  const processState=!m.reader||typeof m.enabled!=='boolean'?tr('unavailable'):!m.reader.enabled||!m.enabled?tr('disabled'):!m.fresh?tr('stale'):m.writes?tr('running'):tr('simulation');
  const observedMode=typeof m.tng.heating_on!=='boolean'||typeof m.tng.boiler_on!=='boolean'?'unknown':m.tng.heating_on&&m.tng.boiler_on?'conflict':m.tng.boiler_on?'boiler':m.tng.heating_on?'heating':'off';
  const tngCards=card('tng',tr(m.unified?'tng_adapter':'tng_process'),`${tone(processState,m.writes?'ok':'warning')}<p>${tr(m.unified?'adapter_role':'tng_role')}</p><p class="meta">${tr('last_cycle')}: ${m.reader?.last_success?esc(siteDateTime(m.reader.last_success)):'—'}</p>`)
    +card('price',tr('planner'),`${tone(shiftLabel,['preheat','solar_preheat','coast','normal'].includes(phase)?'ok':'warning')}<p>${tr('phase_note')}</p><dl class="control-plan-metrics">${metric(tr('effective_heat'),temp(m.targets.heat))}${metric(tr('effective_room'),temp(m.targets.room))}</dl>`)
    +card('controller',tr(m.unified?'unified_controller':'general_controller'),`${tone(ctrl.enabled===true?tr(ctrl.safe_mode?'safe':'running'):ctrl.enabled===false?tr('disabled'):tr('unavailable'),ctrl.enabled&&!ctrl.safe_mode?'ok':'neutral')}<p>${tr(m.unified?'unified_role':'controller_role')}</p><p class="meta">${tr('last_cycle')}: ${ctrl.last_run?esc(siteDateTime(ctrl.last_run)):'—'}</p>`)
    +card('battery',tr('battery_control'),`${tone(writer.enabled===true?tr('write_permitted'):writer.enabled===false?tr('write_disabled'):tr('unavailable'),writer.enabled?'ok':'neutral')}<p>${tr(m.unified?ctrl.goodwe_control_enabled?'battery_auto':'battery_unified_standby':ctrl.enabled?'battery_auto':'battery_standby')}</p><p class="meta">${tr('last_write')}: ${writer.last_write?.timestamp?esc(siteDateTime(writer.last_write.timestamp)):'—'}</p>${writer.last_error?`<p class="notice error">${esc(String(writer.last_error))}</p>`:''}`);
  const gateCards=['basic','thermostat'].map(kind=>{
    const item=gate[kind],state=gateState(item,now,minimum,kind==='basic'&&m.tng.pending_change===true);
    return card(`gate-${kind}`,tr(`gate_${kind}`),`${tone(m.fresh?tr(`gate_${state.phase}`):tr('unavailable'),m.fresh&&['confirmed','no_command'].includes(state.phase)?'ok':'warning')}<dl class="control-plan-metrics">${metric(tr('last_sent'),item?.last_post_at?esc(siteDateTime(item.last_post_at)):'—')}${metric(tr('wait_remaining'),state.remaining===null?'—':`${num(state.remaining,0)} s`)}</dl>`);
  }).join('');
  const todayForecast=(prediction.days||[]).find(day=>day.date===siteDate(now));
  const pricePeriods=prices.today?.date===siteDate(now)?(prices.today.periods||[]):[];
  const atClock=siteClock(now),price=pricePeriods.find(p=>p.start<=atClock&&atClock<p.end);
  return `<div class="control-plan-page control-live-page">
    <header class="control-plan-header"><div><span class="section-tab">${t('control_plan.title')}</span><p class="meta">${tr('subtitle')}</p></div><span id="control-plan-updated" class="meta">${tr('updated')}: ${esc(siteClock(now))}</span></header>
    ${failures.length?`<p class="notice error" role="alert">${tr('partial')}: ${failures.map(key=>esc(tr(`source_${key}`))).join(', ')}</p>`:''}
    <section class="panel control-plan-status"><h2>${tr('processes')}</h2><div class="control-live-processes">${tngCards}</div></section>
    <section class="panel control-plan-status"><h2>${tr('now')}</h2><div class="control-live-processes">
      ${card('effective',tr('effective'),`<dl class="control-plan-metrics">${metric(tr('mode'),esc(tr(`mode_${m.mode}`)))}${metric(tr('heat'),temp(m.targets.heat))}${metric(tr('boiler'),temp(m.targets.boiler))}${metric(tr('room'),temp(m.targets.room))}</dl><p class="meta">${tr(m.writes?'effective_note':'effective_disabled')}</p>`)}
      ${card('observed',tr('observed'),`<dl class="control-plan-metrics">${metric(tr('mode'),esc(tr(`mode_${observedMode}`)))}${metric(tr('reported_heat'),temp(m.tng.heating_set_temperature))}${metric(tr('reported_boiler'),temp(m.tng.boiler_set_temperature))}${metric(t('entity.room'),temp(m.tng.room_temperature))}${metric(t('entity.dhw'),temp(m.tng.boiler_temperature))}</dl><p class="meta">${tr('measurement')}: ${m.tng.sample_time?esc(siteDateTime(m.tng.sample_time)):'—'}</p>`)}
      ${card('energy',tr('energy'),`<dl class="control-plan-metrics">${metric(t('entity.pv'),kw(goodwe.pv_w))}${metric(t('entity.house'),kw(goodwe.house_w))}${metric(t('entity.grid_import'),kw(goodwe.grid_import_w))}${metric(t('entity.grid_export'),kw(goodwe.grid_export_w))}${metric(t('entity.battery_soc'),finite(goodwe.battery_soc)===null?'—':`${num(goodwe.battery_soc,0)} %`)}${metric(t('entity.heatpump'),kw(power))}</dl>${power!==null&&quality!=='valid'?`<p class="meta">${esc(t('meter.partial_phase'))}</p>`:''}`)}
    </div></section>
    <section class="panel control-plan-status"><h2>${tr('gates')}</h2><div class="control-live-gates">${gateCards}</div><details class="explanation-info"><summary>ⓘ</summary><p>${tr('gate_note',{seconds:minimum})}</p></details></section>
    <section class="panel control-plan-status"><h2>${tr('schedule')}</h2><p class="meta">${tr('saved_note')}</p>${future.length?`<div class="table-wrap"><table class="data control-live-schedule"><thead><tr><th>${tr('time')}</th><th>${tr('mode')}</th><th>${tr('heat')}</th><th>${tr('boiler')}</th><th>${tr('room')}</th></tr></thead><tbody>${future.map(block=>`<tr ${block===m.saved?'aria-current="time"':''}><td>${clock(block.from)}–${clock(block.to)} ${block===m.saved?`<span class="meta">${tr('current_window')}</span>`:''}</td><td>${esc(tr(`mode_${block.mode}`))}</td><td>${block.mode==='heating'?temp(block.heat):'—'}</td><td>${block.mode==='boiler'?temp(block.boiler):'—'}</td><td>${temp(block.room)}</td></tr>`).join('')}</tbody></table></div>`:`<p>${tr('no_plan')}</p>`}</section>
    <section class="panel control-plan-status"><h2>${tr('events')}</h2>${eventList(events)}<details class="explanation-info"><summary>${tr('controller_decisions')} (${(decisions.decisions||[]).filter(d=>Number.isFinite(Date.parse(d.timestamp))&&siteDate(new Date(d.timestamp))===siteDate(now)).length})</summary><p>${tr(m.unified?'unified_role':'controller_role')}</p>${(decisions.decisions||[]).filter(d=>Number.isFinite(Date.parse(d.timestamp))&&siteDate(new Date(d.timestamp))===siteDate(now)).slice(-8).reverse().map(d=>`<p>${esc(siteDateTime(d.timestamp))} · ${esc(d.action==='plan_tng'?requestText({plan:d.value}):d.action||d.rule)} · ${esc(t(d.reason_key,d.reason_params))} · ${esc(d.action==='plan_tng'?tr('plan_only'):t(d.applied?'control_plan.applied':'control_plan.not_applied'))}</p>`).join('')}</details></section>
    <section class="panel control-plan-status"><h2>${tr('outlook')}</h2><div class="control-live-gates">${card('price-now',t('entity.price'),finite(price?.price_total_czk_kwh)===null?'—':`${num(price.price_total_czk_kwh,2)} ${t('unit.czk_kwh')}`)}${card('forecast',tr('today_estimate'),`<dl class="control-plan-metrics">${metric(t('entity.pv'),finite(todayForecast?.forecast_pv?.value??todayForecast?.pv_kwh)===null?'—':`${num(todayForecast.forecast_pv?.value??todayForecast.pv_kwh,1)} kWh`)}${metric(t('entity.house'),finite(todayForecast?.forecast_consumption?.value??todayForecast?.consumption_kwh)===null?'—':`${num(todayForecast.forecast_consumption?.value??todayForecast.consumption_kwh,1)} kWh`)}</dl>`)}</div></section>
  </div>`;
}

const requests=new WeakMap();
export async function controlPlan(view,{api,state}){
  const ticket={};requests.set(view,ticket);
  const options={signal:AbortSignal.timeout(8000)};
  const calls={current:()=>api.current({fast:1},options),status:()=>api.status(options),config:()=>api.config(options),
    commands:()=>api.logs('tng_commands',{day:siteDate()},options),decisions:()=>api.decisions(1,options),prediction:()=>api.prediction(options),prices:()=>api.prices(options)};
  const keys=Object.keys(calls),results=await Promise.allSettled(keys.map(key=>calls[key]()));
  if(requests.get(view)!==ticket||(state&&state.page!=='control-plan'))return;
  const data={failures:[]};
  results.forEach((result,i)=>{if(result.status==='fulfilled')data[keys[i]]=keys[i]==='config'?result.value.config:result.value;else data.failures.push(keys[i]);});
  const fresh=document.createElement('div');fresh.innerHTML=renderControlLive(data);
  const existing=view.querySelector('.control-live-page');
  if(existing)patchDOM(existing,fresh.firstElementChild);else view.replaceChildren(fresh.firstElementChild);
}
