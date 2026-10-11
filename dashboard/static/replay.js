'use strict';
// Presentation of replay measurements and controller events; no control logic.
globalThis.replayDashboard = {
  rtEvent:0, crossingEvent:0, requestId:null, controller:'none',
  render(snapshot){
    if(snapshot.source!=='hardware')return;
    const data=globalThis.visionView?.data, metrics=data?.metrics;
    const rt=provider.data;
    $('controller-description').textContent=this.controller==='native'?'Stesso firmware C++ · esecuzione sul PC':'Controller logico · MCU via Bridge';
    if($('controller-kind'))$('controller-kind').textContent=this.controller==='native'?'NATIVO':'STM32';
    if(metrics){
      $('count').textContent=metrics.completed;
      $('ltr').textContent=metrics.left_to_right;$('rtl').textContent=metrics.right_to_left;
      $('avg').textContent=metrics.average_wait_ms===null?'—':`${(metrics.average_wait_ms/1000).toFixed(1)} s`;
      for(const [id,value] of [['ltr',metrics.left_to_right],['rtl',metrics.right_to_left]])$(''+id+'-bar').style.width=`${metrics.completed?100*value/metrics.completed:0}%`;
      for(const entry of metrics.events||[]){
        if(entry.id>this.crossingEvent){event(`Attraversamento ${entry.direction==='left_to_right'?'SX → DX':'DX → SX'} · traccia ${entry.track_id}`);this.crossingEvent=entry.id;}
      }
    }
    for(const entry of rt?.events||[]){
      if(entry.id>this.rtEvent){event(globalThis.controllerText?.code(entry.message)||entry.message,entry.type==='ALARM');this.rtEvent=entry.id;}
    }
    const stopped=data?.fresh&&data.age_ms+(Date.now()-(globalThis.visionView?.receivedAt||0))<750?metrics?.stopped_ids||[]:[];
    const alarms=snapshot.rt?.alarms||[];
    const label=alarms.map(value=>globalThis.controllerText?.code(value)||value).concat(stopped.length?['IMMOBILITÀ NEL VIDEO']:[]);
    $('alarm-status').textContent=snapshot.scenario==='offline'?'Controller non disponibile':label.length?label.join(' · '):'Nessun allarme attivo';
    $('alarm-status').classList.toggle('active-alarm',label.length>0);
    const transportCode=rt?.error||snapshot.rt?.error||snapshot.rt?.fault||'OK';
    $('transport-status').textContent=rt?`${this.controller==='native'?'Firmware nativo su PC':'MCU via Bridge'} · RPC ${rt.rpc_ms??'—'} ms · ${globalThis.controllerText?.code(transportCode)||transportCode}`:'In attesa del servizio';
    const request=(rt?.requests||[]).find(r=>r.requestId===this.requestId);
    if(request){
      const labels={queued:'In coda: attende una nuova immagine',accepted:'Ricevuta dal controller',applied:'Applicata: in attesa della fase',served:'Richiesta servita',cancelled:'Richiesta annullata'};
      $('request-status').textContent=(labels[request.status]||request.status)+(request.reason?` · ${request.reason}`:'');
    }
    $('export').disabled=!metrics;
  }
};
