"""Real local YOLO -> observations -> actual native firmware, without any board."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'dashboard')]
from native import NativeController
from rt import RTService
from vision.pipeline import VisionService
from vision.zones import ZoneStore


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=root/'models/yolo26n.pt')
    parser.add_argument('--controller',type=Path,required=True)
    parser.add_argument('--video-dir',type=Path,default=root/'simulation/output')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--video',type=Path)
    parser.add_argument('--imgsz',type=int,default=320)
    parser.add_argument('--frame-size',type=int,default=480)
    parser.add_argument('--confidence',type=float,default=.15)
    parser.add_argument('--assert-counts',action='store_true',help='Verifica le traiettorie note dei cinque replay del repository')
    args=parser.parse_args()
    reports=[]
    expected=json.loads((root/'simulation/expected-events.json').read_text(encoding='utf-8'))['videos']
    with tempfile.TemporaryDirectory() as folder:
        for video in ([args.video] if args.video else sorted(args.video_dir.glob('*.mp4'))):
            transport=NativeController(args.controller)
            samples=[]
            def call(method,payload):
                raw=transport(method,payload)
                samples.append((json.loads(payload),json.loads(raw)))
                return raw
            rt=RTService(call)
            vision=VisionService(rt,ZoneStore(Path(folder)/'zones.json'),video,args.model,
                                 imgsz=args.imgsz,frame_size=args.frame_size,confidence=args.confidence,inference_threads=2)
            rt.start(); began=time.monotonic()
            try:
                vision.start();vision.thread.join(timeout=180)
                if vision.thread.is_alive():raise RuntimeError(f'Timeout: {video.name}')
                if vision.status!='completed':raise RuntimeError(vision.error)
                time.sleep(.4)
                acquired=[(f,s) for f,s in samples if f['time_ms'] is not None]
                assert acquired and any(s['ok'] for _,s in acquired)
                assert all(not(s['vehicle_light']=='GREEN' and s['pedestrian_light']=='GREEN') for _,s in samples)
                assert samples[-1][0]['time_ms'] is None
                assert any(s['phase']=='FAULT' for _,s in samples[-2:])
                report=dict(video=video.name,seconds=round(time.monotonic()-began,2),
                    frames=vision.serial,rpc_samples=len(samples),valid_samples=sum(f['valid'] for f,_ in acquired),
                    accepted=sum(s['ok'] for _,s in acquired),phases=sorted({s['phase'] for _,s in samples}),
                    alarms=sorted({a for _,s in samples for a in s['alarms']}),
                    metrics=vision.events.snapshot(),final_phase=samples[-1][1]['phase'])
                if args.assert_counts:
                    for direction,value in expected[video.name].items():
                        assert report['metrics'][direction]==value,(video.name,direction,value,report['metrics'])
                reports.append(report); print(json.dumps(report),flush=True)
            finally:
                vision.stop.set();rt.stop.set()
                if vision.thread:vision.thread.join(timeout=3)
                if rt.thread:rt.thread.join(timeout=1)
                transport.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(reports,indent=2),encoding='utf-8')
    print('REAL_REPLAYS_OK',args.output)


if __name__=='__main__':main()
