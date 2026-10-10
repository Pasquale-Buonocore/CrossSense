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
    let saved;try{saved=JSON.parse(localStorage.getItem('crosssense.signal-layout.v1'));}catch{}
    this.positions={};this.nodes={};
    for(const [id,fallback] of Object.entries(signalDefaults)){
      this.positions[id]=normalizeSignalPosition(saved?.[id],fallback);
      const label=id==='vehicles'?'Veicoli':id==='ped-left'?'Pedoni SX':'Pedoni DX';
      const node=document.createElement('button');node.type='button';node.className='traffic-signal';node.dataset.signal=id;
      node.innerHTML=`<span class="traffic-housing"><i data-light="red"></i><i data-light="amber"></i><i data-light="green"></i></span><span class="traffic-label">${label}<small>Stato sconosciuto</small></span>`;
      node.disabled=true;node.addEventListener('pointerdown',e=>{
        if(!this.edit.checked||e.button!==0)return;
        this.select.value=id;this.syncInputs();this.drag={id,pointerId:e.pointerId};node.setPointerCapture(e.pointerId);e.preventDefault();
      });
      node.addEventListener('pointermove',e=>{if(this.drag?.pointerId===e.pointerId)this.moveFromPointer(this.drag.id,e);});
      const finish=e=>{if(this.drag?.pointerId===e.pointerId){this.drag=null;this.save();}};
      node.addEventListener('pointerup',finish);node.addEventListener('pointercancel',finish);
      node.addEventListener('keydown',e=>{
        if(!this.edit.checked||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
        e.preventDefault();this.select.value=id;const p=this.positions[id];const step=e.shiftKey?5:1;
        this.setPosition(id,{x:p.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),y:p.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)});this.save();
      });this.nodes[id]=node;this.layer.append(node);this.place(id);
    }
    this.scene.addEventListener('click',e=>{if(this.edit.checked&&!e.target.closest('.traffic-signal')){this.moveFromPointer(this.select.value,e);this.save();}});
    this.edit.addEventListener('change',()=>{this.scene.classList.toggle('editing',this.edit.checked);Object.values(this.nodes).forEach(n=>n.disabled=!this.edit.checked);this.syncInputs();});
    this.select.addEventListener('change',()=>this.syncInputs());
    [this.x,this.y].forEach(input=>input.addEventListener('input',()=>{this.setPosition(this.select.value,{x:this.x.valueAsNumber,y:this.y.valueAsNumber});this.save();}));
    document.getElementById('signal-reset').addEventListener('click',()=>{for(const id of Object.keys(signalDefaults))this.setPosition(id,{...signalDefaults[id]});this.save();});
    this.syncInputs();
  }
  place(id){const p=this.positions[id];this.nodes[id].style.left=`${p.x}%`;this.nodes[id].style.top=`${p.y}%`;}
  setPosition(id,p){this.positions[id]=normalizeSignalPosition(p,signalDefaults[id]);this.place(id);this.syncInputs();}
  moveFromPointer(id,e){const r=this.scene.getBoundingClientRect();this.setPosition(id,{x:100*(e.clientX-r.left)/r.width,y:100*(e.clientY-r.top)/r.height});}
  syncInputs(){const p=this.positions[this.select.value];this.x.value=p.x.toFixed(1);this.y.value=p.y.toFixed(1);this.x.disabled=this.y.disabled=this.select.disabled=!this.edit.checked;for(const [id,n]of Object.entries(this.nodes))n.classList.toggle('selected',this.edit.checked&&id===this.select.value);}
  save(){try{localStorage.setItem('crosssense.signal-layout.v1',JSON.stringify(this.positions));this.note.textContent='Posizioni salvate in questo browser · nessuna modifica al controller.';}catch{this.note.textContent='Posizioni applicate; salvataggio locale non disponibile.';}}
  render(outputs){
    for(const [id,node]of Object.entries(this.nodes)){
      const value=id==='vehicles'?outputs?.vehicle:outputs?.pedestrian;
      const valid=['red','amber','green'].includes(value);
      node.querySelectorAll('[data-light]').forEach(l=>l.classList.toggle('on',valid&&l.dataset.light===value));
      const state=valid?{red:'Rosso',amber:'Giallo',green:'Verde'}[value]:'Stato sconosciuto';
      node.querySelector('small').textContent=state;node.setAttribute('aria-label',`${id==='vehicles'?'Semaforo veicoli':id==='ped-left'?'Semaforo pedoni sinistra':'Semaforo pedoni destra'}: ${state}`);
      node.classList.toggle('unknown',!valid);
    }
  }
}
const trafficSignals=new TrafficSignals();
