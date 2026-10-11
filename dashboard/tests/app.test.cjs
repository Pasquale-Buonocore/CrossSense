const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {runInNewContext}=require('node:vm');
const assert=require('node:assert/strict');
const source=readFileSync(join(__dirname,'../static/app.js'),'utf8');
const providers=readFileSync(join(__dirname,'../static/providers.js'),'utf8');
const html=readFileSync(join(__dirname,'../static/index.html'),'utf8');
assert.match(html,/<option value="replay">Replay<\/option>/);
assert.match(html,/<option id="mode-camera" value="camera">Telecamera<\/option>/);
assert.doesNotMatch(html,/value="demo"|id="scenario"|id="pause"/);
function node(){return {textContent:'',value:'',hidden:false,disabled:false,style:{},children:[],handlers:{},addEventListener(type,fn){this.handlers[type]=fn;},replaceChildren(){this.children=[];},append(){},prepend(child){this.children.unshift(child);},remove(){},className:''};}
const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,node());return elements.get(id);};
const requests=[node()];requests[0].dataset={request:'pedestrian'};
let selected='camera',requestId=null;
const context={document:{getElementById:get,createElement:node,querySelectorAll:()=>requests},location:{host:'board.test:8080'},Date,console,setInterval(){},trafficSignals:{render(outputs){context.outputs=outputs;}},crypto:{randomUUID:()=> 'test-request'},fetch:async(path,options={})=>{
  let data;
  if(path==='/api/config')data={default_mode:'replay',camera_available:true,controller:'bridge'};
  else if(path==='/api/vision/mode'){selected=JSON.parse(options.body).mode;data={mode:selected,status:'ready',zones:{revision:0,config:{zones:{}}}};}
  else if(path==='/api/requests'){requestId=JSON.parse(options.body).request_id;data={status:'queued',requestId};}
  else if(path==='/api/rt')data={connected:true,age_ms:0,state:{phase:'PED_GREEN',vehicle_light:'RED',pedestrian_light:'GREEN',remaining_ms:4000,applied_frame:42,fault:null}};
  else throw Error(path);
  return {ok:true,json:async()=>data};
}};
runInNewContext(providers+'\n'+source.replace('initialize();','globalThis.ready=initialize();'),context);
(async()=>{
  await context.ready;
  assert.equal(selected,'replay');assert.equal(get('mode').value,'replay');
  assert.equal(get('camera-controls').hidden,true);
  assert.equal(context.outputs.vehicle,'red');assert.equal(context.outputs.pedestrian,'green');
  await requests[0].handlers.click();assert.equal(requestId,'test-request');
  await get('mode').handlers.change({target:{value:'camera'}});
  assert.equal(selected,'camera');assert.equal(get('camera-controls').hidden,false);
  assert.equal(get('video-controls').hidden,true);
  assert.equal(get('mode-label').textContent,'TELECAMERA');
  console.log('APP_OK: Replay default, MCU telemetry, manual camera selection, no UI simulator.');
})().catch(e=>{console.error(e);process.exitCode=1;});
