// Read-only projection of the unified plan; never computes prices or sends commands.
import {t,num,time} from './i18n.js';

const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=(key,params)=>t(`battery_plan.${key}`,params);
const minute=value=>/^([01]\d|2[0-3]):[0-5]\d$/.test(value||'')?Number(value.slice(0,2))*60+Number(value.slice(3)):null;
const pct=value=>typeof value==='number'&&Number.isFinite(value)?`${num(value,0)} %`:'—';

export function batteryModel(status,day,atClock,now=new Date()){
  const ctrl=status?.controller||{},plan=ctrl.battery_plan,at=minute(atClock);
  const age=(+now-Date.parse(plan?.timestamp))/1000;
  const fresh=!!plan&&plan.date===day&&age>=-30&&age<=180;
  const known=typeof ctrl.enabled==='boolean'&&typeof ctrl.goodwe_control_enabled==='boolean';
  const enabled=ctrl.enabled===true&&ctrl.goodwe_control_enabled===true&&
    (ctrl.rules||[]).some(rule=>rule.name==='battery_economic'&&rule.enabled===true);
  const windows=fresh&&enabled&&plan.prices_valid===true&&at!==null?(plan.windows||[]).flatMap(window=>{
    const from=minute(window.from),to=minute(window.to);
    return from!==null&&to!==null&&from<to&&to>at?[{...window,start:Math.max(from,at),end:to}]:[];
  }):[];
  const failed=plan?.last_command?.applied===false;
  const phase=!known?'unavailable':!enabled?'disabled':!fresh?'unavailable':failed?'write_failed':plan.phase;
  return {plan:fresh?plan:null,fresh,enabled,windows,phase,
    drawable:fresh&&enabled&&plan.prices_valid===true&&plan.data_valid===true&&!failed&&
      !['safe_mode','external_mode'].includes(plan.phase)};
}

export function renderBatteryPlan(status,day,atClock,now=new Date()){
  const m=batteryModel(status,day,atClock,now),p=m.plan;
  const metric=(label,value)=>`<div class="control-plan-metric"><dt>${esc(tr(label))}</dt><dd>${value}</dd></div>`;
  const phases=['self_consumption','charge','hold','release','solar','safe_mode','external_mode','disabled','unavailable','write_failed'];
  const phase=phases.includes(m.phase)?m.phase:'unavailable';
  return `<section class="panel control-plan-status battery-plan" data-plan-source="unified-controller">
    <h2>${tr('title')}</h2><span class="pill" data-level="${m.drawable?'ok':'warning'}">${esc(tr(`phase_${phase}`))}</span>
    <p class="meta">${tr('authority')}${p?` · ${esc(p.date)} · ${esc(time(new Date(p.timestamp),{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit'}))}`:''}</p>
    ${p?`<dl class="control-plan-metrics">${metric('grid_target',pct(p.grid_target_soc_pct))}${metric('power_limit',pct(p.charge_power_limit_pct))}${metric('reserve',pct(p.minimum_soc_pct))}${metric('actual_soc',pct(p.actual_soc))}</dl>`:''}
    ${m.windows.length?`<div class="table-wrap"><table class="data"><thead><tr><th>${tr('time')}</th><th>${tr('action')}</th><th>${tr('price')}</th></tr></thead><tbody>${m.windows.map(w=>`<tr><td>${esc(w.from)}–${esc(w.to)}</td><td>${tr('conditional_charge')}</td><td>${typeof w.max_price==='number'?`${num(w.max_price,2)} ${t('unit.czk_kwh')}`:'—'}</td></tr>`).join('')}</tbody></table></div>`:`<p>${esc(tr(m.enabled&&m.fresh?'no_windows':'unavailable_note'))}</p>`}
    <details class="explanation-info"><summary>ⓘ</summary><p>${tr('conditions')}</p><p>${tr('measured_note')}</p></details>
  </section>`;
}
