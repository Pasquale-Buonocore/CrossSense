"""Host check: real YOLO video -> RTService -> actual STM32 sketch (Bridge stub)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'dashboard'))
from rt import RTService, validate_frame
from vision.pipeline import VisionService
from vision.zones import ZoneStore


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',type=Path,required=True)
    parser.add_argument('--model',type=Path,default=root/'models'/'yolo26n.pt')
    parser.add_argument('--arduino-json',type=Path,required=True,help='Directory containing ArduinoJson.h 7.4.3')
    parser.add_argument('--timeout',type=float,default=60)
    parser.add_argument('--confidence',type=float,default=.30)
    args=parser.parse_args()
    if not 0 < args.timeout <= 60:parser.error('Timeout tra 0 e 60 secondi')
    if not 0 < args.confidence <= 1:parser.error('Confidenza tra 0 e 1')
    with tempfile.TemporaryDirectory() as folder:
        directory=Path(folder);runner=directory/'native_bridge'
        subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-pedantic','-DCROSSSENSE_STANDARD_CYCLE=1',
                        '-I',str(args.arduino_json.resolve()),'-I',str(root/'firmware'/'tests'/'stubs'),
                        str(root/'firmware'/'tests'/'native_bridge.cpp'),'-o',str(runner)],check=True)
        process=subprocess.Popen([str(runner)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        began=time.monotonic();samples=[];samples_lock=threading.Lock()
        def call(method,payload):
            assert method=='crosssense_update'
            frame=validate_frame(json.loads(payload))
            process.stdin.write(f'{int((time.monotonic()-began)*1000)} {payload}\n');process.stdin.flush()
            response=process.stdout.readline().strip()
            if not response:raise RuntimeError('Native STM32 runner terminated')
            with samples_lock:samples.append((frame,json.loads(response)))
            return response
        rt=RTService(call)
        vision=VisionService(rt,ZoneStore(directory/'zones.json'),args.video,args.model,confidence=args.confidence)
        changed=False;initial_stream=vision.stream
        rt.start()
        try:
            vision.start()
            deadline=time.monotonic()+args.timeout
            while vision.thread.is_alive() and time.monotonic()<deadline:
                snapshot=vision.snapshot()
                if snapshot['frame'] and snapshot['frame']['video_frame']>=3 and not changed:
                    vision.configure(vision.zones.snapshot());changed=True
                vision.stop.wait(.05)
            if vision.thread.is_alive():raise RuntimeError('YOLO did not complete within timeout')
            if vision.status!='completed':raise RuntimeError(f'Vision failed: {vision.error}')
            time.sleep(.3)  # Let RT deliver the final unavailable snapshot.
            with samples_lock:received=list(samples)
            observations=[(f,s) for f,s in received if f['time_ms'] is not None]
            assert observations,'No video observations delivered'
            assert any(s['ok'] for f,s in observations),'No video observations accepted'
            assert all(s['ok'] or (s['error']=='STALE_FRAME' and f['valid'] and f['age_ms']>=750) for f,s in observations),[(f['frame'],s['error'],f['age_ms']) for f,s in observations if not s['ok']]
            assert changed and vision.stream!=initial_stream,'ROI change did not restart stream'
            assert len({f['stream'] for f,s in observations})>=2,'STM32 did not receive the new ROI stream'
            assert received[-1][0]['time_ms'] is None and not received[-1][0]['valid'],'EOF did not invalidate observations'
            assert all(not (s['vehicle_light']=='GREEN' and s['pedestrian_light']=='GREEN') for f,s in received)
            print(json.dumps({'result':'VIDEO_STM32_OK','video':args.video.name,'observations_accepted':sum(s['ok'] for f,s in observations),
                              'rpc_samples':len(received),'roi_stream_reset':changed,
                              'invalid_overflow_frames':sum(not f['valid'] for f,s in observations),
                              'valid_frames':sum(f['valid'] for f,s in observations),
                              'stale_frames_rejected':sum(s['error']=='STALE_FRAME' for f,s in observations),
                              'final_phase':received[-1][1]['phase'],'gpio':'none','transport':'host Bridge stub'},indent=2))
        finally:
            vision.stop.set();rt.stop.set()
            if vision.thread:vision.thread.join(timeout=3)
            if rt.thread:rt.thread.join(timeout=3)
            process.stdin.close();process.wait(timeout=3);process.stdout.close()


if __name__=='__main__':main()
