"""Host-only HTTP -> RTService -> native STM32 sketch integration check."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'dashboard'))
sys.path.insert(0, str(root/'firmware'/'python'))
from rt import RTService
from server import Handler
from layout import LayoutStore
from cycle_demo import start_demo


class QuietHandler(Handler):
    def log_message(self, *args): pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arduino-json', type=Path, required=True, help='Directory containing ArduinoJson.h (7.4.3)')
    parser.add_argument('--compiler', default='g++')
    args = parser.parse_args()
    build = root/'.local'/'cycle-check'
    build.mkdir(parents=True, exist_ok=True)
    runner = build/('native_bridge.exe' if sys.platform == 'win32' else 'native_bridge')
    subprocess.run([args.compiler, '-std=c++11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                    '-DCROSSSENSE_STANDARD_CYCLE=1', '-I', str(args.arduino_json.resolve()),
                    '-I', str(root/'firmware'/'tests'/'stubs'),
                    str(root/'firmware'/'tests'/'native_bridge.cpp'), '-o', str(runner)], check=True)
    process = subprocess.Popen([str(runner)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    began = time.monotonic()
    def call(method, payload):
        assert method == 'crosssense_update'
        now = int((time.monotonic()-began)*1000)
        process.stdin.write(f'{now} {payload}\n')
        process.stdin.flush()
        response = process.stdout.readline().strip()
        if not response: raise RuntimeError('Native sketch runner terminated')
        return response
    rt = RTService(call)
    handler = partial(QuietHandler, directory=str(root/'dashboard'/'static'))
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        server.rt = rt
        server.layout = LayoutStore(build/'integration-layout.json')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start();rt.start()
        try:
            print('HOST SIMULATION: RouterBridge replaced; actual sketch, HTTP API and automatic Linux trial, zero GPIO.', flush=True)
            demo, result = start_demo(server)
            demo.join(timeout=85)
            if demo.is_alive() or not result['ok']:
                raise RuntimeError(f'Automatic trial failed: {result["error"]}')
            print('HTTP_SKETCH_OK: automatic two cycles, Bridge v1 telemetry and stop, zero GPIO.', flush=True)
        finally:
            rt.stop.set()
            server.shutdown();thread.join(timeout=3)
            rt.thread.join(timeout=3)
            process.stdin.close()
            process.wait(timeout=3)
            process.stdout.close()
            if process.returncode != 0: raise RuntimeError(f'Native runner failed: {process.returncode}')


if __name__ == '__main__':
    main()
