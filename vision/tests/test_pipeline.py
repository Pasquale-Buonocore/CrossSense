import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'dashboard'))
from rt import RTService, validate_frame, encode
from vision.pipeline import VisionService, observation
from vision.zones import ZoneStore, RevisionConflict, classify_position, default_config, validate_config


def detection(i=1, kind='pedestrian', zone='crossing'):
    return dict(id=i, **{'class':kind},label='PEDONE',confidence=.9,bbox=[0,0,10,10],zone=zone)


class ObservationTests(unittest.TestCase):
    def test_vehicle_transit_is_not_pedestrian_occupancy(self):
        f=observation(1,1,100,[detection(1,'vehicle','crossing')])
        validate_frame(f)
        self.assertEqual(f['crossing'],'clear')

    def test_camera_frame_reaches_shared_pipeline_only_after_own_roi_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'model.pt').touch()
            sent=[]
            rt=SimpleNamespace(publish=lambda frame:sent.append(copy.deepcopy(frame)))
            zones=ZoneStore(root/'replay.json')
            camera_zones=ZoneStore(root/'camera.json')
            vision=VisionService(rt,zones,model=root/'model.pt',camera_zones=camera_zones,camera_enabled=True)
            vision.select_mode({'mode':'camera'})
            sent.clear()
            class Capture:
                def __init__(self,**kwargs):pass
                def start(self):pass
                def read_latest(self,after,timeout=1):
                    self_test.assertEqual(timeout,8)
                    return 1,(SimpleNamespace(shape=(240,320,3)),vision.clock())
                def close(self):pass
            model=SimpleNamespace(track=lambda frame,**kwargs:[SimpleNamespace(boxes=None)],
                                  predictor=SimpleNamespace(trackers=[]))
            vision.model=model
            def encode(*args):
                vision.stop.set()
                return True,SimpleNamespace(tobytes=lambda:b'jpeg')
            cv=SimpleNamespace(imencode=encode,IMWRITE_JPEG_QUALITY=1)
            self_test=self
            vision.status='loading'
            with patch('vision.pipeline.CameraCapture',Capture),patch.dict(sys.modules,{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):
                vision.run()
            self.assertFalse(sent[0]['valid'])
            self.assertEqual(vision.image(1),b'jpeg')
            self.assertEqual(vision.snapshot()['metrics']['time_basis'],'live')
            vision.stop.clear()
            vision.configure(vision.zones.snapshot())
            self.assertTrue((root/'camera.json').is_file())
            sent.clear()
            vision.status='loading'
            with patch('vision.pipeline.CameraCapture',Capture),patch.dict(sys.modules,{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):
                vision.run()
            self.assertTrue(sent[0]['valid'])
            self.assertIsNotNone(sent[0]['time_ms'])

    def test_full_protocol_and_no_pixel_coordinates(self):
        f=observation(123,7,100,[detection(),detection(2,'vehicle','approach')])
        validate_frame(f)
        self.assertTrue(f['valid']);self.assertEqual(f['crossing'],'occupied');self.assertEqual(f['approach'],'present')
        self.assertEqual(f['tracks'][0],[1,'pedestrian','crossing',None,None])
        self.assertLessEqual(len(encode(f)),900)

    def test_overflow_untracked_and_missing_image(self):
        for detections in ([detection(i) for i in range(1,10)],[detection(None)],[detection(),detection()]):
            f=observation(1,1,100,detections)
            validate_frame(f);self.assertFalse(f['valid']);self.assertEqual(f['crossing'],'occupied');self.assertNotEqual(f['approach'],'clear')
        validate_frame(observation(1,1,None,[],False))
        self.assertEqual(observation(1,1,100,[])['crossing'],'clear')


class ZoneTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'zones.json';self.store=ZoneStore(self.path)
    def tearDown(self):self.folder.cleanup()
    def test_gaetano_scaling_persistence_and_conflict(self):
        config=default_config()
        self.assertEqual(classify_position(1000,1300,2528,1696,config),'crossing')
        self.assertEqual(classify_position(500,650,1264,848,config),'crossing')
        first=self.store.snapshot();saved=self.store.update(first)
        self.assertEqual(ZoneStore(self.path).snapshot(),saved)
        with self.assertRaises(RevisionConflict):self.store.update(first)
    def test_geometry_errors_are_rejected_atomically(self):
        for points in ([[0,0],[1,1]],[[0,0],[1,1],[0,1],[1,0]],[[0,0],[1,0],[0,0]],[[0,0],[float('nan'),0],[0,1]],[[0,0],[2,0],[0,1]]):
            data=self.store.snapshot();data['config']['zones']['crossing']=points
            with self.assertRaises(ValueError):self.store.update(data)
            self.assertEqual(self.store.snapshot()['revision'],0);self.assertFalse(self.path.exists())
    def test_edit_invalidates_and_changes_stream(self):
        rt=RTService();vision=VisionService(rt,self.store)
        old=vision.stream;vision.configure(self.store.snapshot())
        self.assertNotEqual(vision.stream,old);self.assertFalse(rt.latest[0]['valid']);self.assertIsNone(rt.latest[0]['time_ms'])
        self.assertEqual(rt.latest[0]['stream'],vision.stream)


class Tensor:
    def __init__(self,values):self.values=values
    def int(self):return self
    def cpu(self):return self
    def tolist(self):return self.values


class VideoTests(unittest.TestCase):
    def test_five_fps_limit_with_jitter_preserves_all_frames_and_source_time(self):
        for source_fps in (2, 30):
            with self.subTest(source_fps=source_fps), tempfile.TemporaryDirectory() as folder:
                path=Path(folder)
                now=[10.0];published=[];snapshots=[];durations=iter((.17,.32,.04,.15))
                class Stop:
                    def is_set(self):return False
                    def wait(self,delay):now[0]+=delay;return False
                class Capture:
                    def __init__(self):self.index=0
                    def isOpened(self):return True
                    def get(self,key):return source_fps if key==1 else 4
                    def read(self):
                        self.index+=1
                        return (True,SimpleNamespace(shape=(240,320,3))) if self.index<=4 else (False,None)
                    def release(self):pass
                def track(frame,**kwargs):
                    now[0]+=next(durations)
                    return [SimpleNamespace(boxes=None)]
                def publish(frame):
                    if frame['time_ms'] is not None:published.append((now[0],frame))
                model=SimpleNamespace(track=track,predictor=SimpleNamespace(trackers=[]))
                vision=VisionService(SimpleNamespace(publish=publish),ZoneStore(path/'zones.json'),
                                     video=path/'video.mp4',clock=lambda:now[0])
                vision.model=model;vision.status='loading';vision.stop=Stop()
                def encode(*args):
                    if vision.current:snapshots.append(vision.snapshot())
                    return True,SimpleNamespace(tobytes=lambda:b'jpeg')
                cv=SimpleNamespace(VideoCapture=lambda _:Capture(),CAP_PROP_FPS=1,CAP_PROP_FRAME_COUNT=2,
                                   imencode=encode,IMWRITE_JPEG_QUALITY=1)
                with patch.dict(sys.modules,{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):
                    vision.run()
                self.assertEqual(len(published),4)
                for (before,_),(after,frame) in zip(published,published[1:]):
                    self.assertGreaterEqual(after-before+1e-9,1/min(source_fps,5))
                    self.assertEqual(frame['age_ms'],round(after*1000)-frame['time_ms'])
                for snapshot in snapshots:
                    frame=snapshot['frame']
                    self.assertEqual(frame['video_ms'],round((frame['video_frame']-1)*1000/source_fps))
                    if frame['fps'] is not None:self.assertLessEqual(frame['fps'],min(source_fps,5))
                self.assertEqual(vision.status,'completed')

    def test_model_is_preloaded_and_warmed_without_starting_a_video(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);model_path=path/'model.pt';model_path.touch()
            resets=[];calls=[]
            predictor=SimpleNamespace(trackers=[SimpleNamespace(reset=lambda:resets.append(1))],model=SimpleNamespace(backend=None))
            model=SimpleNamespace(model=SimpleNamespace(stride=[32]),predictor=predictor,
                                  track=lambda frame,**kwargs:calls.append((frame,kwargs)) or [SimpleNamespace(boxes=None)])
            cv=SimpleNamespace(setNumThreads=lambda value:None)
            np=SimpleNamespace(uint8='uint8',zeros=lambda shape,dtype:SimpleNamespace(shape=shape,dtype=dtype))
            torch=SimpleNamespace(set_num_threads=lambda value:None)
            vision=VisionService(RTService(),ZoneStore(path/'zones.json'),model=model_path,imgsz=320,inference_threads=2)
            with patch.dict(sys.modules,{'cv2':cv,'numpy':np,'torch':torch,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):
                vision.preload();vision.model_thread.join(timeout=2)
            snapshot=vision.snapshot()
            self.assertEqual(snapshot['model_status'],'ready');self.assertIsNone(vision.video)
            self.assertEqual(snapshot['status'],'idle');self.assertEqual(len(calls),1);self.assertEqual(len(resets),1)

    def test_every_frame_processed_eof_invalidates_preview_and_bridge(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'video.mp4').touch();(path/'model.pt').touch()
            sent=[]
            class RecordingRT(RTService):
                def publish(self,f):sent.append(copy.deepcopy(f));super().publish(f)
            frames=[SimpleNamespace(shape=(1696,2528,3)) for _ in range(3)]
            class Capture:
                def __init__(self):self.index=0
                def isOpened(self):return True
                def get(self,key):return 240 if key==1 else 3
                def read(self):
                    if self.index==3:return False,None
                    f=frames[self.index];self.index+=1;return True,f
                def release(self):pass
            calls=[]
            def track(frame,**kwargs):
                self.assertEqual(frame.shape[:2],(322,480))
                calls.append(kwargs)
                height,width=frame.shape[:2]
                boxes=SimpleNamespace(id=Tensor([1]),xyxy=Tensor([[.36*width,.65*height,.44*width,.767*height+1]]),conf=Tensor([.912]),cls=Tensor([0]))
                return [SimpleNamespace(boxes=boxes)]
            model=SimpleNamespace(track=track,predictor=SimpleNamespace(trackers=[]))
            cv=SimpleNamespace(VideoCapture=lambda _:Capture(),CAP_PROP_FPS=1,CAP_PROP_FRAME_COUNT=2,
                rectangle=lambda *a:None,putText=lambda *a:None,FONT_HERSHEY_SIMPLEX=1,LINE_AA=1,
                getTextSize=lambda *a:((100,20),5),
                resize=lambda f,size:SimpleNamespace(shape=(size[1],size[0],3)),imencode=lambda *a:(True,SimpleNamespace(tobytes=lambda:b'jpeg')),
                IMWRITE_JPEG_QUALITY=1)
            vision=VisionService(RecordingRT(),ZoneStore(path/'zones.json'),path/'video.mp4',path/'model.pt',frame_size=480,imgsz=320)
            vision.status='loading'
            with patch.dict(sys.modules,{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):vision.run()
            self.assertEqual(len(calls),3);self.assertTrue(all(c['persist'] and c['tracker']=='bytetrack.yaml' for c in calls))
            self.assertTrue(all(c['imgsz']==320 for c in calls))
            self.assertEqual(len(sent),4);self.assertTrue(all(f['valid'] for f in sent[:3]))
            self.assertTrue(all(f['tracks'][0][2]=='crossing' for f in sent[:3]))
            self.assertEqual(vision.snapshot()['status'],'completed');self.assertFalse(vision.snapshot()['fresh'])
            self.assertFalse(sent[-1]['valid']);self.assertIsNone(sent[-1]['time_ms'])
            self.assertEqual(vision.image(3),b'jpeg')


if __name__=='__main__':unittest.main()
