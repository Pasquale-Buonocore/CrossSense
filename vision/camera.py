"""libcamera capture for the CSI camera; only the newest 5 Hz frame is kept."""

import selectors
import threading
import time


class CameraCapture:
    def __init__(self, index=0, width=640, height=480, fps=5, clock=time.monotonic):
        self.index, self.width, self.height = index, width, height
        self.interval, self.clock = 1 / fps, clock
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.thread = None
        self.latest = None
        self.sequence = 0
        self.error = None

    def start(self):
        self.thread = threading.Thread(target=self._capture, name='csi-camera', daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)

    def read_latest(self, after, timeout=1):
        deadline = self.clock() + timeout
        with self.condition:
            while self.sequence <= after and self.error is None and not self.stop_event.is_set():
                remaining = deadline - self.clock()
                if remaining <= 0:
                    raise TimeoutError('Nessun frame dalla telecamera entro 1 s')
                self.condition.wait(remaining)
            if self.error is not None:
                raise RuntimeError(f'Telecamera: {self.error}')
            if self.sequence <= after:
                raise RuntimeError('Telecamera fermata')
            return self.sequence, self.latest

    def _capture(self):
        camera = None
        started = False
        try:
            try:
                import libcamera
                import libcamera.utils
            except ImportError:
                self._capture_gstreamer()
                return
            import cv2
            import numpy as np

            manager = libcamera.CameraManager.singleton()
            if len(manager.cameras) <= self.index:
                raise RuntimeError('Nessuna camera CSI disponibile in App Lab')
            camera = manager.cameras[self.index]
            camera.acquire()
            config = camera.generate_configuration([libcamera.StreamRole.Viewfinder])
            stream_config = config.at(0)
            stream_config.size = libcamera.Size(self.width, self.height)
            config.validate()
            camera.configure(config)
            stream = stream_config.stream
            width, height = stream_config.size.width, stream_config.size.height
            stride = stream_config.stride
            pixel_format = str(stream_config.pixel_format)
            allocator = libcamera.FrameBufferAllocator(camera)
            if allocator.allocate(stream) < 2:
                raise RuntimeError('Buffer libcamera insufficienti')
            requests = []
            for buffer in allocator.buffers(stream):
                request = camera.create_request()
                request.add_buffer(stream, buffer)
                requests.append(request)
            camera.start()
            started = True
            for request in requests:
                camera.queue_request(request)
            selector = selectors.DefaultSelector()
            selector.register(manager.event_fd, selectors.EVENT_READ)
            next_copy = 0
            try:
                while not self.stop_event.is_set():
                    if not selector.select(.2):
                        continue
                    for request in manager.get_ready_requests():
                        if request.status != libcamera.Request.Status.Complete:
                            continue
                        captured = self.clock()
                        if captured >= next_copy:
                            buffer = request.buffers[stream]
                            with libcamera.utils.MappedFrameBuffer(buffer) as mapped:
                                raw = np.frombuffer(mapped.planes[0], dtype=np.uint8)
                                channels = 4 if '8888' in pixel_format else 3
                                if channels not in (3, 4) or stride < width * channels or raw.size < stride * height:
                                    raise RuntimeError(f'Formato camera non supportato: {pixel_format}, stride {stride}')
                                pixels = raw[:stride * height].reshape(height, stride)[:, :width * channels].reshape(height, width, channels)
                                if pixel_format == 'ABGR8888':
                                    frame = cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)
                                elif pixel_format in ('ARGB8888', 'XRGB8888'):
                                    frame = cv2.cvtColor(pixels, cv2.COLOR_BGRA2BGR)
                                elif pixel_format == 'XBGR8888':
                                    frame = cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)
                                elif pixel_format == 'BGR888':
                                    frame = pixels.copy()
                                elif pixel_format == 'RGB888':
                                    frame = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
                                else:
                                    raise RuntimeError(f'Formato camera non supportato: {pixel_format}')
                            with self.condition:
                                self.sequence += 1
                                self.latest = (frame, captured)
                                self.condition.notify_all()
                            next_copy = captured + self.interval
                        request.reuse()
                        camera.queue_request(request)
            finally:
                selector.close()
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.condition.notify_all()
        finally:
            if camera is not None:
                if started:
                    camera.stop()
                camera.release()

    def _capture_gstreamer(self):
        """Use App Lab's libcamerasrc when Python libcamera bindings are absent."""
        import cv2
        pipeline = (
            'libcamerasrc ! '
            f'video/x-raw,width={self.width},height={self.height} ! '
            'videorate drop-only=true ! video/x-raw,framerate=5/1 ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink max-buffers=1 drop=true sync=false'
        )
        capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not capture.isOpened():
            raise RuntimeError('CAM0 non accessibile tramite libcamerasrc di GStreamer')
        try:
            next_copy=0
            while not self.stop_event.is_set():
                ok,frame=capture.read()
                if not ok or frame is None or len(frame.shape) < 2:
                    raise RuntimeError('Acquisizione CAM0 interrotta')
                captured=self.clock()
                if captured < next_copy:
                    continue
                with self.condition:
                    self.sequence+=1
                    self.latest=(frame,captured)
                    self.condition.notify_all()
                # videorate already caps this path at 5 Hz. Allow normal
                # scheduling jitter instead of dropping every other sample.
                next_copy=captured+self.interval*.8
        finally:
            capture.release()
