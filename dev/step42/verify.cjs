// Deterministic browser regression checks; all control data below are fixtures.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({serviceWorkers:'block'});
 const url=process.env.HEC_BASE_URL||'http://127.0.0.1:8192';
 await page.goto(url+'/index.html');
 const modelTests=await page.evaluate(async()=>{
   const {liveModel,gateState,savedSegments,commandEvents,renderControlLive}=await import('/js/control-plan.js?v=42');
   const now=new Date('2026-10-30T12:15:00+01:00');
   const config={tng:{enabled:true,write_enabled:true,heating:{enabled:true,default_temperature:42,date_overrides:{'2026-10-30':{schedule:[{from:'11:30',to:'13:30',temperature:35}]}}},boiler:{enabled:true,default_temperature:50},thermostat:{enabled:true,default_temperature:21.5,schedule:[{from:'12:00',to:'12:30',temperature:21.7}]},operation:{default_mode:'heating'},price_shift:{enabled:true}}};
   const current={sources:{tng:{timestamp:now.toISOString(),sample_time:now.toISOString(),write_enabled:true,heating_on:true,boiler_on:false,heating_set_temperature:42,boiler_set_temperature:50,price_shift:{phase:'comfort_veto',heating_temperature:42,room_target:21.5}}}};
   const status={readers:{tng:{enabled:true,state:'ok',stale:false}},controller:{enabled:false},goodwe_writer_diagnostics:{enabled:true}};
   const checks=[];const ok=(condition,name)=>{if(!condition)throw Error(name);checks.push(name)};
   const m=liveModel(current,status,config,now);
   ok(m.writes&&m.targets.heat===42&&m.saved.heat===35,'runtime veto overrides saved target');
   ok(m.targets.room===21.5,'runtime room target overrides thermostat schedule');
   const unified=structuredClone(status);
   unified.controller={planner:'unified',enabled:true,tng_write_enabled:true,goodwe_control_enabled:false,
     thermal_plan:{planned_at:now.toISOString(),mode:'boiler',heating_temperature:37,boiler_temperature:57,room_target:21.8,phase:'exclusive_mode'}};
   const unifiedModel=liveModel(current,unified,config,now);
   ok(unifiedModel.unified&&unifiedModel.mode==='boiler'&&unifiedModel.targets.heat===37&&unifiedModel.targets.boiler===57&&unifiedModel.targets.room===21.8,'unified controller plan is authoritative');
   unified.controller.enabled=false;
   const off=liveModel(current,unified,config,now);
   ok(!off.writes&&!off.plan&&off.targets.heat===undefined,'unified master disable hides old targets');
   unified.controller.enabled=true;
   unified.controller.thermal_plan.planned_at='2026-10-30T10:00:00+01:00';
   ok(!liveModel(current,unified,config,now).plan,'stale unified plan is not current');
   ok(savedSegments(config,now).some(s=>s.from===720&&s.to===750),'thermostat boundaries included');
   const disabled=structuredClone(config);disabled.tng.write_enabled=false;
   ok(!liveModel(current,status,disabled,now).writes,'write permission respected');
   const bad=structuredClone(status);bad.readers.tng.stale=true;
   const stale=liveModel(current,bad,config,now);
   ok(!stale.fresh&&stale.targets.heat===undefined&&!stale.writes,'stale source never looks active');
   const aged=structuredClone(current);aged.sources.tng.sample_time='2026-10-30T10:00:00+01:00';
   ok(!liveModel(aged,status,config,now).fresh,'sample age checked independently of polling');
   ok(!liveModel(current,{},config,now).fresh,'missing status not assumed healthy');
   const gate={last_post_at:'2026-10-30T12:10:00+01:00',awaiting_confirmation:true,seen_pending:false};
   ok(gateState(gate,now).phase==='waiting_true','awaiting acceptance');
   gate.seen_pending=true;ok(gateState(gate,now).phase==='waiting_false','awaiting completion');
   gate.awaiting_confirmation=false;ok(gateState(gate,now).remaining===600&&gateState(gate,now).phase==='guard','900 second guard retained');
   ok(gateState({...gate,last_post_at:'2026-10-30T11:00:00+01:00'},now).phase==='confirmed','completed confirmation gate');
   ok(gateState(undefined,now).phase==='unknown','missing gate is unknown');
   const commands=[{command_id:'a',timestamp:'2026-10-30T11:00:00+01:00',phase:'requested'},{command_id:'a',timestamp:'2026-10-30T11:00:01+01:00',phase:'sent'},{timestamp:'2026-10-29T11:00:01+01:00',phase:'sent'}];
   ok(commandEvents(commands,{},now).length===1&&commandEvents(commands,{},now)[0].phase==='sent','command lifecycle grouped and Prague date filtered');
   const missing=renderControlLive({failures:['current','status','config'],decisions:{decisions:[{timestamp:'invalid'}]}},now);
   ok(missing.includes('role="alert"')&&!missing.includes('NaN'),'failed endpoints visible and malformed date safe');
   const injection=renderControlLive({current,status,config,commands:{rows:[{timestamp:now.toISOString(),phase:'sent',kind:'<img src=x>',requested:{DayTemperature:21.5}}]}},now);
   ok(!injection.includes('<img src=x>'),'event values escaped');
   return checks;
 });

 console.log(JSON.stringify({passed:true,checks:modelTests},null,2));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
