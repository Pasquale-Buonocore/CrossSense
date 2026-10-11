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
let selected='camera',requestId=null,modePosts=0;
const context={document:{getElementById:get,createElement:node,querySelectorAll:()=>requests},location:{host:'board.test:8080'},Date,console,setInterval(){},trafficSignals:{render(outputs){context.outputs=outputs;}},crypto:{randomUUID:()=> 'test-request'},fetch:async(path,options={})=>{
  let data;
  if(path==='/api/config')data={default_mode:'replay',camera_available:true,controller:'bridge'};
  else if(path==='/api/vision')data={mode:selected,status:'running',fresh:true,age_ms:100};
  else if(path==='/api/vision/mode'){modePosts++;selected=JSON.parse(options.body).mode;data={mode:selected,status:'ready',zones:{revision:0,config:{zones:{}}}};}
  else if(path==='/api/requests'){requestId=JSON.parse(options.body).request_id;data={status:'queued',requestId};}
  else if(path==='/api/rt')data={connected:true,age_ms:0,state:{phase:'PED_GREEN',vehicle_light:'RED',pedestrian_light:'GREEN',remaining_ms:4000,applied_frame:42,fault:null}};
  else throw Error(path);
  return {ok:true,json:async()=>data};
}};
runInNewContext(providers+'\n'+source.replace('initialize();','globalThis.ready=initialize();'),context);
(async()=>{
  await context.ready;
  assert.equal(modePosts,0,'opening a viewer must not change the shared source');
  assert.equal(selected,'camera');assert.equal(get('mode').value,'camera');
  assert.equal(get('camera-controls').hidden,false);
  context.syncVisionMode({mode:'replay'});
  assert.equal(get('mode').value,'replay','a remote mode change updates this viewer');
  assert.equal(modePosts,0,'following a remote mode change must not send another command');
  assert.equal(get('camera-controls').hidden,true);
  assert.equal(context.outputs.vehicle,'red');assert.equal(context.outputs.pedestrian,'green');
  await requests[0].handlers.click();assert.equal(requestId,'test-request');
  await get('mode').handlers.change({target:{value:'camera'}});
  assert.equal(selected,'camera');assert.equal(get('camera-controls').hidden,false);
  assert.equal(get('video-controls').hidden,true);
  assert.equal(get('mode-label').textContent,'TELECAMERA');
  context.visionView={render(){}};context.replayDashboard={render(){}};
  get('occupied').textContent='Libero';get('waiting').textContent='2';get('count').textContent='7';
  context.update();
  assert.equal(get('occupied').textContent,'Libero','controller rendering must not overwrite the vision-owned crossing');
  assert.equal(get('waiting').textContent,'2','controller rendering must not reset vision counts');
  assert.equal(get('count').textContent,'7','controller rendering must not reset analytics counts');
  console.log('APP_OK: new viewers preserve the shared source, remote changes synchronize, explicit selection sends commands.');
})().catch(e=>{console.error(e);process.exitCode=1;});
