const {readFileSync}=require('node:fs');
const {runInNewContext}=require('node:vm');
const assert=require('node:assert/strict');
const source=readFileSync(require('node:path').join(__dirname,'../static/providers.js'),'utf8');
const {HardwareProvider}=runInNewContext(source+'\n({HardwareProvider})');
assert.doesNotMatch(source,/class DemoProvider/);
const hardware=new HardwareProvider(()=>{},null);assert.equal(hardware.snapshot().completed,null);for(let i=0;i<10;i++)hardware.tick();assert.equal(hardware.snapshot().seq,0);
assert.equal(hardware.snapshot().outputs,null);
console.log('Controller provider keeps missing telemetry unavailable.');

(async()=>{
assert.equal((await hardware.request('pedestrian','r3')).status,'rejected');
let now=0;
const live=new HardwareProvider(()=>{},async()=>({ok:true,json:async()=>({connected:true,age_ms:0,state:{phase:'PED_CLEARANCE',vehicle_light:'RED',pedestrian_light:'RED',remaining_ms:null,applied_frame:42}})}),()=>now);
await live.tick();assert.equal(live.snapshot().outputs.vehicle,'red');assert.equal(live.snapshot().remaining,null);
now=3999;assert.equal(live.snapshot().scenario,'hardware');assert.equal(live.snapshot().outputs.vehicle,'red');
now=4000;assert.equal(live.snapshot().scenario,'unstable');assert.equal(live.snapshot().outputs.vehicle,'red');assert.equal((await live.request('pedestrian','x')).status,'rejected');
now=9999;assert.equal(live.snapshot().scenario,'unstable');
now=10000;assert.equal(live.snapshot().scenario,'offline');assert.equal(live.snapshot().outputs,null);
let fail=true;
const resilient=new HardwareProvider(()=>{},async()=>{if(fail)throw Error('rete');return {ok:true,json:async()=>({connected:true,age_ms:0,state:{phase:'PED_CLEARANCE',vehicle_light:'RED',pedestrian_light:'RED',remaining_ms:null,applied_frame:7}})};},()=>now);
fail=false;await resilient.tick();fail=true;now+=200;await resilient.tick();assert.equal(resilient.snapshot().scenario,'hardware');assert.equal(resilient.snapshot().seq,7);
resilient.transport=async()=>({ok:true,json:async()=>({connected:false,age_ms:1200,error:'timeout',state:null})});now+=200;await resilient.tick();assert.equal(resilient.snapshot().scenario,'hardware');assert.equal(resilient.snapshot().seq,7);
console.log('Hardware telemetry tolerates transient network failures, then degrades to unstable and offline.');
// Exercise the real renderer for all three indicators with MCU telemetry.
const signalsSource=readFileSync(require('node:path').join(__dirname,'../static/signals.js'),'utf8');
const {TrafficSignals}=runInNewContext(signalsSource.replace('const trafficSignals=new TrafficSignals();','')+'\n({TrafficSignals})');
function node(){
  const lamps=['red','amber','green'].map(color=>({dataset:{light:color},on:false,classList:{toggle(key,on){lamps.find(l=>l.dataset.light===color).on=on;}}}));
  const label={textContent:''};
  return {lamps,label,unknown:false,classList:{toggle(key,value){this.value=value;}},querySelectorAll:()=>lamps,querySelector:()=>label,setAttribute(){}};
}
const view={nodes:{'ped-left':node(),'ped-right':node(),vehicles:node()}};
const states=[['VEHICLE_GREEN','GREEN','RED'],['VEHICLE_YELLOW','YELLOW','RED'],['ALL_RED_TO_PED','RED','RED'],['PED_GREEN','RED','GREEN'],['PED_CLEARANCE','RED','RED'],['ALL_RED_TO_VEH','RED','RED'],['FAULT','RED','RED']];
for(const [phase,vehicle_light,pedestrian_light]of states){
  const provider=new HardwareProvider(()=>{},async()=>({ok:true,json:async()=>({connected:true,age_ms:0,state:{phase,vehicle_light,pedestrian_light,remaining_ms:null,applied_frame:1}})}),()=>0);
  await provider.tick();TrafficSignals.prototype.render.call(view,provider.snapshot().outputs);
  const on=id=>view.nodes[id].lamps.filter(l=>l.on).map(l=>l.dataset.light).join(',');
  const colors={GREEN:'green',YELLOW:'amber',RED:'red'};
  assert.equal(on('vehicles'),colors[vehicle_light]);
  assert.equal(on('ped-left'),colors[pedestrian_light]);
  assert.equal(on('ped-right'),colors[pedestrian_light]);
}
TrafficSignals.prototype.render.call(view,null);
for(const n of Object.values(view.nodes))assert.equal(n.lamps.filter(l=>l.on).length,0);
console.log('Bridge telemetry mapped to vehicle and both pedestrian dashboard indicators for every cycle phase.');
})().catch(e=>{console.error(e);process.exitCode=1;});
