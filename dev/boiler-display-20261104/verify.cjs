// Fixture-only sensor-selection regression checks against an isolated frontend.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const b=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await b.newPage({serviceWorkers:'block'});
 await page.goto((process.env.HEC_BASE_URL||'http://127.0.0.1:8198')+'/index.html');
 const status={ui:{language:'cs',theme:'dark',animations:'off'},controller:{enabled:true},readers:{tng:{enabled:true,state:'ok',stale:false},tng_wire:{enabled:true,state:'ok',stale:false}}};
 const sample={status,sources:{tng:{sample_time:'2026-11-04T11:07:00+01:00',boiler_temperature:54.4,water_output_temperature:53.1,boiler_set_temperature:55,heating_set_temperature:42,room_temperature:21.6,boiler_on:true,heating_on:false},tng_wire:{sample_time:'2026-11-04T11:08:00+01:00',boiler_temperature:28.8,water_output_temperature:27.4,buffer_temperature:34.8,room_temperature:21.6,field_quality:{boiler_temperature:'photo_validated_provisional',water_output_temperature:'photo_validated_provisional',buffer_temperature:'photo_validated_provisional'}}}};
 const checks=await page.evaluate(async sample=>{
   const {thermalSnapshot,temperatureReading}=await import('/js/thermal-status.js?v=aku-20261104');
   const {heatpumpPanel}=await import('/js/heatpump-panel.js?v=aku-20261104');
   const now=new Date('2026-11-04T11:08:00+01:00'),checks=[];
   const ok=(test,name)=>{if(!test)throw Error(name);checks.push(name)};
   const reading=thermalSnapshot(sample,now);
   ok(reading.boiler===54.4&&reading.water===53.1,'reject plausible aliased passive boiler and outlet');
   ok(reading.buffer===34.8,'retain independent AKU sensor');
   ok(reading.timestamp===sample.sources.tng.sample_time,'do not relabel cloud reading with newer wire timestamp');
   ok(reading.timestamps.buffer_temperature===sample.sources.tng_wire.sample_time,'retain individual sample times');
   const stale=structuredClone(sample);stale.sources.tng.sample_time='2026-11-04T10:00:00+01:00';
   const old=thermalSnapshot(stale,now);
   ok(old.boiler===null&&old.water===null&&old.buffer===34.8,'stale cloud must not fall back to ambiguous wire candidates');
   const absent=structuredClone(sample);delete absent.sources.tng;
   ok(thermalSnapshot(absent,now).boiler===null,'missing cloud is unknown');
   const failed=structuredClone(sample);failed.status.stale_sources=['tng'];
   ok(thermalSnapshot(failed,now).boiler===null,'reader stale status respected');
   const noField=structuredClone(sample);delete noField.sources.tng.boiler_temperature;
   ok(thermalSnapshot(noField,now).boiler===null,'missing cloud field remains unknown');
   const low=structuredClone(sample);low.sources.tng.boiler_temperature=31.2;
   ok(thermalSnapshot(low,now).boiler===31.2,'legitimate cold cloud boiler is preserved');
   const invalid=structuredClone(sample);invalid.sources.tng_wire.field_quality.buffer_temperature='outside_verified_range';
   ok(thermalSnapshot(invalid,now).buffer===34.8,'AKU outside old reference range remains visible');
   invalid.sources.tng_wire.buffer_temperature=43.2;
   ok(thermalSnapshot(invalid,now).buffer===43.2,'owner example 43.2 C is visible');
   invalid.sources.tng_wire.buffer_temperature=29.7;
   ok(thermalSnapshot(invalid,now).buffer===29.7,'AKU below old reference range is visible');
   invalid.sources.tng_wire.sample_time='2026-11-04T10:00:00+01:00';
   ok(thermalSnapshot(invalid,now).buffer===null,'stale AKU stays unavailable');
   ok(!heatpumpPanel(stale,{},now).includes('28,8'),'detail panel shares the same source policy');
   ok(temperatureReading(sample,'boiler_temperature',now).origin==='cloud','source provenance retained internally');
   return checks;
 },sample);

 console.log(JSON.stringify({passed:true,checks},null,2));await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
