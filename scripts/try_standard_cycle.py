"""Exercise STM32 through the dashboard HTTP API using synthetic observations."""
import argparse
import json
import secrets
import socket
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


PHASES = ('VEHICLE_GREEN', 'VEHICLE_YELLOW', 'ALL_RED_TO_PED',
          'PED_GREEN', 'PED_CLEARANCE', 'ALL_RED_TO_VEH', 'VEHICLE_GREEN')
LIGHTS = {
    'VEHICLE_GREEN': ('GREEN', 'RED'),
    'VEHICLE_YELLOW': ('YELLOW', 'RED'),
    'ALL_RED_TO_PED': ('RED', 'RED'),
    'PED_GREEN': ('RED', 'GREEN'),
    'PED_CLEARANCE': ('RED', 'RED'),
    'ALL_RED_TO_VEH': ('RED', 'RED'),
    'PROTECTED_STOP': ('RED', 'RED'),
    'FAULT': ('RED', 'RED'),
}


class APIClient:
    def __init__(self, url, http_timeout=1.0):
        self.url = url.rstrip('/')
        self.http_timeout = http_timeout
        self.stream = secrets.randbits(32)
        self.sequence = 0
        self.capture_time = -1

    def call(self, path, data=None):
        raw = None if data is None else json.dumps(data, separators=(',', ':')).encode()
        request = Request(self.url+path, data=raw, headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=self.http_timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f'{path}: HTTP {exc.code}: {exc.read().decode(errors="replace")}') from exc
        except URLError as exc:
            if isinstance(exc.reason, socket.gaierror):
                host = urlsplit(self.url).hostname
                raise RuntimeError(f'Host {host!r} non risolvibile. Usare l\'IP reale della UNO Q; IP-DELLA-UNO-Q è un segnaposto. Nello ZIP aggiornato la prova parte automaticamente su 127.0.0.1.') from exc
            raise RuntimeError(f'{path}: {exc}') from exc
        except (TimeoutError, OSError, ValueError) as exc:
            raise RuntimeError(f'{path}: {exc}') from exc

    def observe(self, valid=True):
        self.sequence = (self.sequence+1) & 0xffffffff
        # Monotonic acquisition timestamps; HTTP retries are not new images.
        self.capture_time = max(self.capture_time+1, time.monotonic_ns()//1_000_000)
        frame = dict(stream=self.stream, frame=self.sequence,
                     time_ms=self.capture_time if valid else None,
                     age_ms=0 if valid else None, valid=valid,
                     crossing='clear' if valid else 'unknown',
                     approach='clear' if valid else 'unknown',
                     tracks=[], requests=[False, False, False])
        result = self.call('/api/observations', frame)
        if result.get('status') != 'buffered':
            raise RuntimeError(f'Osservazione non accettata: {result}')

    def snapshot(self):
        return self.call('/api/rt')

    def request(self, request_id):
        return self.call('/api/requests', {'type': 'pedestrian', 'request_id': request_id})


def checked_state(snapshot):
    if not snapshot.get('connected') or not isinstance(snapshot.get('state'), dict):
        raise RuntimeError(f'Telemetria non disponibile: {snapshot.get("error")}')
    state = snapshot['state']
    phase = state.get('phase')
    outputs = (state.get('vehicle_light'), state.get('pedestrian_light'))
    if phase not in LIGHTS or outputs != LIGHTS[phase]:
        raise RuntimeError(f'Uscite incoerenti: fase={phase}, luci={outputs}')
    return state


def run_cycle(client, cycles=1, timeout=45.0, clock=time.monotonic,
              sleep=time.sleep, emit=print):
    began = clock()
    last_connected = began
    last_phase = None
    position = None
    completed = 0
    queued = False
    request_id = uuid.uuid4().hex
    emit('SYNTHETIC: ROI libere simulate, nessuna camera. Controllo fasi sulla STM32.', flush=True)
    while clock()-began < timeout:
        lap = clock()
        # 10 Hz producer, above the dashboard worker's 5 Hz. Each sample is new.
        client.observe()
        snapshot = client.snapshot()
        if not snapshot.get('connected'):
            if clock()-last_connected > 3:
                raise RuntimeError(f'Bridge/telemetria non disponibile: {snapshot.get("error")}. Avviare il server con --bridge sulla UNO Q.')
            sleep(0.1)
            continue
        last_connected = clock()
        state = checked_state(snapshot)
        phase = state['phase']
        if phase != last_phase:
            emit(f'PHASE {phase} vehicle={state["vehicle_light"]} pedestrian={state["pedestrian_light"]} remaining_ms={state.get("remaining_ms")}', flush=True)
            last_phase = phase
        if position is None:
            if phase == 'PROTECTED_STOP' and clock()-began > 3:
                raise RuntimeError('Firmware in modalità protetta: preparare/caricare il pacchetto con --standard-cycle.')
            if phase == 'VEHICLE_GREEN':
                position = 0
        else:
            if not state.get('observation_valid') or state.get('fault') is not None or state.get('alarms'):
                raise RuntimeError(f'Ciclo interrotto da guasto/allarme: {state}')
            if not state.get('ok'):
                raise RuntimeError(f'Frame Bridge rifiutato: {state.get("error")}')
            if phase != PHASES[position]:
                if position == 0 and not queued:
                    raise RuntimeError('Transizione pedonale senza conferma della richiesta della prova')
                if phase != PHASES[position+1]:
                    raise RuntimeError(f'Sequenza inattesa: {PHASES[position]} -> {phase}')
                position += 1
                if position == len(PHASES)-1:
                    completed += 1
                    emit(f'CYCLE_OK {completed}/{cycles}', flush=True)
                    if completed == cycles:
                        return
                    position, queued = 0, False
                    request_id = uuid.uuid4().hex
        if position == 0 and not queued:
            result = client.request(request_id)
            if result.get('status') == 'queued':
                queued = True
                emit(f'REQUEST_QUEUED id={request_id} (in attesa del verde pedonale MCU)', flush=True)
            elif result.get('status') != 'rejected':
                raise RuntimeError(f'Risposta richiesta inattesa: {result}')
            # Rejected during an RPC/reset: retry the same ID on the next sample.
        sleep(max(0, 0.1-(clock()-lap)))
    raise RuntimeError(f'Tempo massimo {timeout:g}s superato: completati {completed}/{cycles} cicli, ultima fase {last_phase}')


def check_watchdog(client, clock=time.monotonic, sleep=time.sleep, emit=print):
    # No new samples. The dashboard reports unavailable; MCU must close greens.
    began = clock()
    while clock()-began < 3:
        state = checked_state(client.snapshot())
        if state['phase'] == 'FAULT' and not state.get('observation_valid') and state.get('fault') in ('TIMEOUT', 'INVALID_DATA'):
            emit(f'STOP_OK fault={state["fault"]} vehicle=RED pedestrian=RED', flush=True)
            return
        sleep(0.1)
    raise RuntimeError('Arresto per perdita osservazioni non confermato entro 3s')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080', help='URL dashboard della UNO Q')
    parser.add_argument('--cycles', type=int, default=1)
    parser.add_argument('--timeout', type=float, help='Tempo massimo totale della prova, in secondi')
    args = parser.parse_args()
    if args.cycles < 1 or (args.timeout is not None and args.timeout <= 0):
        parser.error('cycles e timeout devono essere positivi')
    client = APIClient(args.url)
    try:
        run_cycle(client, args.cycles, args.timeout or (10+35*args.cycles))
        check_watchdog(client)
        return 0
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(f'CYCLE_ERROR: {exc or "interrotto"}', file=sys.stderr, flush=True)
        return 1
    finally:
        try:
            client.observe(valid=False)
        except RuntimeError:
            pass  # MCU watchdog also handles an unavailable HTTP connection.


if __name__ == '__main__':
    sys.exit(main())
