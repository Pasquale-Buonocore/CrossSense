"""Bridge v1 adapter. One worker owns RPC; browser reads a timestamped cache."""
import copy
import json
import secrets
import threading
import time
from collections import deque

LIMIT = 900
PHASES = ('VEHICLE_GREEN', 'VEHICLE_YELLOW', 'ALL_RED_TO_PED', 'PED_GREEN', 'PED_CLEARANCE', 'ALL_RED_TO_VEH', 'PROTECTED_STOP', 'FAULT')
ALARMS = ('CROSSING_CONFLICT', 'COLLISION_RISK', 'PEDESTRIAN_STOPPED', 'CLEARANCE_TIMEOUT')


def integer(value, low=0, high=0xffffffff):
    return type(value) is int and low <= value <= high


def encode(value):
    data = json.dumps(value, separators=(',', ':'), allow_nan=False)
    if len(data.encode('utf-8')) > LIMIT:
        raise ValueError('Payload oltre 900 byte')
    return data


def validate_frame(f):
    if not isinstance(f, dict) or set(f) != {'stream','frame','time_ms','age_ms','valid','crossing','approach','tracks','requests'}:
        raise ValueError('Campi frame non validi')
    if not integer(f['stream']) or not integer(f['frame']) or type(f['valid']) is not bool:
        raise ValueError('Identità frame non valida')
    if f['crossing'] not in ('occupied','clear','unknown') or f['approach'] not in ('present','clear','unknown'):
        raise ValueError('Stati ROI non validi')
    if not isinstance(f['requests'], list) or len(f['requests']) != 3 or any(type(x) is not bool for x in f['requests']):
        raise ValueError('Richieste non valide')
    if not isinstance(f['tracks'], list) or len(f['tracks']) > 8:
        raise ValueError('Massimo 8 tracce')
    ids = set()
    for t in f['tracks']:
        if not isinstance(t, list) or len(t) != 5 or not integer(t[0], 1) or t[0] in ids or t[1] not in ('pedestrian','bicycle','vehicle','other') or t[2] not in ('waiting_left','waiting_right','crossing','approach','outside'):
            raise ValueError('Traccia non valida')
        ids.add(t[0])
        if not (t[3] is None and t[4] is None) and not all(integer(v,-1000000,1000000) for v in t[3:]):
            raise ValueError('Coordinate non valide')
        if (t[1] != 'vehicle' and t[2] == 'crossing' and f['crossing'] == 'clear') or (t[1] == 'vehicle' and t[2] == 'approach' and f['approach'] == 'clear'):
            raise ValueError('Traccia e ROI incoerenti')
    if f['time_ms'] is None:
        if f['age_ms'] is not None or f['valid'] or f['tracks'] or f['crossing'] != 'unknown' or f['approach'] != 'unknown':
            raise ValueError('Frame senza immagine incoerente')
    elif not integer(f['time_ms'],0,2**53-1) or not integer(f['age_ms']):
        raise ValueError('Tempi non validi')
    if not f['valid'] and ('clear' in (f['crossing'],f['approach'])):
        raise ValueError('Frame invalido non può dichiarare clear')
    if f['valid'] and 'unknown' in (f['crossing'],f['approach']):
        raise ValueError('Frame valido richiede ROI note')
    encode(f)
    return f


def validate_state(raw, frame):
    if not isinstance(raw, str) or len(raw.encode()) > LIMIT:
        raise ValueError('Risposta Bridge non valida')
    s = json.loads(raw)
    keys = {'frame','ok','error','applied_stream','applied_frame','uptime_ms','phase','remaining_ms','vehicle_light','pedestrian_light','buzzer','beacon','observation_valid','fault','alarms','estimates'}
    if not isinstance(s,dict) or set(s) != keys or not integer(s['frame']) or s['frame'] != frame or type(s['ok']) is not bool:
        raise ValueError('Risposta non corrispondente al frame')
    if (s['ok'] and s['error'] is not None) or (not s['ok'] and s['error'] not in ('BAD_DATA','OLD_FRAME','STALE_FRAME','BUSY')):
        raise ValueError('Esito non valido')
    if not ((s['applied_stream'] is None and s['applied_frame'] is None) or (integer(s['applied_stream']) and integer(s['applied_frame']))):
        raise ValueError('Frame applicato non valido')
    if not integer(s['uptime_ms']) or s['phase'] not in PHASES or (s['remaining_ms'] is not None and not integer(s['remaining_ms'])):
        raise ValueError('Fase o tempi non validi')
    if any(s[k] not in ('RED','YELLOW','GREEN','OFF') for k in ('vehicle_light','pedestrian_light')) or any(type(s[k]) is not bool for k in ('buzzer','beacon','observation_valid')):
        raise ValueError('Uscite non valide')
    if s['fault'] not in (None,'NO_DATA','INVALID_DATA','TIMEOUT') or not isinstance(s['alarms'],list) or len(s['alarms']) > 4 or any(a not in ALARMS for a in s['alarms']) or len(set(s['alarms'])) != len(s['alarms']):
        raise ValueError('Guasti/allarmi non validi')
    if not isinstance(s['estimates'],list) or len(s['estimates']) > 8:
        raise ValueError('Stime non valide')
    ids = set()
    for e in s['estimates']:
        if not isinstance(e,list) or len(e) != 5 or not integer(e[0],1) or e[0] in ids:
            raise ValueError('Stima non valida')
        ids.add(e[0])
        for v,lo,hi in zip(e[1:],(-1000000,-1000000,0,0),(1000000,1000000,600000,1000000)):
            if v is not None and not integer(v,lo,hi):
                raise ValueError('Stima fuori intervallo')
    encode(s)
    return s


