"""HTTP check of replay loop rollover; requires the deployed app loop enabled."""
import argparse
import json
from pathlib import Path
import time
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    def call(path,data=None):
        request=urllib.request.Request(args.url.rstrip('/')+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
    call('/api/vision/source',{'video':'output_2.mp4'})
    began=time.monotonic();first=None;wire=None;seen=set();report={}
    while time.monotonic()-began<150:
        vision,rt=call('/api/vision'),call('/api/rt')
        assert vision['source']=='output_2.mp4'
        if rt['state']:
            assert not(rt['state']['vehicle_light']=='GREEN' and rt['state']['pedestrian_light']=='GREEN')
            if rt['connected'] and rt['state']['observation_valid']:
                if wire is None:wire=rt['state']['applied_stream']
        frame=vision['frame']
        if frame:
            assert max(frame['width'],frame['height'])<=480 and frame['inference_size']<=320
            if first is None:first=frame['stream']
            seen.add(frame['stream'])
            if frame['stream']!=first and rt['connected'] and rt['state']['observation_valid'] and rt['state']['applied_stream']!=wire:
                report=dict(ok=True,seconds=round(time.monotonic()-began,2),streams=list(seen),
                    resumed_video_frame=frame['video_frame'],new_wire_stream=rt['state']['applied_stream'],
                    phase=rt['state']['phase'],metrics=vision['metrics'])
                break
        time.sleep(.15)
    else:raise AssertionError('Replay loop/new MCU stream was not observed')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    print('UNOQ_LOOP_OK',report['seconds'],report['resumed_video_frame'])


if __name__=='__main__':main()
