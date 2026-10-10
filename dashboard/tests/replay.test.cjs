const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),events=[];
function $(id){if(!nodes.has(id))nodes.set(id,{style:{},classList:{toggle(){}},textContent:''});return nodes.get(id);}
const context={$ ,Date,provider:{data:{rpc_ms:20,events:[{id:1,type:'ALARM',message:'CROSSING_CONFLICT'}],requests:[{requestId:'a',status:'served'}]}},event:(...e)=>events.push(e),visionView:{receivedAt:Date.now(),data:{fresh:true,age_ms:0,metrics:{completed:2,left_to_right:1,right_to_left:1,average_wait_ms:1500,stopped_ids:[3],events:[{id:1,track_id:3,direction:'left_to_right'}]}}}};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../static/replay.js'),'utf8'),context);
context.replayDashboard.requestId='a';
const snapshot={source:'hardware',scenario:'hardware',rt:{alarms:['CROSSING_CONFLICT']}};
context.replayDashboard.render(snapshot);context.replayDashboard.render(snapshot);
assert.equal($('count').textContent,2);assert.equal($('avg').textContent,'1.5 s');
assert.equal(events.length,2,'events deduplicated across renders');
assert.match($('alarm-status').textContent,/IMMOBILITÀ/);assert.equal($('request-status').textContent,'Richiesta servita');
context.replayDashboard.render({...snapshot,scenario:'offline',rt:null});
assert.equal($('alarm-status').textContent,'Controller non disponibile');
console.log('REPLAY_UI_OK: real metrics, alarms, command outcome and deduplicated events');
