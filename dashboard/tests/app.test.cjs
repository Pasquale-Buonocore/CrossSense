const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {runInNewContext}=require('node:vm');
const assert=require('node:assert/strict');
const source=readFileSync(join(__dirname,'../static/app.js'),'utf8');
const providers=readFileSync(join(__dirname,'../static/providers.js'),'utf8');
function node(){return {textContent:'',value:'',hidden:false,disabled:false,style:{},children:[],handlers:{},addEventListener(type,fn){this.handlers[type]=fn;},replaceChildren(){this.children=[];},append(){},prepend(child){this.children.unshift(child);},remove(){},className:''};}
async function run(defaultMode){
  const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,node());return elements.get(id);};
  const requests=[node(),node()];requests[0].dataset={request:'pedestrian'};requests[1].dataset={request:'accessible'};
  let trialStatus='completed',posts=0;
  const context={document:{getElementById:get,createElement:node,querySelectorAll:()=>requests},location:{host:'board.test:8081'},Date,console,setInterval(){},trafficSignals:{render(outputs){context.outputs=outputs;}},crypto:{randomUUID:()=> 'test-request'},fetch:async(path,options={})=>{
    let data;
    if(path==='/api/config')data={default_mode:defaultMode};
    else if(path==='/api/trial'){
      if(options.method==='POST'){posts++;trialStatus='running';data={status:'started'};}
      else data={available:true,status:trialStatus,error:null};
    }else if(path==='/api/rt')data={connected:true,age_ms:0,state:{phase:'PED_GREEN',vehicle_light:'RED',pedestrian_light:'GREEN',remaining_ms:4000,applied_frame:42,fault:null}};
    else throw Error(path);
    return {ok:true,json:async()=>data};
  }};
  runInNewContext(providers+'\n'+source.replace('initialize();','globalThis.ready=initialize();'),context);
  await context.ready;
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(get('mode').value,defaultMode);
  if(defaultMode==='hardware'){
    assert.equal(context.outputs.vehicle,'red');assert.equal(context.outputs.pedestrian,'green');
    assert.equal(get('trial-start').hidden,false);assert.equal(get('trial-start').disabled,false);
    assert.match(get('trial-status').textContent,/completata/);
    await get('trial-start').handlers.click();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(posts,1);assert.equal(get('trial-start').disabled,true);
    assert.match(get('trial-status').textContent,/in corso/);
    assert.match(get('notice-detail').textContent,/board.test:8081/);
  }else assert.equal(get('trial-start').hidden,true);
}
(async()=>{await run('hardware');await run('demo');console.log('APP_OK: default Hardware for Bridge, live MCU colors, repeat button and running state; standalone Demo preserved.');})().catch(e=>{console.error(e);process.exitCode=1;});
