'use strict';
const zoneLabels={waiting_left:'Attesa sinistra',crossing:'Attraversamento',waiting_right:'Attesa destra',approach:'Corsia veicoli'};
const zoneColors={waiting_left:'#a4d65e',crossing:'#53e5bc',waiting_right:'#ffd166',approach:'#78adff'};
class VisionView {
  constructor(){
    this.mode='replay';this.data=null;this.polling=false;this.editing=false;this.saving=false;this.serial=null;
    this.image=document.getElementById('preview-frame');this.layer=document.getElementById('vision-zones');this.emptyState=document.getElementById('video-empty-state');
    this.controls=document.getElementById('zone-controls');this.note=document.getElementById('zone-note');
    this.select=document.getElementById('zone-select');this.draft=null;
    this.videoSelect=document.getElementById('video-select');this.changingVideo=false;this.sourceToken=0;
    this.videoSelect.addEventListener('change',()=>this.changeVideo());
    document.getElementById('video-play').addEventListener('click',()=>this.controlVideo('play'));
    document.getElementById('video-pause').addEventListener('click',()=>this.controlVideo('pause'));
    document.getElementById('video-stop').addEventListener('click',()=>this.controlVideo('stop'));
    document.getElementById('camera-start').addEventListener('click',()=>this.controlCamera('play'));
    document.getElementById('camera-stop').addEventListener('click',()=>this.controlCamera('stop'));
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
    this.refresh();setInterval(()=>this.refresh(),200);
  }
  async refresh(){
    if(this.polling)return;this.polling=true;
    const sourceToken=this.sourceToken;
    try{
      const response=await fetch('/api/vision',{cache:'no-store'});if(!response.ok)throw Error('Visione non disponibile');
      const data=await response.json();if(sourceToken!==this.sourceToken)return;this.data=data;this.receivedAt=Date.now();
      this.render(this.mode);
      if(!this.imageLoading&&!this.editing&&this.mode===data.mode&&data.frame&&data.frame.serial!==this.serial){
        this.loadPreview(data.frame.serial,sourceToken);
      }
    }catch{if(sourceToken===this.sourceToken)this.render(this.mode);}
    finally{this.polling=false;}
  }
  async loadPreview(serial,sourceToken){
    this.imageLoading=true;let url=null;
    try{
      const response=await fetch(`/api/vision/frame.jpg?serial=${serial}`,{cache:'no-store'});
      if(!response.ok)throw Error('Fotogramma scaduto');
      url=URL.createObjectURL(await response.blob());
      const image=new Image();
      await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
      if(sourceToken===this.sourceToken&&!this.editing&&this.mode===this.data?.mode){
        const previous=this.previewUrl;
        this.image.src=url;this.serial=serial;this.previewUrl=url;url=null;
        this.image.style.visibility='visible';
        if(previous)URL.revokeObjectURL(previous);
      }
    }catch{} // Preview failure does not invalidate observation metadata.
    finally{if(url)URL.revokeObjectURL(url);this.imageLoading=false;}
  }
  render(mode){
    const changed=this.mode!==mode;this.mode=mode;
    if(changed&&!this.editing){this.serial=null;this.image.src='/api/vision/reference.jpg';this.image.style.visibility=mode==='camera'?'hidden':'visible';}
    const data=this.data;
    const videos=data?.videos||[],catalogKey=JSON.stringify(videos);
    if(catalogKey!==this.catalogKey){
      this.catalogKey=catalogKey;this.videoSelect.replaceChildren();
      const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent=videos.length?'Seleziona un video…':'Nessun video disponibile';this.videoSelect.append(placeholder);
      for(const video of videos){const option=document.createElement('option');option.value=video.id;option.textContent=video.label;this.videoSelect.append(option);}
    }
    if(!this.changingVideo)this.videoSelect.value=data?.selected_video||'';
    this.videoSelect.disabled=mode!=='replay'||!videos.length||this.editing||this.changingVideo;
    const blocked=mode!=='replay'||this.editing||this.changingVideo,status=data?.status;
    const modelReady=!data?.model_status||data.model_status==='ready';
    document.getElementById('video-play').disabled=blocked||!data?.selected_video||!modelReady||status==='loading'||status==='running';
    document.getElementById('video-pause').disabled=blocked||!['loading','running'].includes(status);
    document.getElementById('video-stop').disabled=blocked||!data?.selected_video||['idle','ready'].includes(status);
    document.getElementById('camera-start').disabled=mode!=='camera'||this.editing||this.changingVideo||!modelReady||['loading','running'].includes(status);
    document.getElementById('camera-stop').disabled=mode!=='camera'||this.editing||this.changingVideo||!['loading','running'].includes(status);
    this.image.alt=mode==='camera'?'Telecamera CAM0 elaborata da YOLO':'Replay elaborato con riquadri, classi e confidenze YOLO';
    document.getElementById('zone-edit').disabled=!data?.zones||this.editing||(mode==='camera'&&!data.frame);
    if(!this.editing)this.note.textContent=data?.zones?`Zone ${mode==='camera'?'telecamera':'replay'} · modifica i poligoni direttamente sul frame.`:'Caricamento delle zone…';
    if(mode==='replay'||mode==='camera'){
      const fresh=data?.fresh&&data.frame&&(data.age_ms+(Date.now()-this.receivedAt)<750),frame=data?.frame;
      const statusText={idle:'Seleziona un video',ready:mode==='camera'?'Pronto · premi Avvia':'Pronto · premi Riproduci',loading:mode==='camera'?'Avvio telecamera…':'Avvio video…',paused:'Video in pausa',completed:'Video terminato',error:'Errore visione',stopped:'Sorgente fermata'}[data?.status]||'Osservazioni obsolete';
      const modelLabel=data?.model_status==='loading'?'Preparazione YOLO…':data?.model_status==='error'?'Errore modello':data?.model_status==='ready'?(data.model_load_ms?`YOLO pronto · ${(data.model_load_ms/1000).toFixed(1)} s`:'YOLO pronto'):'Preparazione modello…';
      document.getElementById('vision-badge').textContent=fresh?'● YOLO':data?.model_status==='error'?'Errore modello':statusText;
      document.getElementById('vision-description').textContent=data?.source?`${data.source} · ${frame?.inference_ms??'—'} ms inferenza · ${fresh?(frame?.fps??'—'):'—'} fotogrammi/s`:`Seleziona un video e premi Riproduci · ${modelLabel}`;
      document.getElementById('scene-source').textContent=this.editing?'MODIFICA ZONE · FRAME FERMO':fresh?(mode==='camera'?'CAM0 · YOLO26 + BYTETRACK':'VIDEO MP4 · YOLO26 + BYTETRACK'):statusText.toUpperCase();
      document.getElementById('vision-detail').textContent=data?.model_error||data?.error||(frame?`${frame.width}×${frame.height} · ${frame.detections.length} oggetti · ${mode==='camera'?'tempo live':'frame video '+frame.video_frame} · ROI revisione ${frame.zones_revision}`:statusText);
      document.getElementById('camera-note').textContent=mode==='camera'?(data?.error||(!data?.camera_calibrated&&frame?'Configura e salva le ROI della camera prima di inviare osservazioni valide alla STM32.':statusText)):'';
      const finished=data?.status==='completed';
      const showGuide=!this.editing&&(mode==='camera'?(!frame&&status!=='running'):(!data?.selected_video||data?.status==='ready'||finished||(data?.status==='loading'&&!frame)));
      this.emptyState.hidden=!showGuide;
      this.emptyState.classList.toggle('loading',data?.model_status==='loading'||data?.status==='loading');
      this.emptyState.classList.toggle('completed',finished);
      if(showGuide){
        const icon=document.getElementById('video-empty-icon'),title=document.getElementById('video-empty-title'),detail=document.getElementById('video-empty-detail');
        icon.textContent=finished?'↻':'▶';
        if(mode==='camera'){icon.textContent='●';title.textContent=data?.status==='error'?'Telecamera non disponibile':'Telecamera CAM0';detail.textContent=data?.error||'Premi Avvia telecamera per acquisire e analizzare i frame live.';}
        else if(!data?.selected_video){title.textContent='1. Seleziona un video';detail.textContent=data?.model_status==='error'?`YOLO non è disponibile: ${data.model_error||'errore di preparazione'}`:data?.model_status==='loading'?'Usa il menu a destra. Intanto CrossSense sta preparando YOLO in background.':'Usa il menu a destra, poi premi Riproduci.';}
        else if(finished){title.textContent='Video terminato';detail.textContent='Premi Riproduci per avviarlo di nuovo oppure seleziona un altro video.';}
        else if(data?.model_status==='loading'){title.textContent='YOLO si sta preparando';detail.textContent='Il video è selezionato. Riproduci sarà disponibile appena il modello sarà pronto.';}
        else if(data?.status==='loading'){title.textContent='Avvio del replay';detail.textContent='Il modello è già pronto: attendo il primo frame elaborato.';}
        else{title.textContent='2. Premi Riproduci';detail.textContent='Il video è selezionato e YOLO è pronto.';}
      }
      const obs=fresh?frame.observation:null;
      document.getElementById('occupied').textContent=obs?.crossing==='occupied'?'Occupato':obs?.valid&&obs.crossing==='clear'?'Libero':'Sconosciuto';
      document.getElementById('occupancy-detail').textContent=obs?.valid?'Osservazione YOLO corrente':mode==='camera'&&!data?.camera_calibrated?'ROI camera da configurare':obs?(frame.detections.length>8?'Più di 8 oggetti · osservazione RT invalida':'Tracking non disponibile'):'Nessuna osservazione YOLO fresca';
      const count=zone=>data?.metrics?.waiting?.[zone]??0;
      document.getElementById('waiting').textContent=obs?.valid?count('waiting_left')+count('waiting_right'):'—';
      document.getElementById('wait-detail').textContent=obs?.valid?`Sinistra ${count('waiting_left')} · Destra ${count('waiting_right')}`:'Conteggi non disponibili';
      if(!frame&&!this.editing&&this.serial===null&&!this.image.src.endsWith('/api/vision/reference.jpg'))this.image.src='/api/vision/reference.jpg';
    }
    this.draw();
  }
  async changeVideo(){
    if(this.changingVideo||this.editing)return;
    if(!this.videoSelect.value)return;
    this.changingVideo=true;this.sourceToken++;this.videoSelect.disabled=true;
    if(this.data)this.data={...this.data,status:'ready',fresh:false,frame:null};
    this.render(this.mode);
    const note=document.getElementById('video-note');note.textContent='Selezione video…';
    try{
      const response=await fetch('/api/vision/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video:this.videoSelect.value})});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Cambio video non riuscito');
      this.data=data;this.serial=null;this.image.src='/api/vision/reference.jpg';
      note.textContent='Video selezionato · premi Riproduci per avviare.';
    }catch(e){note.textContent=e.message;}
    finally{this.changingVideo=false;this.render(this.mode);this.refresh();}
  }
  async controlVideo(action){
    if(this.changingVideo||this.editing)return;
    this.changingVideo=true;this.sourceToken++;
    const note=document.getElementById('video-note');
    note.textContent={play:'Avvio video…',pause:'Pausa…',stop:'Arresto e riavvolgimento…'}[action];
    try{
      const response=await fetch(`/api/vision/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Comando video non riuscito');
      this.data=data;
      if(action==='stop'){this.serial=null;this.image.src='/api/vision/reference.jpg';}
      note.textContent={play:'Riproduzione avviata.',pause:'Video in pausa · Riproduci per riprendere.',stop:'Video fermato e riavvolto.'}[action];
    }catch(e){note.textContent=e.message;}
    finally{this.changingVideo=false;this.render(this.mode);this.refresh();}
  }
  async controlCamera(action){
    if(this.changingVideo||this.editing||this.mode!=='camera')return;
    this.changingVideo=true;this.sourceToken++;
    const note=document.getElementById('camera-note');note.textContent=action==='play'?'Avvio telecamera…':'Arresto telecamera…';
    try{
      const response=await fetch(`/api/vision/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Comando camera non riuscito');
      this.data=data;
      if(action==='stop'){this.serial=null;this.image.style.visibility='hidden';}
      note.textContent=action==='play'?'Telecamera avviata.':'Telecamera fermata.';
    }catch(e){note.textContent=e.message;}
    finally{this.changingVideo=false;this.render(this.mode);this.refresh();}
  }
  toggleEditor(){
    if(!this.data?.zones)return;
    this.draft=JSON.parse(JSON.stringify(this.data.zones));this.editorError=null;this.editing=true;this.controls.hidden=false;
    document.getElementById('traffic-overlays').style.visibility='hidden';
    document.getElementById('signal-edit').checked=false;document.getElementById('signal-edit').dispatchEvent(new Event('change'));
    document.getElementById('signal-edit').disabled=true;document.getElementById('signal-reset').disabled=true;
    if(this.serial===null)this.image.src='/api/vision/reference.jpg';
    this.layer.classList.add('zone-editing');this.render(this.mode);
  }
  closeEditor(){
    if(this.saving)return;
    this.editing=false;this.draft=null;this.controls.hidden=true;
    document.getElementById('traffic-overlays').style.visibility='';document.getElementById('signal-edit').disabled=false;document.getElementById('signal-reset').disabled=false;
    this.layer.classList.remove('zone-editing');this.serial=null;
    this.render(this.mode);this.refresh();
  }
  draw(){
    const zones=this.editing?this.draft?.config.zones:this.mode==='camera'&&!this.data?.camera_calibrated?null:this.data?.zones?.config.zones;
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
