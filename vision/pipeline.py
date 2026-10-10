"""Read every MP4 frame, track with YOLO/ByteTrack, publish an atomic snapshot."""
import copy
from collections import OrderedDict
from pathlib import Path
import secrets
import threading
import time
from .zones import classify_position

CLASSES = {0:('pedestrian','PEDONE'),1:('bicycle','BICICLETTA'),2:('vehicle','AUTO'),3:('vehicle','MOTO'),5:('vehicle','AUTOBUS'),7:('vehicle','CAMION')}


def observation(stream, sequence, captured_ms, detections, usable=True):
    crossing = any(d['zone'] == 'crossing' for d in detections)
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
    def __init__(self, rt, zones, video=None, model=None, device='cpu', confidence=.30, imgsz=640, loop=False, clock=time.monotonic):
        self.rt,self.zones,self.clock = rt,zones,clock
        self.video,self.model_path = Path(video) if video else None,Path(model) if model else None
        self.device,self.confidence,self.imgsz,self.loop = device,confidence,imgsz,loop
        self.lock,self.stop = threading.RLock(),threading.Event()
        self.stream,self.sequence = secrets.randbits(32),0
        self.status,self.error = 'idle',None
        self.current,self.received,self.frames = None,None,OrderedDict()
        self.serial,self.thread = 0,None
        self.applied_revision = zones.snapshot()['revision']

    def reset_stream(self):
        old = self.stream
        while self.stream == old: self.stream = secrets.randbits(32)
        self.sequence = 0

    def unavailable(self):
        self.sequence = (self.sequence+1)&0xffffffff
        self.rt.publish(observation(self.stream,self.sequence,None,[],False))
        self.current,self.received = None,None

    def configure(self, data):
        with self.lock:
            result = self.zones.update(data)
            self.reset_stream()
            self.unavailable()
            return result

    def snapshot(self):
        with self.lock:
            age = None if self.received is None else max(0,round((self.clock()-self.received)*1000))
            return {'available':self.video is not None,'status':self.status,'error':self.error,
                    'source':self.video.name if self.video else None,'fresh':self.status == 'running' and age is not None and age < 750,
                    'age_ms':age,'frame':copy.deepcopy(self.current),'zones':self.zones.snapshot()}

    def image(self, serial):
        with self.lock: return self.frames.get(serial)

    def start(self):
        if self.video is None: return
        if not self.video.is_file(): raise ValueError(f'Video assente: {self.video}')
        if self.model_path is None or not self.model_path.is_file(): raise ValueError(f'Modello locale assente: {self.model_path}')
        self.status = 'loading'
        self.thread = threading.Thread(target=self.run,name='yolo-video',daemon=True)
        self.thread.start()

    def run(self):
        cap = None
        try:
            import cv2
            from ultralytics import YOLO
            model = YOLO(str(self.model_path))
            cap = cv2.VideoCapture(str(self.video))
            if not cap.isOpened(): raise ValueError('Impossibile aprire il video')
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not 0 < fps <= 240: fps = 25
            index,previous_ms = 0,-1
            while not self.stop.is_set():
                began = self.clock()
                success,frame = cap.read()
                if not success:
                    total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if index == 0 or (total > 0 and index < total): raise ValueError('Video vuoto o frame non decodificabile')
                    with self.lock:
                        self.status = 'completed'
                        self.unavailable()
                    if not self.loop: break
                    cap.release()
                    cap = cv2.VideoCapture(str(self.video))
                    if not cap.isOpened(): raise ValueError('Impossibile riaprire il video')
                    with self.lock: self.reset_stream()
                    for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                    index = 0
                    continue
                captured_ms = max(previous_ms+1,round(began*1000))
                previous_ms = captured_ms
                index += 1
                config = self.zones.snapshot()
                if config['revision'] != self.applied_revision:
                    for tracker in getattr(model.predictor,'trackers',[]): tracker.reset()
                    self.applied_revision = config['revision']
                start = self.clock()
                result = model.track(frame,persist=True,tracker='bytetrack.yaml',classes=list(CLASSES),conf=self.confidence,
                                     device=self.device,imgsz=self.imgsz,iou=.50,max_det=500,verbose=False)[0]
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
                                           'bbox':[round(v,1) for v in box],'zone':zone})
                        color = (80,220,120) if kind == 'pedestrian' else (255,180,70)
                        scale = max(1,width/1280)
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
                with self.lock:
                    # Drop a result that was inferred against polygons replaced mid-inference.
                    if config['revision'] != self.zones.snapshot()['revision']: continue
                    self.sequence = (self.sequence+1)&0xffffffff
                    obs = observation(self.stream,self.sequence,captured_ms,detections)
                    obs['age_ms'] = max(0,round(self.clock()*1000)-captured_ms)
                    self.rt.publish(obs)
                    self.serial += 1
                    self.frames[self.serial] = jpeg.tobytes()
                    while len(self.frames) > 4: self.frames.popitem(last=False)
                    self.current = {'serial':self.serial,'stream':self.stream,'sequence':self.sequence,'video_frame':index,
                                    'video_ms':round((index-1)*1000/fps),'width':width,'height':height,
                                    'inference_ms':inference_ms,'observation':obs,'detections':detections,'zones_revision':config['revision']}
                    self.received,self.status,self.error = began,'running',None
                self.stop.wait(max(0,1/fps-(self.clock()-began)))
        except Exception as exc:
            with self.lock:
                self.status,self.error = 'error',str(exc)
                self.unavailable()
            print(f'VISION_ERROR: {exc}',flush=True)
        finally:
            if cap is not None: cap.release()
            with self.lock:
                if self.stop.is_set():
                    self.status = 'stopped'
                    self.unavailable()