class RTService:
    def __init__(self, call=None, clock=time.monotonic):
        self.call, self.clock = call, clock
        self.lock = threading.Lock()
        self.latest = None
        self.stream = secrets.randbits(32)
        self.sequence = 0
        self.requests = [False]*3
        self.lowering = False
        self.state = None
        self.received = None
        self.error = 'Bridge non configurato' if call is None else None
        self.stop = threading.Event()
        self.seen = {}
        self.thread = None
        self.in_flight = False
        self.last_wire = None
        self.rpc_ms = None
        self.events = deque(maxlen=100)
        self.event_sequence = 0

    def event(self, kind, message):
        self.event_sequence += 1
        self.events.append({'id':self.event_sequence,'type':kind,'message':message})

    def cancel_requests(self, reason):
        for result in self.seen.values():
            if result['status'] not in ('served','cancelled'):
                result.update(status='cancelled',reason=reason)
        self.requests = [False]*3
        self.lowering = False

    def publish(self, frame):
        f = copy.deepcopy(validate_frame(frame))
        if any(f['requests']):
            raise ValueError('Le richieste appartengono al servizio dashboard')
        with self.lock:
            if self.latest and f['stream'] == self.latest[0]['stream']:
                old = self.latest[0]
                delta = (f['frame']-old['frame']) & 0xffffffff
                if not 0 < delta < 0x80000000 or (f['time_ms'] is not None and old['time_ms'] is not None and f['time_ms'] <= old['time_ms']):
                    raise ValueError('Frame vecchio o duplicato')
            elif self.latest:
                self.cancel_requests('Sorgente o configurazione cambiata')
                self.stream = secrets.randbits(32)
                self.sequence = 0
            self.latest = (f,self.clock())

    def snapshot(self):
        with self.lock:
            age = None if self.received is None else max(0,round((self.clock()-self.received)*1000))
            return {'connected':self.call is not None and age is not None and age < 1000 and self.error is None,'age_ms':age,'state':copy.deepcopy(self.state),'error':self.error,'rpc_ms':self.rpc_ms,'sent_age_ms':self.last_wire.get('age_ms') if self.last_wire else None,
                    'requests':copy.deepcopy(list(self.seen.values())), 'events':list(self.events)}

    def request(self, kind, request_id):
        if kind not in ('pedestrian','accessible','vehicle_priority') or not isinstance(request_id,str) or not 1 <= len(request_id) <= 80:
            raise ValueError('Richiesta non valida')
        with self.lock:
            if request_id in self.seen:
                return self.seen[request_id]
            if self.call is None or self.received is None or self.clock()-self.received >= 1 or self.error is not None:
                return {'status':'rejected','reason':'Telemetria non disponibile'}
            self.requests[('pedestrian','accessible','vehicle_priority').index(kind)] = True
            if kind == 'accessible': self.requests[0] = True
            result = {'status':'queued','requestId':request_id,'type':kind}
            self.seen[request_id] = result
            if len(self.seen) > 256: self.seen.pop(next(iter(self.seen)))
            return result

    def exchange(self):
        if self.call is None: return
        with self.lock:
            if self.latest is None:
                self.sequence = (self.sequence+1) & 0xffffffff
                f = dict(stream=self.stream,frame=self.sequence,time_ms=None,age_ms=None,valid=False,crossing='unknown',approach='unknown',tracks=[],requests=[False]*3)
            else:
                f, captured = self.latest
                f = copy.deepcopy(f)
                if f['age_ms'] is not None: f['age_ms'] = min(0xffffffff,f['age_ms']+round((self.clock()-captured)*1000))
                # Poll telemetry by retrying the identical wire frame. The MCU
                # acknowledges duplicates without applying them or renewing its
                # watchdog. A changed request needs a new acquisition/message.
                self.sequence = (self.sequence+1) & 0xffffffff
                if getattr(self,'last_sent',None) == (f['stream'],f['frame']):
                    if self.last_wire is not None:
                        age = f['age_ms']
                        f = copy.deepcopy(self.last_wire)
                        if f['time_ms'] is not None: f['age_ms'] = age
                    else:
                        f = dict(stream=self.stream,frame=self.sequence,time_ms=None,age_ms=None,valid=False,crossing='unknown',approach='unknown',tracks=[],requests=[False]*3)
                else:
                    self.last_sent = (f['stream'],f['frame'])
                    f['stream'], f['frame'] = self.stream, self.sequence
            # Duplicate acquisitions keep identical request levels. A button
            # waits for the next real frame instead of injecting INVALID_DATA.
            duplicate = self.last_wire is not None and (f['stream'],f['frame']) == (self.last_wire['stream'],self.last_wire['frame'])
            if not duplicate: f['requests'] = [False]*3 if self.lowering else list(self.requests)
            levels = list(f['requests'])
            if not duplicate:
                self.wire_request_ids = [key for key,r in self.seen.items() if r['status']=='queued' and levels[('pedestrian','accessible','vehicle_priority').index(r['type'])]]
                self.wire_acknowledged = False
            request_ids = list(getattr(self,'wire_request_ids',[]))
            source_stream = self.stream
            self.last_wire = copy.deepcopy(f)
            self.in_flight = True
        start = self.clock()
        transport_resets = getattr(self.call,'resets',0)
        try:
            s = validate_state(self.call('crosssense_update',encode(validate_frame(f))),f['frame'])
            self.rpc_ms = round((self.clock()-start)*1000,1)
            if self.rpc_ms > 250:
                raise ValueError('RPC oltre budget 250 ms')
            with self.lock:
                if source_stream != self.stream:
                    return  # Response belongs to a source invalidated mid-call.
                if self.state is not None and 0 < ((self.state['uptime_ms']-s['uptime_ms']) & 0xffffffff) < 0x80000000:
                    self.cancel_requests('Controller riavviato')
                    self.stream = secrets.randbits(32)
                    self.last_sent = None
                    self.event('RESTART','Controller riavviato: richieste annullate')
                    request_ids = []
                previous_phase = self.state['phase'] if self.state else None
                previous_alarms = set(self.state['alarms']) if self.state else set()
                if s['phase'] != previous_phase: self.event('PHASE',s['phase'])
                for alarm in set(s['alarms'])-previous_alarms: self.event('ALARM',alarm)
                self.state, self.received, self.error = s,self.clock(),None
                if s['ok'] and not getattr(self,'wire_acknowledged',False):
                    self.wire_acknowledged = True
                    for key in request_ids:
                        self.seen[key].update(status='accepted',stream=f['stream'],frame=f['frame'])
                    if any(levels):
                        self.lowering = True
                    else: self.lowering = False
                    # A click may arrive while this RPC is running or while
                    # the previous edge is being lowered. Keep those queued
                    # commands for the next edge instead of dropping them.
                    self.requests = [False]*3
                    for result in self.seen.values():
                        if result['status']=='queued':
                            self.requests[('pedestrian','accessible','vehicle_priority').index(result['type'])] = True
                            if result['type']=='accessible': self.requests[0] = True
                for result in self.seen.values():
                    if result['status']=='accepted' and result['stream']==s['applied_stream'] and s['applied_frame'] is not None and ((s['applied_frame']-result['frame']) & 0xffffffff)<0x80000000:
                        result['status']='applied'
                    if result['status']=='applied' and s['observation_valid'] and ((result['type']=='vehicle_priority' and s['phase']=='VEHICLE_GREEN') or (result['type']!='vehicle_priority' and s['phase']=='PED_GREEN' and previous_phase!='PED_GREEN')):
                        result['status']='served'
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                if getattr(self.call,'resets',0) != transport_resets:
                    self.cancel_requests('Trasporto riavviato')
                    self.stream = secrets.randbits(32)
                    self.last_sent = None
                    self.event('RESTART','Trasporto riavviato: recupero con nuovo stream')
        finally:
            with self.lock: self.in_flight = False

    def start(self):
        if self.call is None: return
        def run():
            while not self.stop.is_set():
                began = self.clock()
                self.exchange()  # Blocking RPC never spawns another in-flight call.
                self.stop.wait(max(0,.2-(self.clock()-began)))
        self.thread = threading.Thread(target=run,daemon=True)
        self.thread.start()
