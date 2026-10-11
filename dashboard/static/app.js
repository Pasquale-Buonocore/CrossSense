'use strict';
const $ = id => document.getElementById(id);
const controllerText={
  phases:{VEHICLE_GREEN:'Verde veicoli',VEHICLE_YELLOW:'Giallo veicoli',ALL_RED_TO_PED:'Tutto rosso · apertura pedoni',PED_GREEN:'Verde pedoni',PED_CLEARANCE:'Sgombero pedonale',ALL_RED_TO_VEH:'Tutto rosso · apertura veicoli',PROTECTED_STOP:'Arresto protetto',FAULT:'Stato di sicurezza'},
  lights:{red:'Rosso',amber:'Giallo',green:'Verde',off:'Spento',RED:'Rosso',YELLOW:'Giallo',GREEN:'Verde',OFF:'Spento'},
  codes:{NO_DATA:'Nessun dato',INVALID_DATA:'Dati non validi',TIMEOUT:'Tempo scaduto',CROSSING_CONFLICT:'Conflitto sull’attraversamento',COLLISION_RISK:'Rischio di collisione',PEDESTRIAN_STOPPED:'Pedone fermo',CLEARANCE_TIMEOUT:'Tempo di sgombero superato',OK:'Operativo'}
};
controllerText.code=value=>controllerText.codes[value]||controllerText.phases[value]||value;
globalThis.controllerText=controllerText;
function newRequestId(){
  if(typeof globalThis.crypto?.randomUUID==='function')return globalThis.crypto.randomUUID();
  if(typeof globalThis.crypto?.getRandomValues==='function')return Array.from(globalThis.crypto.getRandomValues(new Uint32Array(4)),v=>v.toString(16).padStart(8,'0')).join('');
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}
let mode='replay',events=0,provider=new HardwareProvider(event),modeChanging=false;
function event(message,warn=false){events++;const li=document.createElement('li');li.className=warn?'warn':'';const time=document.createElement('time');time.textContent=new Date().toLocaleTimeString('it-IT');const dot=document.createElement('span');const text=document.createElement('div');text.textContent=message;const tag=document.createElement('small');tag.textContent=mode==='camera'?'CAMERA':'REPLAY';li.append(time,dot,text,tag);$('event-list').prepend(li);while($('event-list').children.length>50)$('event-list').lastChild.remove();$('event-total').textContent=`${events} EVENTI`;}
function render(snapshot){
  const {phase,seq,scenario,phases}=snapshot,offline=scenario==='offline',unstable=scenario==='unstable';
  const p=snapshot.rt?{...phases[phase],name:controllerText.phases[snapshot.rt.phase]||snapshot.rt.phase,sub:snapshot.rt.fault?controllerText.code(snapshot.rt.fault):'Telemetria in tempo reale',light:snapshot.outputs.vehicle}:phases[phase];
  $('clock').textContent=new Date().toLocaleTimeString('it-IT');
  $('seq').textContent=offline?'CONTROLLER NON COLLEGATO':`FRAME ${String(seq).padStart(4,'0')}`;
  $('phase-name').textContent=offline?'Controller disconnesso':p.name;
  $('phase-sub').textContent=offline?'Stato del controller non disponibile':unstable?'Telemetria temporaneamente ritardata':p.sub;
  ['red','amber','green'].forEach(c=>$(c).className=!offline&&c===p.light?c:'');
  $('remaining').textContent=offline||snapshot.remaining===null?'—':`${snapshot.remaining} s`;
  $('progress').style.width='0%';
  $('ped-signal').textContent=offline?'—':controllerText.lights[snapshot.outputs.pedestrian]||'Sconosciuto';
  $('protection').textContent=offline?'—':['PED_CLEARANCE','PROTECTED_STOP','FAULT'].includes(snapshot.rt.phase)?'Attiva':'Inattiva';
  // Vision and analytics own their fields. A telemetry poll must not reset
  // them to unknown/empty before the owning view renders the same values.
  if(!globalThis.visionView){
    $('occupied').textContent='Sconosciuto';$('occupancy-detail').textContent='In attesa di osservazioni YOLO';
    $('waiting').textContent='—';$('wait-detail').textContent='Conteggi non disponibili';
    $('vision-badge').textContent=offline?'DISCONNESSO':'● TEMPO REALE';
  }
  if(!globalThis.replayDashboard){
    $('count').textContent='—';$('avg').textContent='—';$('ltr').textContent='—';$('rtl').textContent='—';
    ['ltr','rtl'].forEach(id=>$(id+'-bar').style.width='0%');
  }
  $('controller-description').textContent=offline?'Telemetria MCU · non disponibile':unstable?'Telemetria MCU · connessione instabile':'Telemetria MCU · Bridge v1';
  trafficSignals.render(snapshot.outputs);
  document.querySelectorAll('[data-request]').forEach(b=>b.disabled=offline||unstable||modeChanging||!!globalThis.visionView?.changingVideo||!!globalThis.visionView?.saving);
  globalThis.visionView?.render(mode);globalThis.replayDashboard?.render(snapshot);
}
function update(){render(provider.snapshot());}
function showMode(){
  $('mode').value=mode;$('mode-label').textContent=mode==='camera'?'TELECAMERA':'REPLAY';
  $('device-detail').textContent=location.host;
  $('events-description').textContent='Fasi, allarmi e attraversamenti osservati';
  $('request-status').textContent='Richieste disponibili quando il controller è collegato.';
  $('overlay-note').textContent=mode==='camera'?'Telecamera CAM0 · semafori logici nella dashboard.':'Replay MP4 dichiarato · semafori logici nella dashboard.';
  $('video-controls').hidden=mode==='camera';$('camera-controls').hidden=mode!=='camera';
  update();
}
function syncVisionMode(data){
  if(modeChanging||!['replay','camera'].includes(data?.mode)||mode===data.mode)return;
  mode=data.mode;
  if(globalThis.visionView){globalThis.visionView.sourceToken++;globalThis.visionView.serial=null;}
  showMode();
}
globalThis.syncVisionMode=syncVisionMode;
async function setMode(value){
  if(modeChanging||!['replay','camera'].includes(value))return;
  modeChanging=true;$('mode').disabled=true;
  try{
    const response=await fetch('/api/vision/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:value})});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Cambio sorgente non riuscito');
    mode=value;events=0;$('event-list').replaceChildren();$('event-total').textContent='0 EVENTI';
    if(globalThis.visionView){globalThis.visionView.sourceToken++;globalThis.visionView.data=result;globalThis.visionView.serial=null;}
    if(globalThis.replayDashboard){globalThis.replayDashboard.rtEvent=0;globalThis.replayDashboard.crossingEvent=0;}
    showMode();event(value==='camera'?'Telecamera selezionata · premi Avvia':'Replay selezionato · scegli un video e premi Riproduci');
    globalThis.visionView?.refresh();
  }catch(e){$('mode').value=mode;event(e.message,true);}
  finally{modeChanging=false;$('mode').disabled=false;update();}
}
document.querySelectorAll('[data-request]').forEach(b=>b.addEventListener('click',async()=>{
  if(modeChanging||globalThis.visionView?.changingVideo||globalThis.visionView?.saving)return;
  const active=provider,result=await provider.request(b.dataset.request,newRequestId());
  if(active!==provider)return;
  if(globalThis.replayDashboard)globalThis.replayDashboard.requestId=result.requestId||null;
  $('request-status').textContent=result.status==='queued'?'Richiesta in coda per RT · conferma al prossimo scambio':`Rifiutata · ${result.reason}`;update();
}));
$('mode').addEventListener('change',e=>setMode(e.target.value));
$('export').addEventListener('click',()=>{
  const metrics=globalThis.visionView?.data?.metrics;if(!metrics)return;
  const report={source:mode,video:mode==='replay'?globalThis.visionView.data.source:null,metrics,controller:provider.data};
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=`crosssense-${mode}.json`;a.click();URL.revokeObjectURL(url);
});
async function initialize(){
  try{const response=await fetch('/api/config',{cache:'no-store'});if(response.ok){const config=await response.json();if(globalThis.replayDashboard)globalThis.replayDashboard.controller=config.controller;$('mode-camera').disabled=!config.camera_available;}}catch{}
  // Opening a second dashboard observes the shared source; only an explicit
  // selection may change it for everyone.
  try{const response=await fetch('/api/vision',{cache:'no-store'});if(response.ok){const data=await response.json();if(globalThis.visionView){globalThis.visionView.data=data;globalThis.visionView.receivedAt=Date.now();}syncVisionMode(data);}}catch{}
  showMode();await provider.tick();update();
  setInterval(async()=>{const active=provider;await active.tick();if(active===provider)update();},200);
}
initialize();
