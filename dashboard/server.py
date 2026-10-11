"""Local dashboard with an optional, browser-independent Bridge v1 worker."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rt import RTService
from layout import LayoutStore
from vision.zones import ZoneStore, RevisionConflict
from vision.pipeline import VisionService


class Handler(SimpleHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        # Keep MCU phase/trial messages visible instead of logging each 5/10 Hz poll.
        if code == 200 and (self.path in ('/api/rt','/api/observations','/api/trial','/api/vision','/api/vision/zones') or self.path.startswith('/api/vision/frame.jpg')):
            return
        super().log_request(code,size)

    def end_headers(self):
        # App updates must not reuse an old dashboard/provider from the browser cache.
        self.send_header('Cache-Control','no-store')
        super().end_headers()

    def reply(self, value, status=200):
        raw = json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        vision = getattr(self.server,'vision',None)
        path = urlsplit(self.path)
        if path.path.startswith('/api/vision'):
            if vision is None: return self.reply({'available':False,'status':'unavailable'})
            if path.path == '/api/vision': return self.reply(vision.snapshot())
            if path.path == '/api/vision/zones': return self.reply(vision.zones.snapshot())
            if path.path == '/api/vision/frame.jpg':
                try: raw = vision.image(int(parse_qs(path.query).get('serial',[''])[0]))
                except ValueError: raw = None
                if raw is None: return self.reply({'error':'Frame non più disponibile'},404)
            elif path.path == '/api/vision/reference.jpg':
                raw = (Path(__file__).resolve().parents[1]/'vision'/'config'/'reference.jpg').read_bytes()
            else: return self.reply({'error':'Endpoint sconosciuto'},404)
            self.send_response(200)
            self.send_header('Content-Type','image/jpeg')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == '/api/config':
            self.reply({'default_mode':'replay','camera_available':bool(vision and vision.camera_enabled),
                        'controller':getattr(self.server,'controller_kind','bridge' if self.server.rt.call else 'none')})
        elif self.path == '/api/trial':
            trial = getattr(self.server,'trial',None)
            self.reply(trial.snapshot() if trial is not None else {'available':False,'status':'unavailable'})
        elif self.path == '/api/signal-layout': self.reply(self.server.layout.snapshot())
        elif self.path == '/api/rt': self.reply(self.server.rt.snapshot())
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
            if not 0 < size <= (16384 if self.path == '/api/vision/zones' else 4096): raise ValueError('Dimensione richiesta non valida')
            data = json.loads(self.rfile.read(size))
            vision = getattr(self.server,'vision',None)
            if self.path == '/api/vision/zones':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                self.reply(vision.configure(data))
            elif self.path == '/api/vision/source':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                self.reply(vision.select_video(data))
            elif self.path == '/api/vision/mode':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                self.reply(vision.select_mode(data))
            elif self.path == '/api/vision/play':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                if data != {}: raise ValueError('Play richiede un oggetto JSON vuoto')
                self.reply(vision.play())
            elif self.path == '/api/vision/pause':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                if data != {}: raise ValueError('Pausa richiede un oggetto JSON vuoto')
                self.reply(vision.pause())
            elif self.path == '/api/vision/stop':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                if data != {}: raise ValueError('Stop richiede un oggetto JSON vuoto')
                self.reply(vision.stop_playback())
            elif self.path == '/api/vision/restart':
                if vision is None: return self.reply({'error':'Visione non configurata'},409)
                if data != {}: raise ValueError('Il riavvio richiede un oggetto JSON vuoto')
                self.reply(vision.restart())
            elif self.path == '/api/trial':
                if vision and (vision.video is not None or vision.mode == 'camera'): return self.reply({'error':'La visione YOLO è la sorgente attiva'},409)
                trial = getattr(self.server,'trial',None)
                if trial is None: return self.reply({'error':'Prova sintetica non disponibile'},409)
                if data != {}: raise ValueError('La prova richiede un oggetto JSON vuoto')
                result = trial.start()
                self.reply(result,409 if result['status']=='rejected' else 200)
            elif self.path == '/api/signal-layout':
                self.reply(self.server.layout.update(data))
            elif self.path == '/api/observations':
                if vision and (vision.video is not None or vision.mode == 'camera'): return self.reply({'error':'Le osservazioni sono prodotte dalla visione YOLO'},409)
                self.server.rt.publish(data)
                self.reply({'status':'buffered'})
            elif self.path == '/api/requests':
                self.reply(self.server.rt.request(data.get('type'),data.get('request_id')))
            else: self.reply({'error':'Endpoint sconosciuto'},404)
        except RevisionConflict as exc:
            self.reply({'error':str(exc)},409)
        except OSError:
            self.reply({'error':'Salvataggio sul server non riuscito'},503)
        except (ValueError,TypeError,AttributeError) as exc:
            self.reply({'error':str(exc)},400)


def main(on_ready=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8080)
    parser.add_argument('--host',default='127.0.0.1')
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument('--bridge',action='store_true',help='Usa arduino.app_utils sulla UNO Q')
    transport.add_argument('--native-controller',type=Path,help='Eseguibile dello stesso sketch compilato per PC')
    parser.add_argument('--layout-file',type=Path,default=Path(__file__).parent/'.local'/'signal-layout.json')
    parser.add_argument('--video',type=Path,help='MP4 da elaborare con YOLO26n')
    parser.add_argument('--video-dir',type=Path,help='Abilita replay e catalogo MP4 selezionabile')
    parser.add_argument('--camera',action='store_true',help='Abilita la camera CSI CAM0 su comando dalla dashboard')
    parser.add_argument('--selection-file',type=Path,default=Path(__file__).parent/'.local'/'selected-video.json')
    parser.add_argument('--model',type=Path,default=Path(__file__).resolve().parents[1]/'models'/'yolo26n.pt')
    parser.add_argument('--zones-file',type=Path,default=Path(__file__).parent/'.local'/'vision-zones.json')
    parser.add_argument('--camera-zones-file',type=Path,default=Path(__file__).parent/'.local'/'camera-zones.json')
    parser.add_argument('--loop-video',action='store_true',help='Ripeti il video con un nuovo stream e tracker')
    parser.add_argument('--device',default='cpu')
    parser.add_argument('--confidence',type=float,default=.30)
    parser.add_argument('--imgsz',type=int,default=320)
    parser.add_argument('--inference-threads',type=int,choices=range(1,5),help='Thread NCNN; lascia risorse a Bridge e dashboard')
    parser.add_argument('--frame-size','--frame-height',dest='frame_size',type=int,default=480,help='Limite di entrambi i lati dei frame elaborati, rapporto conservato')
    args = parser.parse_args()
    if not 0 < args.confidence <= 1 or not 32 <= args.imgsz <= 2048 or not 32 <= args.frame_size <= 2160: parser.error('Confidenza o risoluzione non valida')
    layout = LayoutStore(args.layout_file)
    call = None
    if args.bridge:
        from native import BridgeController
        call = BridgeController()
    elif args.native_controller:
        from native import NativeController
        if not args.native_controller.is_file(): parser.error('Controller nativo assente: eseguire scripts/build_native.py')
        call = NativeController(args.native_controller)
    rt = RTService(call)
    vision = VisionService(rt,ZoneStore(args.zones_file),args.video,args.model,args.device,args.confidence,args.imgsz,args.loop_video,frame_size=args.frame_size,video_dir=args.video_dir,selection_file=args.selection_file,inference_threads=args.inference_threads,camera_zones=ZoneStore(args.camera_zones_file),camera_enabled=args.camera)
    handler = partial(Handler,directory=str(Path(__file__).parent/'static'))
    with ThreadingHTTPServer((args.host,args.port),handler) as server:
        server.rt = rt
        server.layout = layout
        server.vision = vision
        server.controller_kind = 'native' if args.native_controller else 'bridge' if args.bridge else 'none'
        rt.start()
        vision.preload()
        print(f'CrossSense: http://{args.host}:{args.port}',flush=True)
        try:
            if on_ready is not None: on_ready(server)
            server.serve_forever()
        finally:
            vision.stop.set()
            rt.stop.set()
            if vision.thread: vision.thread.join(timeout=2)
            if vision.model_thread: vision.model_thread.join(timeout=2)
            if rt.thread: rt.thread.join(timeout=1)
            if args.native_controller or args.bridge: call.close()


if __name__ == '__main__': main()
