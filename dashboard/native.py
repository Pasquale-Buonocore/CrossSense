"""Run the same C++ sketch on a host PC. No Python copy of the controller."""
from pathlib import Path
import queue
import subprocess
import threading
import time
import json
import sys


class NativeController:
    def __init__(self, executable, timeout=.25):
        self.executable = str(Path(executable).resolve())
        self.command = [self.executable]
        self.handshake = False
        self.resets = 0
        self.timeout = timeout
        self.process = None
        self.began = time.monotonic()

    def _start(self):
        self.began = time.monotonic()
        self.process = subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,bufsize=1)
        self.responses = queue.Queue(maxsize=1)
        process, responses = self.process,self.responses
        def read():
            try:
                for line in process.stdout:
                    responses.put(line)
            finally:
                try: responses.put_nowait(None)
                except queue.Full: pass
        self.reader = threading.Thread(target=read,daemon=True)
        self.reader.start()
        if self.handshake:
            try:
                if self.responses.get(timeout=5) != 'READY\n': raise RuntimeError('Runtime Bridge non disponibile')
            except (queue.Empty, RuntimeError) as exc:
                self.close()
                raise RuntimeError('Avvio runtime Bridge fallito') from exc

    def encode(self, method, payload):
        return f'{int((time.monotonic()-self.began)*1000)} {payload}\n'

    def decode(self, response):
        return response.strip()

    def __call__(self, method, payload):
        if method != 'crosssense_update': raise ValueError('RPC sconosciuta')
        if self.process is None: self._start()
        try:
            self.process.stdin.write(self.encode(method,payload))
            self.process.stdin.flush()
            response = self.responses.get(timeout=self.timeout)
            if response is None: raise RuntimeError('Controller nativo terminato')
            return self.decode(response)
        except (queue.Empty, OSError, RuntimeError) as exc:
            self.close()
            raise RuntimeError('Trasporto controller indisponibile o timeout; riavvio al prossimo scambio') from exc

    def close(self):
        if self.process is not None:
            self.process.kill()
            self.process.wait(timeout=2)
            self.process.stdin.close()
            self.reader.join(timeout=2)
            self.process.stdout.close()
            self.process = None
            self.resets += 1


class BridgeController(NativeController):
    """Isolate the blocking Arduino SDK; a failed child never stalls RTService."""
    def __init__(self):
        super().__init__(sys.executable)
        self.command = [sys.executable,'-u',str(Path(__file__).with_name('bridge_worker.py'))]
        self.handshake = True

    def encode(self, method, payload):
        return json.dumps([method,payload])+'\n'

    def decode(self, response):
        value=json.loads(response)
        if 'error' in value: raise RuntimeError(value['error'])
        return value['result']
