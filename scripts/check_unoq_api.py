"""Deployed API contracts, ROI revision and request lifecycle; changes replay selection."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();checks=[]
    def call(path,data=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        request=urllib.request.Request(args.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=10) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as exc:return exc.code,json.load(exc)
    def passed(name):checks.append(name);print('API_CHECK_OK',name,flush=True)
    def wait(predicate):
        began=time.monotonic()
        while time.monotonic()-began<45:
            r=call('/api/rt')[1]
            if predicate(r):return r
            time.sleep(.1)
        raise AssertionError(('condition timeout',r))
    try:
        assert call('/api/vision/source',{'video':'../other.mp4'})[0]==400
        passed('catalog_path_rejected')
        assert call('/api/observations',{})[0]==409
        passed('replay_owns_observations')
        assert call('/api/requests',{'type':'pedestrian','request_id':'cross-origin'},'http://invalid.example')[0]==403
        passed('cross_origin_write_rejected')
        zones=call('/api/vision/zones')[1]
        code,saved=call('/api/vision/zones',zones);assert code==200 and saved['revision']==zones['revision']+1
        assert call('/api/vision/zones',zones)[0]==409
        assert call('/api/vision/zones')[1]==saved
        passed('roi_save_revision_conflict_and_readback')
        assert call('/api/vision/source',{'video':'output_2.mp4'})[0]==200
        assert call('/api/vision/play',{'unexpected':True})[0]==400
        assert call('/api/vision/play',{})[0]==200
        assert call('/api/vision/pause',{})[0]==200
        assert call('/api/vision/play',{})[0]==200
        assert call('/api/vision/restart',{})[0]==200
        passed('manual_replay_controls_contract')
        wait(lambda r:r['connected'] and r['state']['observation_valid'] and r['state']['phase']=='VEHICLE_GREEN')
        key='api-'+uuid.uuid4().hex;began=time.monotonic()
        while True:
            code,result=call('/api/requests',{'type':'pedestrian','request_id':key})
            assert code==200
            if result['status']!='rejected':break
            if time.monotonic()-began>10:raise AssertionError(result)
            time.sleep(.05)
        again=call('/api/requests',{'type':'pedestrian','request_id':key})[1]
        assert again['requestId']==key
        before=call('/api/rt')[1]
        assert sum(r['requestId']==key for r in before['requests'])==1
        passed('request_id_deduplicated')
        assert call('/api/vision/source',{'video':'output_1.mp4'})[0]==200
        after=wait(lambda r:any(v['requestId']==key and v['status']=='cancelled' for v in r['requests']))
        passed('source_change_cancels_pending_request')
        time.sleep(.5)
        assert call('/api/vision/zones')[1]==saved
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(checks=checks),indent=2))
    print('UNOQ_API_OK',args.output)


if __name__=='__main__':main()
