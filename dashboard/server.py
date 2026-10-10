"""Local dashboard with an optional, browser-independent Bridge v1 worker."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from rt import RTService


class Handler(SimpleHTTPRequestHandler):
    def reply(self, value, status=200):
        raw = json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/api/rt': self.reply(self.server.rt.snapshot())
        else: super().do_GET()

    def do_POST(self):
        # Reject browser cross-origin writes, including form submissions.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host',''):
            return self.reply({'error':'Origine non consentita'},403)
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            return self.reply({'error':'Richiesto JSON'},415)
        try:
            size = int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 4096: raise ValueError('Dimensione richiesta non valida')
            data = json.loads(self.rfile.read(size))
            if self.path == '/api/observations':
                self.server.rt.publish(data)
                self.reply({'status':'buffered'})
            elif self.path == '/api/requests':
                self.reply(self.server.rt.request(data.get('type'),data.get('request_id')))
            else: self.reply({'error':'Endpoint sconosciuto'},404)
        except (ValueError,TypeError,AttributeError) as exc:
            self.reply({'error':str(exc)},400)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8080)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--bridge',action='store_true',help='Usa arduino.app_utils sulla UNO Q')
    args = parser.parse_args()
    call = None
    if args.bridge:
        from arduino.app_utils import Bridge
        call = Bridge.call
    rt = RTService(call)
    handler = partial(Handler,directory=str(Path(__file__).parent/'static'))
    with ThreadingHTTPServer((args.host,args.port),handler) as server:
        server.rt = rt
        rt.start()
        print(f'CrossSense: http://{args.host}:{args.port}',flush=True)
        try: server.serve_forever()
        finally: rt.stop.set()


if __name__ == '__main__': main()
