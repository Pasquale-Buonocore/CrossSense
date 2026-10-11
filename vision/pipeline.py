"""Read every MP4 frame, track with YOLO/ByteTrack, publish an atomic snapshot."""
import copy
from collections import OrderedDict, deque
from pathlib import Path
import os
import secrets
import threading
import time
from .zones import classify_position
from .sources import VideoCatalog
from .camera import CameraCapture
from .events import CrossingEvents
from .identity import IdentityTracker, deduplicate_users

CLASSES = {0:('pedestrian','PEDONE'),2:('vehicle','AUTO'),7:('vehicle','AMBULANZA')}
MAX_FPS = 5


def observation(stream, sequence, captured_ms, detections, usable=True):
    crossing = any(d['zone'] == 'crossing' and d['class'] != 'vehicle' for d in detections)
    approach = any(d['class'] == 'vehicle' and d['zone'] == 'approach' for d in detections)
    ids = [d['id'] for d in detections]
    valid = usable and len(detections) <= 8 and all(type(i) is int and 0 < i <= 0xffffffff for i in ids) and len(set(ids)) == len(ids)
    # Bboxes/confidence/pixel coordinates stay on Linux. Metric calibration is absent.
    tracks = [[d['id'],d['class'],d['zone'],None,None] for d in detections if type(d['id']) is int and 0 < d['id'] <= 0xffffffff][:8]
    if len({t[0] for t in tracks}) != len(tracks): tracks = []
    return dict(stream=stream,frame=sequence,time_ms=captured_ms,age_ms=0 if captured_ms is not None else None,
                valid=valid if captured_ms is not None else False,
                crossing='occupied' if crossing else 'clear' if valid and captured_ms is not None else 'unknown',
                approach='present' if approach else 'clear' if valid and captured_ms is not None else 'unknown',
                tracks=tracks,requests=[False]*3)


