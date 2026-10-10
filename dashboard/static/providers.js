'use strict';
// Providers own data and actions. Neither provider depends on the DOM.
const phases = [{name:'Verde veicoli',sub:'Attraversamento pedonale in attesa',duration:18,light:'green'},{name:'Transizione',sub:'Chiusura del flusso veicolare',duration:3,light:'amber'},{name:'Verde pedoni',sub:'Attraversamento protetto',duration:12,light:'red'},{name:'Sgombero',sub:'Verifica delle strisce prima del verde',duration:4,light:'red'}];
class DemoProvider {
  constructor(emit = () => {}) { this.emit=emit; this.reset(); }
  reset() { this.state={phase:0,elapsed:0,seq:0,paused:false,scenario:'normal',left:0,right:0,completed:0,pending:[],waitSamples:[],extended:false}; }
  snapshot() { return {...this.state, source:'demo', outputs:this.state.scenario==='offline'?null:{vehicle:phases[this.state.phase].light,pedestrian:this.state.phase===2?'green':'red'}, phases, waitSamples:[...this.state.waitSamples]}; }
  tick() {
    const s=this.state;
    if(s.paused||s.scenario==='offline') return this.snapshot();
    s.seq++;s.elapsed++;
    if(s.scenario==='stopped'&&s.phase===3){s.elapsed=0;return this.snapshot();}
    const duration=phases[s.phase].duration+(s.phase===2&&s.extended?8:0);
    if(s.elapsed>=duration){
      if(s.phase===2){const n=s.scenario==='busy'?6:2;s.left+=n/2;s.right+=n/2;s.completed+=n;this.emit(`${n} attraversamenti demo completati`);}
      s.phase=(s.phase+1)%4;s.elapsed=0;
      if(s.phase===2){s.waitSamples.push(...s.pending.map(r=>s.seq-r.seq));s.pending=[];}
      if(s.phase===0)s.extended=false;
      this.emit(`Fase: ${phases[s.phase].name}`,s.phase===3);
      if(s.phase===3&&s.scenario==='stopped')this.emit('Pedone fermo: sgombero mantenuto',true);
    }
    return this.snapshot();
  }
  request(type,requestId){
    const s=this.state;
    if(s.paused||s.scenario==='offline')return {status:'rejected',reason:'Simulatore non disponibile'};
    if(!['pedestrian','accessible'].includes(type))return {status:'rejected',reason:'Tipo richiesta sconosciuto'};
    if(s.pending.some(r=>r.id===requestId))return {status:'accepted',requestId,pending:s.pending.length};
    s.pending.push({id:requestId,seq:s.seq,type});
    if(type==='accessible')s.extended=true;
    if(s.phase===0)s.elapsed=Math.max(s.elapsed,13);
    this.emit(type==='accessible'?'Richiesta accessibile accettata':'Richiesta pedonale accettata');
    return {status:'accepted',requestId,pending:s.pending.length};
  }
  setScenario(value){
    if(!['normal','busy','stopped','offline'].includes(value))return;
    const wasOffline=this.state.scenario==='offline';
    if(wasOffline&&value!=='offline'){this.state.phase=0;this.state.elapsed=0;this.state.pending=[];this.state.extended=false;this.emit('Telemetria demo ripristinata · coda azzerata');}
    this.state.scenario=value;
    this.emit(value==='offline'?'Telemetria interrotta: stato sconosciuto':`Scenario demo: ${value}`,value==='offline');
  }
  togglePause(){this.state.paused=!this.state.paused;this.emit(this.state.paused?'Simulazione in pausa':'Simulazione ripresa');}
  dispose() {}
}
class HardwareProvider {
  constructor(emit=()=>{}, transport=globalThis.fetch?.bind(globalThis), clock=()=>Date.now()) {
    this.emit=emit;this.transport=transport;this.clock=clock;this.data=null;this.received=0;this.disposed=false;this.busy=false;
  }
  snapshot(){
    const d=this.data,s=d?.state;
    const fresh=!!(d?.connected&&s&&this.clock()-this.received+(d.age_ms??1000)<1000);
    const map={VEHICLE_GREEN:0,VEHICLE_YELLOW:1,ALL_RED_TO_PED:1,PED_GREEN:2,PED_CLEARANCE:3,ALL_RED_TO_VEH:3,PROTECTED_STOP:3,FAULT:3};
    const lights={RED:'red',YELLOW:'amber',GREEN:'green',OFF:'off'};
    return {source:'hardware',outputs:fresh?{vehicle:lights[s.vehicle_light],pedestrian:lights[s.pedestrian_light]}:null,phase:map[s?.phase]??0,elapsed:0,seq:s?.applied_frame??0,paused:false,scenario:fresh?'hardware':'offline',left:null,right:null,completed:null,waitSamples:[],extended:false,phases,rt:fresh?s:null,remaining:fresh&&s.remaining_ms!==null?Math.max(0,Math.ceil((s.remaining_ms-(this.clock()-this.received))/1000)):null};
  }
  async tick(){
    if(this.busy||this.disposed||!this.transport)return this.snapshot();
    this.busy=true;
    try{const response=await this.transport('/api/rt',{cache:'no-store'});if(!response.ok)throw Error('HTTP');const data=await response.json();if(!this.disposed){this.data=data;this.received=this.clock();}}
    catch(e){this.data=null;}finally{this.busy=false;}
    return this.snapshot();
  }
  async request(type,requestId){
    if(this.snapshot().scenario==='offline'||!this.transport)return {status:'rejected',reason:'Telemetria non disponibile'};
    try{const response=await this.transport('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,request_id:requestId})});const result=await response.json();return response.ok?result:{status:'rejected',reason:result.error};}
    catch(e){return {status:'rejected',reason:'Collegamento interrotto'};}
  }
  dispose(){this.disposed=true;this.data=null;}
}
