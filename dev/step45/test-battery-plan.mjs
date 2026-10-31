import assert from 'node:assert/strict';
import {batteryModel,renderBatteryPlan} from '../hec/web/frontend/js/battery-plan.js';
import {timeline,chartRange} from '../hec/web/frontend/js/today-chart.js';

const now=new Date('2026-10-31T12:45:00+01:00');
const status={controller:{enabled:true,goodwe_control_enabled:true,
  rules:[{name:'battery_economic',enabled:true}],battery_plan:{
    timestamp:now.toISOString(),date:'2026-10-31',phase:'charge',prices_valid:true,data_valid:true,
    grid_target_soc_pct:60,minimum_soc_pct:20,charge_power_limit_pct:20,actual_soc:10,
    windows:[{from:'04:00',to:'06:30',max_price:7},{from:'12:30',to:'15:30',max_price:7.043}]}}};
const original=JSON.stringify(status);
const model=s=>batteryModel(s,'2026-10-31','12:45',now);
assert.equal(model(status).windows.length,1);
assert.equal(model(status).windows[0].start,765);
assert.equal(model(status).windows[0].end,930);
assert.equal(JSON.stringify(status),original);
const html=renderBatteryPlan(status,'2026-10-31','12:45',now);
assert.ok(html.includes('12:30–15:30')&&!html.includes('04:00'));
assert.ok(!/<(button|input|form)\b/.test(html));
const svg=s=>timeline([],[],[],chartRange(1,now),now,300000,1200,{},s);
assert.equal((svg(status).match(/class="timeline-plan-block timeline-battery-block"/g)||[]).length,1);
for(const change of [
  s=>s.controller.enabled=false,
  s=>s.controller.goodwe_control_enabled=false,
  s=>s.controller.rules[0].enabled=false,
  s=>s.controller.battery_plan.timestamp='2026-10-31T08:00:00+01:00',
  s=>s.controller.battery_plan.date='2026-10-30',
  s=>s.controller.battery_plan.data_valid=false,
  s=>s.controller.battery_plan.prices_valid=false,
  s=>s.controller.battery_plan.phase='safe_mode',
  s=>s.controller.battery_plan.last_command={applied:false},
]){
  const changed=structuredClone(status);change(changed);
  assert.equal(model(changed).drawable,false);
  assert.ok(!svg(changed).includes('timeline-battery-block'));
}
const finished=structuredClone(status);finished.controller.battery_plan.windows=[{from:'04:00',to:'06:30'}];
assert.equal(model(finished).windows.length,0);
console.log('Battery plan projection: current, elapsed, stale, disabled, failed and protected states passed');
