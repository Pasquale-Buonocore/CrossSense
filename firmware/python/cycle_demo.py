"""Run the synthetic trial against this app's bound HTTP server, without DNS."""
import threading
from try_standard_cycle import APIClient, run_cycle, check_watchdog


class SyntheticTrial:
    def __init__(self, server):
        self.url = f'http://127.0.0.1:{server.server_port}'
        self.lock = threading.Lock()
        self.status = 'idle'
        self.thread = None
        self.result = {'ok': False, 'error': None}

    def snapshot(self):
        with self.lock:
            return {'available':True,'status':self.status,'cycles':2,'error':self.result['error']}

    def start(self):
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return {'status':'rejected','reason':'Prova già in corso'}
            self.status = 'running'
            self.result = {'ok': False, 'error': None}
            self.thread = threading.Thread(target=self.run, name='synthetic-cycle', daemon=True)
            self.thread.start()
        return {'status':'started'}

    def run(self):
        client = APIClient(self.url)
        try:
            run_cycle(client, cycles=2, timeout=80)
            check_watchdog(client)
            with self.lock:
                self.result['ok'] = True
                self.status = 'completed'
            print('DEMO_OK: due cicli STM32 completati; semafori dashboard rossi.', flush=True)
        except Exception as exc:
            with self.lock:
                self.result['error'] = str(exc)
                self.status = 'error'
            print(f'DEMO_ERROR: {exc}', flush=True)
        finally:
            try:
                client.observe(valid=False)
            except RuntimeError:
                pass


def start_demo(server):
    server.trial = SyntheticTrial(server)
    server.trial.start()
    return server.trial.thread, server.trial.result
