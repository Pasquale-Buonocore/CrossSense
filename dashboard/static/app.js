'use strict';
const $ = id => document.getElementById(id);
let mode='demo',events=0,provider;
function event(message,warn=false){events++;const li=document.createElement('li');li.className=warn?'warn':'';const time=document.createElement('time');time.textContent=new Date().toLocaleTimeString('it-IT');const dot=document.createElement('span');const text=document.createElement('div');text.textContent=message;const tag=document.createElement('small');tag.textContent=mode==='demo'?'DEMO':'HARDWARE';li.append(time,dot,text,tag);$('event-list').prepend(li);while($('event-list').children.length>50)$('event-list').lastChild.remove();$('event-total').textContent=`${events} EVENTI`;}
function render(snapshot){
const {phase,elapsed,seq,paused,scenario,left,right,completed,waitSamples,extended,phases}=snapshot;const offline=scenario==='offline'||snapshot.source==='hardware',stopped=scenario==='stopped'&&phase===3;const p=phases[phase];const duration=p.duration+(phase===2&&extended?8:0);const waiting=phase<2?(scenario==='busy'?6:2):0;
$('clock').textContent=new Date().toLocaleTimeString('it-IT');$('seq').textContent=offline?(snapshot.source==='hardware'?'HARDWARE NON COLLEGATO':'TELEMETRIA OBSOLETA'):`FRAME ${String(seq).padStart(4,'0')}`;
$('phase-name').textContent=offline?(snapshot.source==='hardware'?'Hardware disconnesso':'Telemetria obsoleta'):p.name;$('phase-sub').textContent=offline?'Stato del controller non disponibile':p.sub;
['red','amber','green'].forEach(c=>$(c).className=!offline&&c===p.light?c:'');$('remaining').textContent=offline||stopped?'—':`${Math.max(0,duration-elapsed)} s`;$('progress').style.width=offline?'0%':`${100*(1-elapsed/duration)}%`;
$('ped-signal').textContent=offline?'—':phase===2?'Verde':'Rosso';$('protection').textContent=offline?'—':phase===3?'Attiva':'Inattiva';$('occupied').textContent=offline?'Sconosciuto':phase===2||stopped?'Occupato':'Libero';$('occupancy-detail').textContent=offline?'Osservazioni non valide':stopped?'Pedone fermo · protezione mantenuta':phase===2?'Tracce demo in attraversamento':'Nessuna traccia sulle strisce';$('waiting').textContent=offline?'—':waiting;$('wait-detail').textContent=offline?'Conteggi non disponibili':`Sinistra ${waiting/2} · Destra ${waiting/2}`;
$('count').textContent=completed??'—';$('avg').textContent=waitSamples.length?`${Math.round(waitSamples.reduce((a,b)=>a+b,0)/waitSamples.length)} s`:'—';$('ltr').textContent=left??'—';$('rtl').textContent=right??'—';['ltr','rtl'].forEach((id,i)=>$(id+'-bar').style.width=`${completed?100*(i?right:left)/completed:0}%`);
let tracks='';if(!offline){const n=phase===2? (scenario==='busy'?6:2):stopped?1:waiting;for(let i=0;i<n;i++){const y=phase===2?95+(elapsed/duration)*205:stopped?190:i%2?345:50;const x=355+(i%3)*35;tracks+=`<rect x="${x-13}" y="${y-19}" width="26" height="38" rx="3" fill="#63d4b2" fill-opacity=".1" stroke="#63d4b2"/><circle cx="${x}" cy="${y-4}" r="6" fill="#9fe7ce"/><path d="M${x} ${y+2}v10" stroke="#9fe7ce" stroke-width="4"/><text x="${x-12}" y="${y-24}" fill="#9fe7ce" font-size="8" font-family="monospace">P${i+1}</text>`;}}$('tracks').innerHTML=tracks;const cx=phase===0?80+(elapsed/18)*650:phase===1?260:120;$('car').innerHTML=offline?'':`<rect x="${cx}" y="225" width="66" height="32" rx="8" fill="#91a5b5"/><rect x="${cx+15}" y="229" width="26" height="24" rx="4" fill="#344d60"/><rect x="${cx-5}" y="219" width="76" height="44" rx="5" fill="none" stroke="#81b4ee"/><text x="${cx}" y="213" fill="#81b4ee" font-size="8" font-family="monospace">V01 · STIMA N/D</text>`;
document.querySelectorAll('[data-request]').forEach(b=>b.disabled=offline||paused);$('export').disabled=snapshot.source==='hardware';}
function update(){render(provider.snapshot());}
function setMode(value){
  provider?.dispose();mode=value;events=0;$('event-list').replaceChildren();$('event-total').textContent='0 EVENTI';
  provider=mode==='demo'?new DemoProvider(event):new HardwareProvider();
  const demo=mode==='demo';
  $('mode-label').textContent=demo?'MODALITÀ DEMO':'MODALITÀ HARDWARE';
  $('notice-title').textContent=demo?'Simulazione locale':'Hardware non collegato';
  $('notice-detail').textContent=demo?'Camera e controller non collegati. Tutti i dati e le richieste sono simulati.':'API da configurare: telemetria e video non disponibili.';
  $('vision-description').textContent=demo?'Schema animato · osservazioni simulate':'Schema di riferimento · nessun video collegato';
  $('vision-badge').textContent=demo?'● DEMO':'DISCONNESSO';
  $('controller-description').textContent=demo?'Macchina a stati · simulata':'Telemetria MCU · non disponibile';
  $('scene-source').textContent=demo?'VISION SIMULATOR':'VIDEO NON DISPONIBILE';
  $('device-detail').textContent=demo?'Ambiente di dimostrazione':'Connessione da configurare';
  $('events-description').textContent=demo?'Transizioni e risposte alle richieste demo':'Eventi di connessione hardware';
  $('scenario').disabled=!demo;$('scenario').value='normal';$('pause').disabled=!demo;$('pause').textContent='Ⅱ Pausa';
  $('request-status').textContent=demo?'Le richieste demo rispettano le transizioni del simulatore.':'Richieste disabilitate: controller non collegato.';
  event(demo?'Sessione demo avviata · hardware non collegato':'Modalità hardware: nessun provider API configurato',!demo);update();
}
document.querySelectorAll('[data-request]').forEach(b=>b.addEventListener('click',()=>{
  const result=provider.request(b.dataset.request,crypto.randomUUID());
  $('request-status').textContent=result.status==='accepted'?`Accettata dal simulatore · ${result.requestId.slice(0,8)} · ${result.pending} in coda`:`Rifiutata · ${result.reason}`;update();
}));
$('mode').addEventListener('change',e=>setMode(e.target.value));
$('pause').addEventListener('click',()=>{provider.togglePause();$('pause').textContent=provider.snapshot().paused?'▶ Riprendi':'Ⅱ Pausa';update();});
$('scenario').addEventListener('change',e=>{provider.setScenario(e.target.value);$('request-status').textContent=e.target.value==='offline'?'Telemetria obsoleta: richieste disabilitate':'Le richieste demo rispettano le transizioni del simulatore.';update();});
$('export').addEventListener('click',()=>{
  const s=provider.snapshot();if(s.source!=='demo')return;
  const csv='origine,attraversamenti,sinistra_destra,destra_sinistra,attesa_media_s\n'+`simulazione,${s.completed},${s.left},${s.right},${s.waitSamples.length?s.waitSamples.reduce((a,b)=>a+b,0)/s.waitSamples.length:''}\n`;
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='crosssense-demo.csv';a.click();URL.revokeObjectURL(url);event('Statistiche della simulazione esportate');
});
setMode('demo');setInterval(()=>{provider.tick();update();},1000);
