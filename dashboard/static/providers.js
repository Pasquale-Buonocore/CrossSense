'use strict';
// Providers own data and actions. Neither provider depends on the DOM.
const phases = [{name:'Verde veicoli',sub:'Attraversamento pedonale in attesa',duration:18,light:'green'},{name:'Transizione',sub:'Chiusura del flusso veicolare',duration:3,light:'amber'},{name:'Verde pedoni',sub:'Attraversamento protetto',duration:12,light:'red'},{name:'Sgombero',sub:'Verifica delle strisce prima del verde',duration:4,light:'red'}];
class DemoProvider {
  constructor(emit = () => {}) { this.emit=emit; this.reset(); }
  reset() { this.state={phase:0,elapsed:0,seq:0,paused:false,scenario:'normal',left:0,right:0,completed:0,pending:[],waitSamples:[],extended:false}; }
  snapshot() { return {...this.state, source:'demo', phases, waitSamples:[...this.state.waitSamples]}; }
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
  // Deliberately disconnected until a transport and validated contract exist.
  snapshot(){return {source:'hardware',phase:0,elapsed:0,seq:0,paused:false,scenario:'offline',left:null,right:null,completed:null,waitSamples:[],extended:false,phases};}
  tick(){return this.snapshot();}
  request(){return {status:'rejected',reason:'API hardware non configurata'};}
  dispose() {}
}
