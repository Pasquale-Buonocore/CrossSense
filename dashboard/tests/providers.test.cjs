const {readFileSync}=require('node:fs');
const {runInNewContext}=require('node:vm');
const assert=require('node:assert/strict');
const source=readFileSync(require('node:path').join(__dirname,'../static/providers.js'),'utf8');
const {DemoProvider,HardwareProvider}=runInNewContext(source+'\n({DemoProvider,HardwareProvider})');
const demo=new DemoProvider();
assert.equal(demo.request('pedestrian','r1').status,'accepted');
demo.request('pedestrian','r1');assert.equal(demo.snapshot().pending.length,1);
demo.setScenario('offline');const before=demo.snapshot().seq;demo.tick();assert.equal(demo.snapshot().seq,before);assert.equal(demo.request('pedestrian','r2').status,'rejected');
demo.setScenario('normal');assert.equal(demo.snapshot().pending.length,0);
demo.setScenario('stopped');for(let i=0;i<60;i++)demo.tick();assert.equal(demo.snapshot().phase,3);assert.equal(demo.snapshot().elapsed,0);
const hardware=new HardwareProvider(()=>{},null);assert.equal(hardware.snapshot().completed,null);for(let i=0;i<10;i++)hardware.tick();assert.equal(hardware.snapshot().seq,0);
const fresh=new DemoProvider();assert.equal(fresh.snapshot().completed,0);
console.log('Provider checks passed: deduplication, offline, clearance protection, hardware isolation.');
const outputsDemo=new DemoProvider();
assert.equal(outputsDemo.snapshot().outputs.vehicle,'green');
assert.equal(outputsDemo.snapshot().outputs.pedestrian,'red');
for(let i=0;i<18;i++)outputsDemo.tick();
assert.equal(outputsDemo.snapshot().outputs.vehicle,'amber');
for(let i=0;i<3;i++)outputsDemo.tick();
assert.equal(outputsDemo.snapshot().outputs.vehicle,'red');
assert.equal(outputsDemo.snapshot().outputs.pedestrian,'green');
outputsDemo.setScenario('stopped');for(let i=0;i<20;i++)outputsDemo.tick();
assert.equal(outputsDemo.snapshot().outputs.vehicle,'red');
assert.equal(outputsDemo.snapshot().outputs.pedestrian,'red');
outputsDemo.setScenario('offline');assert.equal(outputsDemo.snapshot().outputs,null);
assert.equal(hardware.snapshot().outputs,null);
console.log('Commanded outputs checked for all phases and missing telemetry.');

(async()=>{
assert.equal((await hardware.request('pedestrian','r3')).status,'rejected');
let now=0;
const live=new HardwareProvider(()=>{},async()=>({ok:true,json:async()=>({connected:true,age_ms:0,state:{phase:'PED_CLEARANCE',vehicle_light:'RED',pedestrian_light:'RED',remaining_ms:null,applied_frame:42}})}),()=>now);
await live.tick();assert.equal(live.snapshot().outputs.vehicle,'red');assert.equal(live.snapshot().remaining,null);
now=1000;assert.equal(live.snapshot().outputs,null);assert.equal((await live.request('pedestrian','x')).status,'rejected');
console.log('Hardware freshness and unavailable countdown checked.');
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
