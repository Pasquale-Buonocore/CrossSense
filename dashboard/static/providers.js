'use strict';
// Presentation-only filtering; acquisition deadlines and watchdogs stay active.
function visibleMessage(value){
  const message=String(value??'');
  return /timeout|timed out|deadline|stale|old_frame|scadut|obsolet|ritard|instabil|oltre budget|entro\s+\d+\s*(?:ms|s)\b/i.test(message)?'':message;
}
// The browser displays controller telemetry; source selection belongs to the server.
const phases = [{name:'Verde veicoli',sub:'Attraversamento pedonale in attesa',duration:18,light:'green'},{name:'Transizione',sub:'Chiusura del flusso veicolare',duration:3,light:'amber'},{name:'Verde pedoni',sub:'Attraversamento protetto',duration:12,light:'red'},{name:'Sgombero',sub:'Verifica delle strisce prima del verde',duration:4,light:'red'}];
const unstableAfterMs=4000,offlineAfterMs=10000;
class HardwareProvider {
  constructor(emit=()=>{}, transport=globalThis.fetch?.bind(globalThis), clock=()=>Date.now()) {
    this.emit=emit;this.transport=transport;this.clock=clock;this.data=null;this.received=0;this.disposed=false;this.busy=false;
  }
  snapshot(){
    const d=this.data,s=d?.state;
    const age=s?this.clock()-this.received+(d.age_ms??offlineAfterMs):Infinity;
    const scenario=age<unstableAfterMs?'hardware':age<offlineAfterMs?'unstable':'offline';
    const available=scenario!=='offline';
    const map={VEHICLE_GREEN:0,VEHICLE_YELLOW:1,ALL_RED_TO_PED:1,PED_GREEN:2,PED_CLEARANCE:3,ALL_RED_TO_VEH:3,PROTECTED_STOP:3,FAULT:3};
    const lights={RED:'red',YELLOW:'amber',GREEN:'green',OFF:'off'};
    return {source:'hardware',outputs:available?{vehicle:lights[s.vehicle_light],pedestrian:lights[s.pedestrian_light]}:null,phase:map[s?.phase]??0,elapsed:0,seq:s?.applied_frame??0,paused:false,scenario,left:null,right:null,completed:null,waitSamples:[],extended:false,phases,rt:available?s:null,remaining:available&&s.remaining_ms!==null?Math.max(0,Math.ceil((s.remaining_ms-(this.clock()-this.received))/1000)):null};
  }
  async tick(){
    if(this.busy||this.disposed||!this.transport)return this.snapshot();
    this.busy=true;
    try{const response=await this.transport('/api/rt',{cache:'no-store'});if(!response.ok)throw Error('HTTP');const data=await response.json();if(!this.disposed&&data?.connected&&data.state){this.data=data;this.received=this.clock();}}
    catch(e){}finally{this.busy=false;}
    return this.snapshot();
  }
  async request(type,requestId){
    if(this.snapshot().scenario!=='hardware'||!this.transport)return {status:'rejected',reason:'Telemetria non disponibile'};
    try{const response=await this.transport('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,request_id:requestId})});const result=await response.json();return response.ok?result:{status:'rejected',reason:result.error};}
    catch(e){return {status:'rejected',reason:'Collegamento interrotto'};}
  }
  dispose(){this.disposed=true;this.data=null;}
}
