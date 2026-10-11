import threading
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vision.camera import CameraCapture


class CameraBufferTests(unittest.TestCase):
    def test_gstreamer_five_hz_does_not_drop_jittered_samples_twice(self):
        times=iter((1.0,1.01,1.199,1.398,1.597))
        capture=CameraCapture(clock=lambda:next(times))
        class VideoCapture:
            def __init__(self,pipeline,backend):
                self.pipeline=pipeline
                self.reads=0
                self.released=False
            def isOpened(self):return True
            def read(self):
                self.reads+=1
                if self.reads==5:capture.stop_event.set()
                return True,SimpleNamespace(shape=(480,640,3),number=self.reads)
            def release(self):self.released=True
        opened=[]
        def video_capture(pipeline,backend):
            opened.append(VideoCapture(pipeline,backend))
            return opened[-1]
        cv=SimpleNamespace(CAP_GSTREAMER=42,VideoCapture=video_capture)
        with patch.dict(sys.modules,{'cv2':cv}):capture._capture_gstreamer()
        self.assertIn('videorate drop-only=true',opened[0].pipeline)
        self.assertIn('appsink max-buffers=1 drop=true',opened[0].pipeline)
        self.assertEqual(capture.sequence,4)
        self.assertEqual(capture.latest[0].number,5)
        self.assertEqual(capture.latest[1],1.597)
        self.assertTrue(opened[0].released)

    def test_latest_frame_replaces_older_frame_and_stop_wakes_waiter(self):
        capture=CameraCapture()
        with capture.condition:
            capture.sequence=1
            capture.latest=('old',1.0)
            capture.sequence=2
            capture.latest=('new',1.2)
            capture.condition.notify_all()
        self.assertEqual(capture.read_latest(0),(2,('new',1.2)))
        result=[]
        waiter=threading.Thread(target=lambda: result.append(self._read_after_stop(capture)))
        waiter.start()
        capture.close()
        waiter.join(timeout=1)
        self.assertEqual(result,['Telecamera fermata'])

    @staticmethod
    def _read_after_stop(capture):
        try:
            capture.read_latest(2)
        except RuntimeError as exc:
            return str(exc)
        return 'nessun errore'


if __name__ == '__main__':
    unittest.main()
