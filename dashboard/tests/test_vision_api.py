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
    def test_editor_save_conflict_and_source_ownership(self):
        code,data=self.call('/api/vision/zones');self.assertEqual(code,200)
        self.assertEqual(self.call('/api/vision/zones',data)[0],200)
        self.assertEqual(self.call('/api/vision/zones',data)[0],409)
        self.assertEqual(self.call('/api/vision/zones',{'config':{}})[0],400)
        self.server.vision.video=Path('synthetic.mp4')
        self.assertEqual(self.call('/api/config')[1]['default_mode'],'hardware')
        self.assertEqual(self.call('/api/observations',{})[0],409)
        self.assertEqual(self.call('/api/trial',{})[0],409)
    def test_snapshot_and_exact_frame_endpoint(self):
        self.assertFalse(self.call('/api/vision')[1]['fresh'])
        from urllib.request import urlopen
        self.server.vision.frames[42]=b'jpeg'
        with urlopen(self.url+'/api/vision/frame.jpg?serial=42',timeout=2) as response:
            self.assertEqual(response.headers['Content-Type'],'image/jpeg');self.assertEqual(response.read(),b'jpeg')
        self.assertEqual(self.call('/api/vision/frame.jpg?serial=41')[0],404)
        with urlopen(self.url+'/api/vision/reference.jpg',timeout=2) as response:
            self.assertGreater(len(response.read()),1000)
