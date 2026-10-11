from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from test_trial_api import TrialAPITests
from vision.zones import ZoneStore
from vision.pipeline import VisionService


class VisionAPITests(TrialAPITests):
    def setUp(self):
        super().setUp()
        self.server.vision=VisionService(self.server.rt,ZoneStore(Path(self.folder.name)/'zones.json'))
    def test_video_selection_is_limited_to_catalog_and_invalidates_observations(self):
        from unittest.mock import patch
        root=Path(self.folder.name);videos=root/'videos';videos.mkdir();(videos/'one.mp4').touch();(videos/'two.mp4').touch()
        vision=VisionService(self.server.rt,ZoneStore(root/'zones.json'),video_dir=videos,selection_file=root/'selected.json')
        self.server.vision=vision
        old=vision.stream
        self.assertEqual(len(self.call('/api/vision')[1]['videos']),2)
        self.assertEqual(self.call('/api/vision/source',{'video':'../elsewhere.mp4'})[0],400)
        code,data=self.call('/api/vision/source',{'video':'two.mp4'})
        self.assertEqual(code,200);self.assertEqual(data['selected_video'],'two.mp4')
        self.assertEqual(data['status'],'ready');self.assertIsNone(vision.thread)
        self.assertNotEqual(vision.stream,old);self.assertFalse(self.server.rt.latest[0]['valid'])
        with patch.object(vision,'start') as start:
            code,data=self.call('/api/vision/play',{})
        self.assertEqual(code,200);self.assertEqual(data['status'],'loading');start.assert_called_once()
        self.assertEqual(self.call('/api/vision/pause',{})[1]['status'],'paused')
        self.assertEqual(self.call('/api/vision/stop',{})[1]['status'],'ready')
    def test_editor_save_conflict_and_source_ownership(self):
        code,data=self.call('/api/vision/zones');self.assertEqual(code,200)
        self.assertEqual(self.call('/api/vision/zones',data)[0],200)
        self.assertEqual(self.call('/api/vision/zones',data)[0],409)
        self.assertEqual(self.call('/api/vision/zones',{'config':{}})[0],400)
        self.server.vision.video=Path('synthetic.mp4')
        self.assertEqual(self.call('/api/config')[1]['default_mode'],'replay')
        self.assertEqual(self.call('/api/observations',{})[0],409)
        self.assertEqual(self.call('/api/trial',{})[0],409)
    def test_camera_switch_is_manual_and_uses_own_zones(self):
        root=Path(self.folder.name)
        vision=VisionService(self.server.rt,ZoneStore(root/'replay-zones.json'),
                             camera_zones=ZoneStore(root/'camera-zones.json'),camera_enabled=True)
        self.server.vision=vision
        old_stream=vision.stream
        code,data=self.call('/api/vision/mode',{'mode':'camera'})
        self.assertEqual(code,200)
        self.assertEqual(data['mode'],'camera')
        self.assertEqual(data['status'],'ready')
        self.assertIsNone(vision.thread)
        self.assertFalse(data['camera_calibrated'])
        self.assertNotEqual(vision.stream,old_stream)
        self.assertFalse(self.server.rt.latest[0]['valid'])
        zones=data['zones']
        self.assertEqual(self.call('/api/vision/zones',zones)[0],200)
        self.assertTrue(self.call('/api/vision')[1]['camera_calibrated'])
        self.assertTrue((root/'camera-zones.json').is_file())
        self.assertFalse((root/'replay-zones.json').exists())
        self.assertEqual(self.call('/api/vision/source',{'video':'x'})[0],400)
        self.assertEqual(self.call('/api/vision/mode',{'mode':'replay'})[1]['mode'],'replay')
        self.assertEqual(self.call('/api/vision')[1]['zones']['revision'],0)
    def test_snapshot_and_exact_frame_endpoint(self):
        self.assertFalse(self.call('/api/vision')[1]['fresh'])
        from urllib.request import urlopen
        self.server.vision.frames[42]=b'jpeg'
        with urlopen(self.url+'/api/vision/frame.jpg?serial=42',timeout=2) as response:
            self.assertEqual(response.headers['Content-Type'],'image/jpeg');self.assertEqual(response.read(),b'jpeg')
        self.assertEqual(self.call('/api/vision/frame.jpg?serial=41')[0],404)
        with urlopen(self.url+'/api/vision/reference.jpg',timeout=2) as response:
            self.assertGreater(len(response.read()),1000)
