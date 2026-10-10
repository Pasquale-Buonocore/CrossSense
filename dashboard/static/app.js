'use strict';
const $ = id => document.getElementById(id);
let mode='demo',events=0,provider,trialPolling=false;
function event(message,warn=false){events++;const li=document.createElement('li');li.className=warn?'warn':'';const time=document.createElement('time');time.textContent=new Date().toLocaleTimeString('it-IT');const dot=document.createElement('span');const text=document.createElement('div');text.textContent=message;const tag=document.createElement('small');tag.textContent=mode==='demo'?'DEMO':'HARDWARE';li.append(time,dot,text,tag);$('event-list').prepend(li);while($('event-list').children.length>50)$('event-list').lastChild.remove();$('event-total').textContent=`${events} EVENTI`;}
function render(snapshot){
const {phase,elapsed,seq,paused,scenario,left,right,completed,waitSamples,extended,phases}=snapshot;const offline=scenario==='offline',stopped=scenario==='stopped'&&phase===3;const p=snapshot.rt?{...phases[phase],name:snapshot.rt.phase,sub:snapshot.rt.fault||'Telemetria RT',light:snapshot.outputs.vehicle}:phases[phase];const duration=p.duration+(phase===2&&extended?8:0);const waiting=phase<2?(scenario==='busy'?6:2):0;
$('clock').textContent=new Date().toLocaleTimeString('it-IT');$('seq').textContent=offline?(snapshot.source==='hardware'?'HARDWARE NON COLLEGATO':'TELEMETRIA OBSOLETA'):`FRAME ${String(seq).padStart(4,'0')}`;
$('phase-name').textContent=offline?(snapshot.source==='hardware'?'Hardware disconnesso':'Telemetria obsoleta'):p.name;$('phase-sub').textContent=offline?'Stato del controller non disponibile':p.sub;
['red','amber','green'].forEach(c=>$(c).className=!offline&&c===p.light?c:'');$('remaining').textContent=offline||stopped?'—':snapshot.source==='hardware'?(snapshot.remaining===null?'—':`${snapshot.remaining} s`):`${Math.max(0,duration-elapsed)} s`;$('progress').style.width=offline||snapshot.source==='hardware'?'0%':`${100*(1-elapsed/duration)}%`;
$('ped-signal').textContent=offline?'—':snapshot.source==='hardware'?snapshot.outputs.pedestrian:phase===2?'Verde':'Rosso';$('protection').textContent=offline?'—':snapshot.source==='hardware'?(['PED_CLEARANCE','PROTECTED_STOP','FAULT'].includes(snapshot.rt.phase)?'Attiva':'Inattiva'):phase===3?'Attiva':'Inattiva';$('occupied').textContent=offline||snapshot.source==='hardware'?'Sconosciuto':phase===2||stopped?'Occupato':'Libero';$('occupancy-detail').textContent=snapshot.source==='hardware'?'Occupazione non inclusa nella telemetria RT':offline?'Osservazioni non valide':stopped?'Pedone fermo · protezione mantenuta':phase===2?'Tracce demo in attraversamento':'Nessuna traccia sulle strisce';$('waiting').textContent=offline||snapshot.source==='hardware'?'—':waiting;$('wait-detail').textContent=offline||snapshot.source==='hardware'?'Conteggi non disponibili':`Sinistra ${waiting/2} · Destra ${waiting/2}`;
$('count').textContent=completed??'—';$('avg').textContent=waitSamples.length?`${Math.round(waitSamples.reduce((a,b)=>a+b,0)/waitSamples.length)} s`:'—';$('ltr').textContent=left??'—';$('rtl').textContent=right??'—';['ltr','rtl'].forEach((id,i)=>$(id+'-bar').style.width=`${completed?100*(i?right:left)/completed:0}%`);
if(snapshot.source==='hardware'){ $('notice-title').textContent=offline?'Hardware disconnesso':'Controller RT collegato';$('vision-badge').textContent=offline?'DISCONNESSO':'● RT';$('controller-description').textContent=offline?'Telemetria MCU · non disponibile':'Telemetria MCU · Bridge v1';$('vision-description').textContent=offline?'Frame di esempio · uscite MCU non disponibili':'Frame di esempio · colori ricevuti dalla STM32';}
trafficSignals.render(snapshot.outputs);
document.querySelectorAll('[data-request]').forEach(b=>b.disabled=offline||paused);$('export').disabled=snapshot.source==='hardware';
globalThis.visionView?.render(mode);}
function update(){render(provider.snapshot());}
function setMode(value){
  provider?.dispose();mode=value;events=0;$('event-list').replaceChildren();$('event-total').textContent='0 EVENTI';
  $('mode').value=mode;$('trial-start').hidden=true;$('trial-status').textContent='';
  provider=mode==='demo'?new DemoProvider(event):new HardwareProvider(event);
  const demo=mode==='demo';
  $('mode-label').textContent=demo?'MODALITÀ DEMO':'MODALITÀ HARDWARE';
  $('notice-title').textContent=demo?'Simulazione locale':'Hardware non collegato';
  $('notice-detail').textContent=demo?'Camera e controller non collegati. Tutti i dati e le richieste sono simulati.':`Stato STM32 dal servizio ${location.host}. Video live non disponibile.`;
  $('vision-description').textContent=demo?'Frame di esempio · uscite simulate':'Frame di esempio · uscite MCU non disponibili';
  $('vision-badge').textContent=demo?'● DEMO':'DISCONNESSO';
  $('controller-description').textContent=demo?'Macchina a stati · simulata':'Telemetria MCU · non disponibile';
  $('scene-source').textContent='FRAME DI ESEMPIO · NON LIVE';
  $('device-detail').textContent=demo?'Ambiente di dimostrazione':location.host;
  $('events-description').textContent=demo?'Transizioni e risposte alle richieste demo':'Eventi di connessione hardware';
  $('scenario').disabled=!demo;$('scenario').value='normal';$('pause').disabled=!demo;$('pause').textContent='Ⅱ Pausa';
  $('request-status').textContent=demo?'Le richieste demo rispettano le transizioni del simulatore.':'Richieste disabilitate: controller non collegato.';
  event(demo?'Sessione demo avviata · hardware non collegato':`Lettura telemetria STM32 da ${location.host}`);update();
  if(!demo)refreshTrial();
}
async function refreshTrial(){
  if(mode!=='hardware'||trialPolling)return;
  trialPolling=true;
  try{
    const response=await fetch('/api/trial',{cache:'no-store'});if(!response.ok)throw Error('HTTP');
    const trial=await response.json();if(mode!=='hardware')return;
    $('trial-start').hidden=!trial.available;$('trial-start').disabled=!trial.available||trial.status==='running';
    $('trial-start').textContent=trial.status==='completed'?'Ripeti prova STM32':'Avvia prova STM32';
    $('trial-status').textContent=!trial.available?'':trial.status==='running'?'Prova sintetica in corso · 2 cicli':trial.status==='completed'?'Prova completata · semafori rossi':trial.status==='error'?`Prova interrotta: ${trial.error}`:'ROI libere simulate · nessuna camera';
  }catch{if(mode==='hardware'){$('trial-start').hidden=true;$('trial-status').textContent='';}}
  finally{trialPolling=false;}
}
$('trial-start').addEventListener('click',async()=>{
  $('trial-start').disabled=true;
  try{
    const response=await fetch('/api/trial',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const result=await response.json();
    if(!response.ok){$('trial-status').textContent=result.reason||result.error||'Avvio non riuscito';return;}
    event('Prova sintetica STM32 avviata · due cicli');
  }catch{$('trial-status').textContent='Collegamento interrotto';}
  finally{refreshTrial();}
});
document.querySelectorAll('[data-request]').forEach(b=>b.addEventListener('click',async()=>{
  const active=provider;const result=await provider.request(b.dataset.request,crypto.randomUUID());
  if(active!==provider)return;
  $('request-status').textContent=result.status==='accepted'?`Accettata dal simulatore · ${result.requestId.slice(0,8)} · ${result.pending} in coda`:result.status==='queued'?'Richiesta in coda per RT · conferma al prossimo scambio':`Rifiutata · ${result.reason}`;update();
}));
$('mode').addEventListener('change',e=>setMode(e.target.value));
$('pause').addEventListener('click',()=>{provider.togglePause();$('pause').textContent=provider.snapshot().paused?'▶ Riprendi':'Ⅱ Pausa';update();});
$('scenario').addEventListener('change',e=>{provider.setScenario(e.target.value);$('request-status').textContent=e.target.value==='offline'?'Telemetria obsoleta: richieste disabilitate':'Le richieste demo rispettano le transizioni del simulatore.';update();});
$('export').addEventListener('click',()=>{
  const s=provider.snapshot();if(s.source!=='demo')return;
  const csv='origine,attraversamenti,sinistra_destra,destra_sinistra,attesa_media_s\n'+`simulazione,${s.completed},${s.left},${s.right},${s.waitSamples.length?s.waitSamples.reduce((a,b)=>a+b,0)/s.waitSamples.length:''}\n`;
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='crosssense-demo.csv';a.click();URL.revokeObjectURL(url);event('Statistiche della simulazione esportate');
});
async function initialize(){
  let initial='demo';
  try{const response=await fetch('/api/config',{cache:'no-store'});if(response.ok){const config=await response.json();if(config.default_mode==='hardware')initial='hardware';}}catch{}
  setMode(initial);
  if(mode==='hardware'){await provider.tick();update();}
  setInterval(async()=>{const active=provider;if(mode==='hardware'||Date.now()-(active.lastTick??0)>=1000){active.lastTick=Date.now();await active.tick();}if(active===provider)update();},200);
  setInterval(refreshTrial,1000);
}
initialize();
