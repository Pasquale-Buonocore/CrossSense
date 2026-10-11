'use strict';
// Overlay positions use normalized image coordinates, independent of frame resolution.
const signalDefaults = {'ped-left':{x:20,y:66},'ped-right':{x:81,y:65},vehicles:{x:57,y:30}};
function normalizeSignalPosition(position,fallback){
  const clamp=(value,min,max,backup)=>Number.isFinite(value)?Math.max(min,Math.min(max,value)):backup;
  return {x:clamp(position?.x,5,95,fallback.x),y:clamp(position?.y,12,88,fallback.y)};
}
class TrafficSignals {
  constructor(){
    this.scene=document.getElementById('frame-scene');this.layer=document.getElementById('traffic-overlays');
    this.edit=document.getElementById('signal-edit');this.select=document.getElementById('signal-select');
    this.x=document.getElementById('signal-x');this.y=document.getElementById('signal-y');this.note=document.getElementById('overlay-note');
    this.dirty={};this.saving=false;this.loading=false;this.revision=-1;
    this.edit.disabled=true;
    this.positions={};this.nodes={};
    for(const [id,fallback] of Object.entries(signalDefaults)){
      this.positions[id]=normalizeSignalPosition(fallback,fallback);
      const label=id==='vehicles'?'Veicoli':id==='ped-left'?'Pedoni SX':'Pedoni DX';
      const node=document.createElement('button');node.type='button';node.className='traffic-signal';node.dataset.signal=id;
      node.innerHTML=`<span class="traffic-housing"><i data-light="red"></i><i data-light="amber"></i><i data-light="green"></i></span><span class="traffic-label">${label}</span>`;
      node.disabled=true;node.addEventListener('pointerdown',e=>{
        if(!this.edit.checked||e.button!==0)return;
        this.select.value=id;this.syncInputs();this.drag={id,pointerId:e.pointerId};node.setPointerCapture(e.pointerId);e.preventDefault();
      });
      node.addEventListener('pointermove',e=>{if(this.drag?.pointerId===e.pointerId)this.moveFromPointer(this.drag.id,e);});
      const finish=e=>{if(this.drag?.pointerId===e.pointerId){const id=this.drag.id;this.drag=null;this.save(id);}};
      node.addEventListener('pointerup',finish);node.addEventListener('pointercancel',finish);
      node.addEventListener('keydown',e=>{
        if(!this.edit.checked||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
        e.preventDefault();this.select.value=id;const p=this.positions[id];const step=e.shiftKey?5:1;
        this.setPosition(id,{x:p.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),y:p.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)});this.save(id);
      });this.nodes[id]=node;this.layer.append(node);this.place(id);
    }
    this.scene.addEventListener('click',e=>{if(this.edit.checked&&!e.target.closest('.traffic-signal')){this.moveFromPointer(this.select.value,e);this.save(this.select.value);}});
    this.edit.addEventListener('change',()=>{this.scene.classList.toggle('editing',this.edit.checked);Object.values(this.nodes).forEach(n=>n.disabled=!this.edit.checked);this.syncInputs();});
    this.select.addEventListener('change',()=>this.syncInputs());
    [this.x,this.y].forEach(input=>input.addEventListener('input',()=>{this.setPosition(this.select.value,{x:this.x.valueAsNumber,y:this.y.valueAsNumber});this.save(this.select.value);}));
    document.getElementById('signal-reset').addEventListener('click',()=>{for(const id of Object.keys(signalDefaults))this.setPosition(id,{...signalDefaults[id]});this.save();});
    this.syncInputs();this.load();this.poll=setInterval(()=>this.load(),2000);
  }
  place(id){const p=this.positions[id];this.nodes[id].style.left=`${p.x}%`;this.nodes[id].style.top=`${p.y}%`;}
  setPosition(id,p){this.positions[id]=normalizeSignalPosition(p,signalDefaults[id]);this.place(id);this.syncInputs();}
  moveFromPointer(id,e){const r=this.scene.getBoundingClientRect();this.setPosition(id,{x:100*(e.clientX-r.left)/r.width,y:100*(e.clientY-r.top)/r.height});}
  syncInputs(){const p=this.positions[this.select.value];this.x.value=String(p.x);this.y.value=String(p.y);this.x.disabled=this.y.disabled=this.select.disabled=!this.edit.checked;for(const [id,n]of Object.entries(this.nodes))n.classList.toggle('selected',this.edit.checked&&id===this.select.value);}
  applyLayout(data){
    for(const id of Object.keys(signalDefaults)){this.positions[id]=normalizeSignalPosition(data.positions[id],signalDefaults[id]);this.place(id);}
    this.revision=data.revision;this.syncInputs();
  }
  async load(){
    if(this.loading||this.saving||this.drag||Object.keys(this.dirty).length||this.edit.checked)return;
    this.loading=true;
    try{
      const response=await fetch('/api/signal-layout',{cache:'no-store'});if(!response.ok)throw Error('HTTP');
      const data=await response.json();
      if(!this.saving&&!this.drag&&!Object.keys(this.dirty).length&&!this.edit.checked&&data.revision>this.revision)this.applyLayout(data);
      this.edit.disabled=this.scene.querySelector('.zone-editing')!==null;this.note.textContent='Posizioni condivise con tutti · salvate sulla scheda.';
    }catch{this.note.textContent='Impossibile caricare le posizioni condivise. Riprovo automaticamente.';}
    finally{this.loading=false;}
  }
  save(id){
    for(const key of id?[id]:Object.keys(signalDefaults))this.dirty[key]={...this.positions[key]};
    this.note.textContent='Salvataggio delle posizioni condivise…';
    clearTimeout(this.saveTimer);this.saveTimer=setTimeout(()=>this.flush(),200);
  }
  async flush(){
    if(this.saving||!Object.keys(this.dirty).length)return;
    this.saving=true;const patch=this.dirty;this.dirty={};let failed=false;
    try{
      const response=await fetch('/api/signal-layout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)});
      if(!response.ok)throw Error('HTTP');const data=await response.json();
      if(!this.drag&&!Object.keys(this.dirty).length)this.applyLayout(data);
      this.note.textContent='Posizioni salvate e condivise con tutti.';
    }catch{
      this.dirty={...patch,...this.dirty};failed=true;
      this.note.textContent='Salvataggio non riuscito: modifiche non ancora condivise. Riprovo automaticamente.';
    }finally{
      this.saving=false;
      if(Object.keys(this.dirty).length){clearTimeout(this.saveTimer);this.saveTimer=setTimeout(()=>this.flush(),failed?2000:200);}
    }
  }
  render(outputs){
    for(const [id,node]of Object.entries(this.nodes)){
      const value=id==='vehicles'?outputs?.vehicle:outputs?.pedestrian;
      const valid=['red','amber','green'].includes(value);
      node.querySelectorAll('[data-light]').forEach(l=>l.classList.toggle('on',valid&&l.dataset.light===value));
      const state=valid?{red:'Rosso',amber:'Giallo',green:'Verde'}[value]:'Stato sconosciuto';
      node.setAttribute('aria-label',`${id==='vehicles'?'Semaforo veicoli':id==='ped-left'?'Semaforo pedoni sinistra':'Semaforo pedoni destra'}: ${state}`);
      node.classList.toggle('unknown',!valid);
    }
  }
}
const trafficSignals=new TrafficSignals();
