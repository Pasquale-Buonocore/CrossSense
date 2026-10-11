from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from vision.pipeline import VisionService
from vision.sources import VideoCatalog
from vision.zones import ZoneStore
from rt import RTService


class SourceTests(unittest.TestCase):
    def test_catalog_rejects_paths_and_never_autoselects_at_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);videos=root/'videos';videos.mkdir()
            for name in ('one.mp4','two.mp4'): (videos/name).touch()
            (root/'outside.mp4').touch()
            catalog=VideoCatalog(videos,root/'selected.json')
            self.assertEqual(list(catalog.files()),['one.mp4','two.mp4'])
            for name in ('../outside.mp4',str(root/'outside.mp4'),'link.mp4','missing.mp4'):
                with self.assertRaises(ValueError):catalog.select({'video':name})
            catalog.select({'video':'two.mp4'})
            self.assertIsNone(VideoCatalog(videos,root/'selected.json').initial(None))

    def test_symlinks_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); videos=root/'videos'; videos.mkdir(); (root/'outside.mp4').touch()
            try: (videos/'link.mp4').symlink_to(root/'outside.mp4')
            except OSError as exc:
                if getattr(exc,'winerror',None)==1314: self.skipTest('Windows: privilegio symlink non disponibile')
                raise
            self.assertEqual(VideoCatalog(videos).files(),{})

    def test_switch_discards_in_flight_result_and_resets_tracker(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);videos=root/'videos';videos.mkdir()
            for name in ('one.mp4','two.mp4'): (videos/name).touch()
            (root/'model.pt').touch()
            sent=[]
            class RecordingRT(RTService):
                def publish(self,frame):sent.append(frame);super().publish(frame)
            vision=VisionService(RecordingRT(),ZoneStore(root/'zones.json'),model=root/'model.pt',video_dir=videos)
            self.assertIsNone(vision.video);self.assertEqual(vision.status,'idle')
            vision.select_video({'video':'one.mp4'})
            self.assertEqual(vision.status,'ready');self.assertIsNone(vision.thread)
            vision.thread=SimpleNamespace(is_alive=lambda:True)
            vision.status='loading'
            old_stream=vision.stream;calls=[];resets=[];opened=[]
            class Capture:
                def __init__(self,path):opened.append(Path(path).name)
                def isOpened(self):return True
                def get(self,key):return 240
                def read(self):return True,SimpleNamespace(shape=(240,320,3))
                def release(self):pass
            def track(frame,**kwargs):
                calls.append(1)
                if len(calls)==1:
                    vision.select_video({'video':'two.mp4'})
                    vision.play()
                else:vision.stop.set()
                return [SimpleNamespace(boxes=None)]
            model=SimpleNamespace(track=track,predictor=SimpleNamespace(trackers=[SimpleNamespace(reset=lambda:resets.append(1))]))
            cv=SimpleNamespace(VideoCapture=Capture,CAP_PROP_FPS=1,CAP_PROP_FRAME_COUNT=2,
                imencode=lambda *a:(True,SimpleNamespace(tobytes=lambda:b'new-video-jpeg')),IMWRITE_JPEG_QUALITY=1)
            with patch.dict('sys.modules',{'cv2':cv,'ultralytics':SimpleNamespace(YOLO=lambda _:model)}):vision.run()
            acquired=[f for f in sent if f['time_ms'] is not None]
            self.assertEqual(len(acquired),1)
            self.assertNotEqual(acquired[0]['stream'],old_stream)
            self.assertEqual(opened,['one.mp4','two.mp4']);self.assertEqual(len(resets),2)
            self.assertFalse(sent[0]['valid']);self.assertIsNone(sent[0]['time_ms'])
            self.assertEqual(vision.serial,1)