class VisionService:
    def __init__(self, rt, zones, video=None, model=None, device='cpu', confidence=.30, imgsz=320, loop=False, clock=time.monotonic, frame_size=480, video_dir=None, selection_file=None, inference_threads=None, camera_zones=None, camera_enabled=False):
        self.rt,self.zones,self.clock = rt,zones,clock
        self.zone_stores={'replay':zones,'camera':camera_zones or zones}
        self.camera_enabled=camera_enabled
        self.mode='replay'
        self.camera_calibrated=bool(camera_zones and camera_zones.path.exists())
        self.video,self.model_path = Path(video) if video else None,Path(model) if model else None
        self.catalog=VideoCatalog(video_dir,selection_file)
        self.video=self.catalog.initial(self.video)
        self.source_generation=0
        self.device,self.confidence,self.imgsz,self.loop = device,confidence,imgsz,loop
        self.frame_size = frame_size
        self.inference_threads = inference_threads
        self.lock,self.stop = threading.RLock(),threading.Event()
        self.stream,self.sequence = secrets.randbits(32),0
        self.status,self.error = 'idle',None
        self.current,self.received,self.frames = None,None,OrderedDict()
        self.serial,self.thread = 0,None
        self.model=None
        self.model_status='idle'
        self.model_error=None
        self.model_load_ms=None
        self.model_thread=None
        self.applied_revision = zones.snapshot()['revision']
        self.events = CrossingEvents()
        self.identities = IdentityTracker()

    def reset_stream(self):
        old = self.stream
        while self.stream == old: self.stream = secrets.randbits(32)
        self.sequence = 0
        self.events.reset_tracks(self.stream)
        self.identities.reset()

    def unavailable(self):
        self.sequence = (self.sequence+1)&0xffffffff
        self.rt.publish(observation(self.stream,self.sequence,None,[],False))
        self.current,self.received = None,None
        self.events.tracks.clear()
        self.events.stopped = []
        self.events.waiting = {'waiting_left': 0, 'waiting_right': 0}

    def configure(self, data):
        with self.lock:
            result = self.zones.update(data)
            if self.mode == 'camera': self.camera_calibrated=True
            self.reset_stream()
            self.unavailable()
            return result

    def select_video(self, data):
        with self.lock:
            if self.mode != 'replay': raise ValueError('Passare a Replay per scegliere un video')
            self.video=self.catalog.select(data)
            self.source_generation+=1
            self.reset_stream()
            self.unavailable()
            self.frames.clear()
            self.status,self.error='ready',None
        return self.snapshot()

    def select_mode(self, data):
        if not isinstance(data,dict) or set(data) != {'mode'} or data['mode'] not in ('replay','camera'):
            raise ValueError('Modalità richiesta non valida')
        with self.lock:
            target=data['mode']
            if target == 'camera' and not self.camera_enabled:
                raise ValueError('Telecamera non configurata nel server')
            if target == self.mode: return self.snapshot()
            self.source_generation+=1
            self.mode=target
            self.zones=self.zone_stores[target]
            self.applied_revision=self.zones.snapshot()['revision']
            self.reset_stream()
            self.unavailable()
            self.frames.clear()
            self.status,self.error=('ready' if target == 'camera' or self.video else 'idle'),None
            return self.snapshot()

    def preload(self):
        with self.lock:
            if self.model_status in ('loading','ready'):
                return
            if self.model_path is None or not (self.model_path.is_file() or (self.model_path.is_dir() and all((self.model_path/f).is_file() for f in ('model.ncnn.param','model.ncnn.bin','metadata.yaml')))):
                self.model_status='error'
                self.model_error=f'Modello locale assente: {self.model_path}'
                return
            self.model_status='loading'
            self.model_error=None
            began=self.clock()
        def load():
            try:
                os.environ['YOLO_OFFLINE']='true'
                os.environ['YOLO_AUTOINSTALL']='false'
                config_dir=Path(__file__).resolve().parents[1]/'.local'/'ultralytics'
                config_dir.mkdir(parents=True,exist_ok=True)
                os.environ.setdefault('YOLO_CONFIG_DIR',str(config_dir))
                import cv2
                import numpy as np
                if self.inference_threads is not None:
                    import torch
                    torch.set_num_threads(1)
                    cv2.setNumThreads(1)
                from ultralytics import YOLO
                model=YOLO(str(self.model_path))
                stride=max(int(v) for v in getattr(getattr(model,'model',None),'stride',[32]))
                inference_size=max(stride,(self.imgsz//stride)*stride)
                dummy=np.zeros((inference_size,inference_size,3),dtype=np.uint8)
                options=dict(persist=False,tracker='bytetrack.yaml',classes=list(CLASSES),conf=self.confidence,
                             device=self.device,imgsz=inference_size,iou=.50,max_det=500,verbose=False)
                # The first call creates the Ultralytics predictor and NCNN backend.
                model.track(dummy,**options)
                backend=getattr(getattr(model.predictor,'model',None),'backend',None)
                net=getattr(backend,'net',None)
                if net is not None and self.inference_threads is not None:
                    # NCNN packs weights for the load-time thread count.
                    net.clear()
                    net.opt.num_threads=self.inference_threads
                    net.load_param(str(self.model_path/'model.ncnn.param'))
                    net.load_model(str(self.model_path/'model.ncnn.bin'))
                    model.track(dummy,**options)
                for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                with self.lock:
                    self.model=model
                    self.model_status='ready'
                    self.model_load_ms=round((self.clock()-began)*1000)
            except Exception as exc:
                with self.lock:
                    self.model_status='error'
                    self.model_error=str(exc)
                print(f'YOLO_PRELOAD_ERROR: {exc}',flush=True)
        self.model_thread=threading.Thread(target=load,name='yolo-preload',daemon=True)
        self.model_thread.start()

    def play(self, restart=False):
        with self.lock:
            if self.mode == 'replay' and self.video is None: raise ValueError('Selezionare un video prima di Play')
            if self.mode == 'camera' and not self.camera_enabled: raise ValueError('Telecamera non configurata')
            if self.model_status == 'loading': raise ValueError('YOLO è ancora in preparazione')
            if self.model_status == 'error': raise ValueError(self.model_error or 'Preparazione YOLO non riuscita')
            if self.status in ('loading','running') and not restart: return self.snapshot()
            if restart or self.status != 'paused':
                self.source_generation+=1
                self.reset_stream()
                self.unavailable()
                self.frames.clear()
            self.status,self.error='loading',None
        try:
            self.start()
        except ValueError as exc:
            with self.lock:
                self.status,self.error='error',str(exc)
                self.unavailable()
            raise
        return self.snapshot()

    def pause(self):
        with self.lock:
            if self.mode == 'camera': raise ValueError('Usare Ferma per interrompere la telecamera')
            if self.status not in ('loading','running'): raise ValueError('Il video non è in riproduzione')
            self.status='paused'
            self.unavailable()
            return self.snapshot()

    def stop_playback(self):
        with self.lock:
            if self.mode == 'replay' and self.video is None: raise ValueError('Nessun video selezionato')
            self.source_generation+=1
            self.reset_stream()
            self.unavailable()
            self.frames.clear()
            self.status,self.error='ready',None
            return self.snapshot()

    def restart(self):
        return self.play(restart=True)

    def snapshot(self):
        with self.lock:
            age = None if self.received is None else max(0,round((self.clock()-self.received)*1000))
            return {**self.catalog.snapshot(self.video),'available':self.video is not None if self.mode == 'replay' else self.camera_enabled,
                    'camera_available':self.camera_enabled,'camera_calibrated':self.camera_calibrated,
                    'status':self.status,'error':self.error,'confidence':self.confidence,'max_fps':MAX_FPS,
                    'model_status':self.model_status,'model_error':self.model_error,'model_load_ms':self.model_load_ms,
                    'source':self.video.name if self.mode == 'replay' and self.video else 'CAM0' if self.mode == 'camera' else None,
                    'fresh':self.status == 'running' and age is not None and age < 750,
                    'age_ms':age,'frame':copy.deepcopy(self.current),'zones':self.zones.snapshot(),
                    'metrics':copy.deepcopy(self.events.snapshot('live' if self.mode == 'camera' else 'video')),'mode':self.mode}

    def image(self, serial):
        with self.lock: return self.frames.get(serial)

    def start(self):
        with self.lock:
            if self.thread is not None and self.thread.is_alive(): return
            if self.mode == 'replay' and self.video is None: return
            if self.mode == 'replay' and not self.video.is_file():
                raise ValueError(f'Video assente: {self.video}')
            if self.model_path is None or not (self.model_path.is_file() or (self.model_path.is_dir() and all((self.model_path/f).is_file() for f in ('model.ncnn.param','model.ncnn.bin','metadata.yaml')))):
                raise ValueError(f'Modello locale assente: {self.model_path}')
            self.status = 'loading'
            self.thread = threading.Thread(target=self.run,name='yolo-vision',daemon=True)
            self.thread.start()

    def run(self):
        cap = None
        camera_capture = None
        try:
            # Runtime is offline; preparation/downloads belong to setup only.
            os.environ['YOLO_OFFLINE'] = 'true'
            os.environ['YOLO_AUTOINSTALL'] = 'false'
            config_dir = Path(__file__).resolve().parents[1]/'.local'/'ultralytics'
            config_dir.mkdir(parents=True,exist_ok=True)
            os.environ.setdefault('YOLO_CONFIG_DIR',str(config_dir))
            import cv2
            if self.inference_threads is not None:
                import torch
                torch.set_num_threads(1)
                cv2.setNumThreads(1)
            from ultralytics import YOLO
            with self.lock: model=self.model
            model = model or YOLO(str(self.model_path))
            # Round down to the stride: neither inference side may exceed imgsz.
            stride = max(int(v) for v in getattr(getattr(model,'model',None),'stride',[32]))
            inference_size = max(stride,(self.imgsz//stride)*stride)
            generation,previous_ms=-1,-1
            completed = deque(maxlen=30)
            last_published = None
            threads_configured = self.model is not None
            while not self.stop.is_set():
                with self.lock:
                    playback_status=self.status
                    requested_generation,video,mode=self.source_generation,self.video,self.mode
                if generation != requested_generation:
                    if cap is not None:
                        cap.release()
                        cap=None
                    if camera_capture is not None:
                        camera_capture.close()
                        camera_capture=None
                if playback_status == 'paused':
                    self.stop.wait(.05)
                    continue
                if playback_status not in ('loading','running'):
                    self.stop.wait(.05)
                    continue
                if generation != requested_generation:
                    if mode == 'camera':
                        camera_capture=CameraCapture(clock=self.clock)
                        camera_capture.start()
                        fps=MAX_FPS
                    else:
                        cap=cv2.VideoCapture(str(video))
                        if not cap.isOpened(): raise ValueError('Impossibile aprire il video')
                        fps=cap.get(cv2.CAP_PROP_FPS)
                        if not 0 < fps <= 240: fps=25
                    for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                    generation,index=requested_generation,0
                    camera_sequence=0
                    camera_start=None
                    completed.clear()
                began = self.clock()
                if mode == 'camera':
                    try:
                        camera_sequence,(frame,captured_at)=camera_capture.read_latest(
                            camera_sequence,timeout=8 if camera_sequence == 0 else 2)
                    except (RuntimeError,TimeoutError):
                        with self.lock:
                            if generation != self.source_generation or self.status not in ('loading','running'):
                                continue
                        raise
                    captured_ms=max(previous_ms+1,round(captured_at*1000))
                    previous_ms=captured_ms
                    if camera_start is None: camera_start=captured_at
                    source_ms=round((captured_at-camera_start)*1000)
                else:
                    success,frame = cap.read()
                if mode == 'replay' and not success:
                    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if index == 0 or (total > 0 and index < total): raise ValueError('Video vuoto o frame non decodificabile')
                    with self.lock:
                        if generation != self.source_generation: continue
                        self.status = 'completed'
                        self.unavailable()
                    if not self.loop:
                        if self.catalog.directory is None: break
                        while not self.stop.is_set() and generation == self.source_generation:
                            self.stop.wait(.1)
                        continue
                    cap.release()
                    cap = cv2.VideoCapture(str(video))
                    if not cap.isOpened(): raise ValueError('Impossibile riaprire il video')
                    with self.lock:
                        if generation != self.source_generation: continue
                        self.reset_stream()
                    for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                    index = 0
                    completed.clear()
                    continue
                if mode == 'replay':
                    captured_ms = max(previous_ms+1,round(began*1000))
                    previous_ms = captured_ms
                    source_ms=round(index*1000/fps)
                index += 1
                height,width = frame.shape[:2]
                if max(height,width) > self.frame_size:
                    ratio = self.frame_size/max(height,width)
                    frame = cv2.resize(frame,(max(1,round(width*ratio)),max(1,round(height*ratio))))
                config = self.zones.snapshot()
                if config['revision'] != self.applied_revision:
                    for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                    self.applied_revision = config['revision']
                start = self.clock()
                result = model.track(frame,persist=True,tracker='bytetrack.yaml',classes=list(CLASSES),conf=self.confidence,
                                     device=self.device,imgsz=inference_size,iou=.50,max_det=500,verbose=False)[0]
                if self.inference_threads is not None and not threads_configured:
                    backend = getattr(getattr(model.predictor,'model',None),'backend',None)
                    net = getattr(backend,'net',None)
                    if net is not None:
                        # NCNN packs convolution weights for the load-time thread
                        # count. Reload before changing it; changing opt on a
                        # loaded net produces warnings and slower inference.
                        net.clear()
                        net.opt.num_threads = self.inference_threads
                        net.load_param(str(self.model_path/'model.ncnn.param'))
                        net.load_model(str(self.model_path/'model.ncnn.bin'))
                    threads_configured = True
                inference_ms = round((self.clock()-start)*1000,1)
                height,width = frame.shape[:2]
                detections = []
                boxes = result.boxes
                if boxes is not None:
                    ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None]*len(boxes)
                    for box,confidence,class_id,track_id in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist(),boxes.cls.int().cpu().tolist(),ids):
                        kind,label = CLASSES[class_id]
                        x1,y1,x2,y2 = box
                        zone = classify_position((x1+x2)/2,min(height-1,max(0,y2-1)),width,height,config['config'])
                        detections.append({'id':track_id,'class':kind,'label':label,'confidence':round(confidence,4),
                                           'bbox':[round(v,1) for v in box],'zone':zone if mode == 'replay' or self.camera_calibrated else 'outside'})
                with self.lock:
                    if config['revision'] != self.zones.snapshot()['revision'] or generation != self.source_generation: continue
                    detections=deduplicate_users(detections)
                    self.identities.update(detections,source_ms/1000,width,height)
                for detection in detections:
                    kind,label=detection['class'],detection['label']
                    track_id,confidence=detection['id'],detection['confidence']
                    x1,y1,x2,y2=detection['bbox']
                    color = (80,220,120) if kind == 'pedestrian' else (255,180,70)
                    scale = max(.55,width/1280)
                    thickness = max(2,round(2*scale))
                    text = f'{label} #{track_id or "?"} {confidence:.0%}'
                    (text_width,text_height),baseline = cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,.65*scale,thickness)
                    label_x = max(0,min(int(x1),width-text_width-8))
                    label_y = max(text_height+8,int(y1)-8)
                    cv2.rectangle(frame,(int(x1),int(y1)),(int(x2),int(y2)),color,thickness)
                    cv2.rectangle(frame,(label_x,label_y-text_height-5),(label_x+text_width+6,label_y+baseline),(20,32,36),-1)
                    cv2.putText(frame,text,(label_x+3,label_y),cv2.FONT_HERSHEY_SIMPLEX,.65*scale,color,thickness,cv2.LINE_AA)
                # Limit web preview size; protocol observations always use the source frame.
                if width > 1280: frame = cv2.resize(frame,(1280,round(height*1280/width)))
                ok,jpeg = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
                if not ok: raise ValueError('Codifica preview non riuscita')
                # Space publications too: a fast inference after a slow one must
                # not produce a catch-up burst. Wait outside the snapshot lock.
                interval = 1/min(fps,MAX_FPS)
                if last_published is not None:
                    if self.stop.wait(max(0,last_published+interval-self.clock())): break
                with self.lock:
                    # Drop a result that was inferred against polygons replaced mid-inference.
                    if config['revision'] != self.zones.snapshot()['revision'] or generation != self.source_generation: continue
                    # Pause/stop issued during inference must not publish one
                    # more observation after the user's command.
                    if self.status not in ('loading','running'): continue
                    self.sequence = (self.sequence+1)&0xffffffff
                    calibrated=mode == 'replay' or self.camera_calibrated
                    obs = observation(self.stream,self.sequence,captured_ms,detections,usable=calibrated)
                    obs['age_ms'] = max(0,round(self.clock()*1000)-captured_ms)
                    self.rt.publish(obs)
                    # Analytics owns each pedestrian trajectory. An untracked
                    # vehicle can invalidate RT clear decisions without erasing
                    # already observed pedestrian journeys; unknown IDs are
                    # skipped and expire individually in CrossingEvents.
                    if calibrated: self.events.update(self.stream,source_ms,detections,width,height)
                    self.serial += 1
                    completed.append(self.clock())
                    last_published = completed[-1]
                    fps_actual = round((len(completed)-1)/(completed[-1]-completed[0]),1) if len(completed)>1 and completed[-1]>completed[0] else None
                    self.frames[self.serial] = jpeg.tobytes()
                    while len(self.frames) > 4: self.frames.popitem(last=False)
                    self.current = {'serial':self.serial,'stream':self.stream,'sequence':self.sequence,'video_frame':index,
                                    'video_ms':source_ms,'width':width,'height':height,
                                    'inference_ms':inference_ms,'fps':fps_actual,'inference_size':inference_size,'observation':obs,'detections':detections,'zones_revision':config['revision']}
                    self.received,self.error = captured_ms/1000,None
                    if self.status != 'paused': self.status='running'
                self.stop.wait(max(0,interval-(self.clock()-began)))
        except Exception as exc:
            with self.lock:
                self.status,self.error = 'error',str(exc)
                self.unavailable()
            print(f'VISION_ERROR: {exc}',flush=True)
        finally:
            if cap is not None: cap.release()
            if camera_capture is not None: camera_capture.close()
            with self.lock:
                if self.stop.is_set():
                    self.status = 'stopped'
                    self.unavailable()
