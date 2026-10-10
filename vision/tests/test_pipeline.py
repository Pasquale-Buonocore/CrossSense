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
                self.assertLessEqual(max(frame.shape[:2]),360)
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
            vision=VisionService(RecordingRT(),ZoneStore(path/'zones.json'),path/'video.mp4',path/'model.pt')
            with patch.dict(sys.modules,{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):vision.run()
            self.assertEqual(len(calls),3);self.assertTrue(all(c['persist'] and c['tracker']=='bytetrack.yaml' for c in calls))
            self.assertTrue(all(c['imgsz']==352 for c in calls))
            self.assertEqual(len(sent),4);self.assertTrue(all(f['valid'] for f in sent[:3]))
            self.assertTrue(all(f['tracks'][0][2]=='crossing' for f in sent[:3]))
            self.assertEqual(vision.snapshot()['status'],'completed');self.assertFalse(vision.snapshot()['fresh'])
            self.assertFalse(sent[-1]['valid']);self.assertIsNone(sent[-1]['time_ms'])
            self.assertEqual(vision.image(3),b'jpeg')


if __name__=='__main__':unittest.main()
