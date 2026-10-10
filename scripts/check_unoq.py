"""Black-box replay/dashboard checks against the deployed UNO Q HTTP service."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid


def percentile(values, percent):
    if not values:return None
    ordered=sorted(values)
    return round(ordered[min(len(ordered)-1,int((len(ordered)-1)*percent/100))],2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=900)
    parser.add_argument('--video')
    parser.add_argument('--requests-only',action='store_true')
    args=parser.parse_args()
    expected=json.loads((Path(__file__).resolve().parents[1]/'simulation/expected-events.json').read_text())['videos']
    def api(path,data=None):
        request=urllib.request.Request(args.url.rstrip('/')+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json'} if data is not None else {})
        with urllib.request.urlopen(request,timeout=10) as response:return json.load(response)
    began=time.monotonic()
    while True:
        try:
            config=api('/api/config');break
        except (OSError,urllib.error.URLError):
            if time.monotonic()-began>120:raise
            time.sleep(1)
    assert config['controller']=='bridge',config
    reports=[]; failures=[]
    try:
        if not args.requests_only:
            for video in ([args.video] if args.video else list(expected)):
                selected=api('/api/vision/source',{'video':video})
                baseline=selected['metrics'];began=time.monotonic();last_progress=began
                inference=[];rpc=[];age=[];fps=[];faults={};errors={};phases=set()
                frame_serial=uptime=None;frames=connected=disconnected=0;jpeg_checked=False
                while time.monotonic()-began<args.timeout:
                    v=api('/api/vision');rt=api('/api/rt');s=rt['state']
                    assert v['selected_video']==video,('Replay changed during test',v['selected_video'],video)
                    if s:
                        assert not(s['vehicle_light']=='GREEN' and s['pedestrian_light']=='GREEN'),s
                        phases.add(s['phase'])
                        if s['uptime_ms']!=uptime:
                            uptime=s['uptime_ms']
                            if rt['connected']:connected+=1
                            else:disconnected+=1
                            if s['fault']:faults[s['fault']]=faults.get(s['fault'],0)+1
                            if rt['error']:errors[rt['error']]=errors.get(rt['error'],0)+1
                            if rt['rpc_ms'] is not None:rpc.append(rt['rpc_ms'])
                            if rt['sent_age_ms'] is not None:age.append(rt['sent_age_ms'])
                    f=v['frame']
                    if f and f['serial']!=frame_serial:
                        assert max(f['width'],f['height'])<=480,f
                        assert f['inference_size']<=320,f
                        frame_serial=f['serial'];frames+=1
                        inference.append(f['inference_ms'])
                        if f['fps'] is not None:fps.append(f['fps'])
                        if not jpeg_checked:
                            try:
                                with urllib.request.urlopen(args.url+'/api/vision/frame.jpg?serial='+str(frame_serial),timeout=10) as image:
                                    assert image.headers.get_content_type()=='image/jpeg'
                                    assert image.read(2)==b'\xff\xd8'
                                jpeg_checked=True
                            except urllib.error.HTTPError as exc:
                                if exc.code!=404:raise
                    if v['status']=='error':raise RuntimeError(v['error'])
                    if v['status']=='completed':break
                    if time.monotonic()-last_progress>=15:
                        print('PROGRESS',video,f['video_frame'] if f else None,v['metrics']['completed']-baseline['completed'],flush=True)
                        last_progress=time.monotonic()
                    time.sleep(.2)
                else:raise RuntimeError('Replay timeout: '+video)
                time.sleep(1.2)
                end=api('/api/rt')
                assert end['state']['phase']=='FAULT' and end['state']['vehicle_light']=='RED' and end['state']['pedestrian_light']=='RED',end
                metrics={k:v['metrics'][k]-baseline[k] for k in ('completed','left_to_right','right_to_left')}
                for key,count in expected.get(video,{}).items():
                    if metrics[key]!=count:failures.append(f'{video}: {key} expected={count}, actual={metrics[key]}')
                report=dict(video=video,seconds=round(time.monotonic()-began,2),observed_frames=frames,metrics=metrics,
                    inference_median_ms=percentile(inference,50),inference_p95_ms=percentile(inference,95),
                    rpc_median_ms=percentile(rpc,50),rpc_p95_ms=percentile(rpc,95),rpc_max_ms=max(rpc,default=None),
                    sent_age_p95_ms=percentile(age,95),pipeline_fps_median=percentile(fps,50),connected_samples=connected,
                    disconnected_samples=disconnected,fault_samples=faults,transport_errors=errors,phases=sorted(phases),jpeg_verified=jpeg_checked)
                reports.append(report);print(json.dumps(report),flush=True)
        selected=api('/api/vision/source',{'video':'output_2.mp4'})
        def wait(predicate,timeout=75):
            began=time.monotonic()
            while time.monotonic()-began<timeout:
                rt=api('/api/rt');v=api('/api/vision')
                if v['status']=='error':raise RuntimeError(v['error'])
                if predicate(rt,v):return rt,v
                time.sleep(.2)
            raise RuntimeError('Timeout waiting for dashboard/controller condition')
        wait(lambda rt,v:rt['connected'] and v['fresh'] and any(d['zone'].startswith('waiting_') for d in (v['frame'] or {}).get('detections',[])))
        request_report=[]
        for kind in ('accessible','vehicle_priority','pedestrian'):
            key='unoq-check-'+uuid.uuid4().hex;began=time.monotonic()
            while True:
                result=api('/api/requests',{'type':kind,'request_id':key})
                if result['status']!='rejected':break
                if time.monotonic()-began>10:raise RuntimeError(result)
                time.sleep(.05)
            def served(rt,v):return any(r['requestId']==key and r['status']=='served' for r in rt['requests'])
            rt,v=wait(served)
            if kind=='accessible':
                assert rt['state']['phase']=='PED_GREEN' and rt['state']['remaining_ms']>=6000,rt
            request_report.append(dict(type=kind,status='served',seconds=round(time.monotonic()-began,2),remaining_ms=rt['state']['remaining_ms']))
            print('REQUEST_OK',kind,flush=True)
        reports.append({'requests':request_report})
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(config=config,reports=reports,failures=failures),indent=2))
    if failures:raise AssertionError('; '.join(failures))
    print('UNOQ_HTTP_OK',args.output)


if __name__=='__main__':main()
