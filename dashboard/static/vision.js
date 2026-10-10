'use strict';
const zoneLabels={waiting_left:'Attesa sinistra',crossing:'Attraversamento',waiting_right:'Attesa destra',approach:'Corsia veicoli'};
const zoneColors={waiting_left:'#a4d65e',crossing:'#53e5bc',waiting_right:'#ffd166',approach:'#78adff'};
class VisionView {
  constructor(){
    this.mode='demo';this.data=null;this.polling=false;this.editing=false;this.saving=false;this.serial=null;
    this.image=document.getElementById('preview-frame');this.layer=document.getElementById('vision-zones');
    this.controls=document.getElementById('zone-controls');this.note=document.getElementById('zone-note');
    this.select=document.getElementById('zone-select');this.draft=null;
    document.getElementById('zone-edit').addEventListener('click',()=>this.toggleEditor());
    document.getElementById('zone-cancel').addEventListener('click',()=>this.closeEditor());
    document.getElementById('zone-clear').addEventListener('click',()=>{this.draft.config.zones[this.select.value]=[];this.draw();});
    document.getElementById('zone-undo').addEventListener('click',()=>{this.draft.config.zones[this.select.value].pop();this.draw();});
    document.getElementById('zone-save').addEventListener('click',()=>this.save());
    this.select.addEventListener('change',()=>this.draw());
    this.layer.addEventListener('click',e=>{
      if(!this.editing||this.saving)return;
      const r=this.layer.getBoundingClientRect();const points=this.draft.config.zones[this.select.value];
      if(points.length>=32){this.note.textContent='Massimo 32 vertici per zona.';return;}
      points.push([Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))]);this.draw();
    });
    this.refresh();setInterval(()=>this.refresh(),400);
  }
  async refresh(){
    if(this.polling)return;this.polling=true;
    try{
      const response=await fetch('/api/vision',{cache:'no-store'});if(!response.ok)throw Error('Visione non disponibile');
      const data=await response.json();this.data=data;this.receivedAt=Date.now();
      if(!this.editing&&this.mode==='hardware'&&data.frame&&data.frame.serial!==this.serial){
        const serial=data.frame.serial,url=`/api/vision/frame.jpg?serial=${serial}`,image=new Image();
        await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Frame scaduto'));image.src=url;});
        if(!this.editing&&this.mode==='hardware'){this.image.src=url;this.serial=serial;}
      }
      this.render(this.mode);
    }catch{this.data=null;this.render(this.mode);}
    finally{this.polling=false;}
  }
  render(mode){
    const changed=this.mode!==mode;this.mode=mode;
    if(changed&&!this.editing){this.serial=null;this.image.src=mode==='demo'?'example-frame.jpg':'/api/vision/reference.jpg';}
    const data=this.data;
    this.image.alt=mode==='hardware'?'Video elaborato con bounding box, classi e confidenze YOLO':'Frame della simulazione locale';
    document.getElementById('zone-edit').disabled=!data?.zones||this.editing;
    if(!this.editing)this.note.textContent=data?.zones?'Zone condivise · modifica i poligoni direttamente sul frame.':'Caricamento delle zone…';
    if(mode==='hardware'){
      const fresh=data?.fresh&&data.frame&&(data.age_ms+(Date.now()-this.receivedAt)<750),frame=data?.frame;
      const status={idle:'Nessun video caricato',loading:'Caricamento YOLO…',completed:'Video terminato',error:'Errore visione',stopped:'Video fermato'}[data?.status]||'Osservazioni obsolete';
      document.getElementById('vision-badge').textContent=fresh?'● YOLO':status;
      document.getElementById('vision-description').textContent=data?.source?`${data.source} · ${frame?.inference_ms??'—'} ms inferenza`:'Video MP4 · configurare la sorgente sul server';
      document.getElementById('scene-source').textContent=this.editing?'MODIFICA ZONE · FRAME FERMO':fresh?'VIDEO MP4 · YOLO26 + BYTETRACK':status.toUpperCase();
      document.getElementById('notice-detail').textContent=data?.available?'Video YOLO · lo stato del controller è mostrato separatamente.':'Stato RT dal servizio · video MP4 non configurato.';
      document.getElementById('vision-detail').textContent=data?.error||(frame?`${frame.detections.length} oggetti · frame video ${frame.video_frame} · ${Math.round(frame.video_ms/1000)} s · ROI revisione ${frame.zones_revision}`:status);
      const obs=fresh?frame.observation:null;
      document.getElementById('occupied').textContent=obs?.crossing==='occupied'?'Occupato':obs?.valid&&obs.crossing==='clear'?'Libero':'Sconosciuto';
      document.getElementById('occupancy-detail').textContent=obs?.valid?'Osservazione YOLO corrente':obs?(frame.detections.length>8?'Più di 8 oggetti · osservazione RT invalida':'Tracking non disponibile'):'Nessuna osservazione YOLO fresca';
      const count=zone=>frame?.detections.filter(d=>d.class==='pedestrian'&&d.zone===zone).length??0;
      document.getElementById('waiting').textContent=obs?.valid?count('waiting_left')+count('waiting_right'):'—';
      document.getElementById('wait-detail').textContent=obs?.valid?`Sinistra ${count('waiting_left')} · Destra ${count('waiting_right')}`:'Conteggi non disponibili';
      if(!frame&&!this.editing&&this.serial===null&&!this.image.src.endsWith('/api/vision/reference.jpg'))this.image.src='/api/vision/reference.jpg';
    }else{
      document.getElementById('vision-detail').textContent='Simulazione locale · seleziona Hardware per il video YOLO';
      if(this.editing)document.getElementById('scene-source').textContent='MODIFICA ZONE · FRAME DI RIFERIMENTO';
    }
    this.draw();
  }
  toggleEditor(){
    if(!this.data?.zones)return;
    this.draft=JSON.parse(JSON.stringify(this.data.zones));this.editorError=null;this.editing=true;this.controls.hidden=false;
    document.getElementById('traffic-overlays').style.visibility='hidden';
    document.getElementById('signal-edit').checked=false;document.getElementById('signal-edit').dispatchEvent(new Event('change'));
    document.getElementById('signal-edit').disabled=true;document.getElementById('signal-reset').disabled=true;
    if(this.mode==='demo'||this.serial===null)this.image.src='/api/vision/reference.jpg';
    this.layer.classList.add('zone-editing');this.render(this.mode);
  }
  closeEditor(){
    if(this.saving)return;
    this.editing=false;this.draft=null;this.controls.hidden=true;
    document.getElementById('traffic-overlays').style.visibility='';document.getElementById('signal-edit').disabled=false;document.getElementById('signal-reset').disabled=false;
    this.layer.classList.remove('zone-editing');this.serial=null;
    if(this.mode==='demo')this.image.src='example-frame.jpg';
    this.render(this.mode);this.refresh();
  }
  draw(){
    const zones=this.editing?this.draft?.config.zones:this.mode==='hardware'?this.data?.zones?.config.zones:null;
    this.layer.replaceChildren();if(!zones)return;
    const create=tag=>document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const [name,points] of Object.entries(zones)){
      const shape=create(points.length>=3?'polygon':'polyline');shape.setAttribute('points',points.map(p=>`${p[0]*1000},${p[1]*1000}`).join(' '));
      shape.setAttribute('stroke',zoneColors[name]);shape.setAttribute('fill',points.length>=3?zoneColors[name]+'22':'none');
      shape.setAttribute('stroke-width',this.editing&&this.select.value===name?'4':'2');shape.setAttribute('vector-effect','non-scaling-stroke');this.layer.append(shape);
      if(points.length){const label=create('text');label.setAttribute('x',points[0][0]*1000);label.setAttribute('y',Math.max(20,points[0][1]*1000-8));label.setAttribute('fill',zoneColors[name]);label.textContent=zoneLabels[name];this.layer.append(label);}
      if(this.editing&&this.select.value===name)for(const p of points){const dot=create('circle');dot.setAttribute('cx',p[0]*1000);dot.setAttribute('cy',p[1]*1000);dot.setAttribute('r','5');dot.setAttribute('fill',zoneColors[name]);this.layer.append(dot);}
    }
    if(this.editing)this.note.textContent=this.editorError||`${zoneLabels[this.select.value]} · ${zones[this.select.value].length} vertici. Svuota per ridisegnare, poi clicca i vertici in ordine e salva tutte le zone.`;
  }
  async save(){
    if(this.saving)return;this.saving=true;this.controls.querySelectorAll('button,select').forEach(el=>el.disabled=true);
    try{
      const response=await fetch('/api/vision/zones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.draft)});
      const result=await response.json();if(!response.ok)throw Error(result.error||'Salvataggio non riuscito');
      this.data={...this.data,zones:result};this.saving=false;this.closeEditor();this.note.textContent='Zone salvate · tracking e osservazioni riavviati.';
    }catch(e){this.editorError=e.message;this.note.textContent=e.message;}
    finally{this.saving=false;this.controls.querySelectorAll('button,select').forEach(el=>el.disabled=false);}
  }
}
globalThis.visionView=new VisionView();
