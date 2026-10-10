"""Synthetic Bridge tests of the flashed controller; run with the app producer stopped."""
import argparse
import copy
import json
from pathlib import Path
import secrets
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--producer-stopped',action='store_true',required=True)
    parser.add_argument('--native-controller',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    dashboard=root/'dashboard'
    if not dashboard.is_dir():dashboard=Path(__file__).parent/'dashboard'
    sys.path.insert(0,str(dashboard))
    from native import BridgeController,NativeController
    transport=NativeController(args.native_controller,timeout=2) if args.native_controller else BridgeController()
    # Startup is checked separately from steady-state RPC latency.
    transport.timeout=2
    stream=secrets.randbits(32);sequence=0;last=None;samples=[];checks=[]
    def call(frame):
        # The host stub advances testMillis by delay(10) on both loop calls.
        # Do not drive its wall clock backwards with immediate consecutive calls.
        if args.native_controller:time.sleep(.03)
        began=time.monotonic()
        state=json.loads(transport('crosssense_update',json.dumps(frame,separators=(',',':'))))
        assert not(state['vehicle_light']=='GREEN' and state['pedestrian_light']=='GREEN'),state
        samples.append(dict(state=state,rpc_ms=round((time.monotonic()-began)*1000,2)))
        return state
    def send(occupied=False,requests=None,valid=True,age=0):
        nonlocal sequence,last
        sequence+=1
        captured=max(round(time.monotonic()*1000),(last['time_ms']+1) if last else 0)
        last=dict(stream=stream,frame=sequence,time_ms=captured,age_ms=age,valid=valid,
            crossing='occupied' if occupied else 'clear' if valid else 'unknown',
            approach='clear' if valid else 'unknown',tracks=[[1,'pedestrian','crossing',None,None]] if occupied else [],
            requests=requests or [False]*3)
        return call(last)
    def until(predicate,occupied=False,timeout=15):
        began=time.monotonic()
        while time.monotonic()-began<timeout:
            s=send(occupied)
            if predicate(s):return s
            time.sleep(.2)
        raise AssertionError(('condition timeout',s))
    def passed(name):checks.append(name);print('MCU_CHECK_OK',name,flush=True)
    try:
        until(lambda s:s['phase']=='VEHICLE_GREEN');passed('startup_clear_recovery')
        send(requests=[True,False,False]);time.sleep(.05)
        until(lambda s:s['phase']=='PED_GREEN',timeout=8);passed('pedestrian_request_cycle')
        until(lambda s:s['phase']=='PED_CLEARANCE',occupied=True,timeout=7)
        until(lambda s:s['phase']=='PROTECTED_STOP' and 'CLEARANCE_TIMEOUT' in s['alarms'],occupied=True,timeout=12)
        assert all(x['state']['vehicle_light']=='RED' for x in samples if x['state']['phase'] in ('PED_GREEN','PED_CLEARANCE','PROTECTED_STOP'))
        passed('occupied_clearance_timeout_keeps_red')
        send(occupied=True,requests=[False,False,True]);time.sleep(.25)
        assert send(occupied=True)['vehicle_light']=='RED';passed('priority_cannot_release_occupied_crossing')
        until(lambda s:s['phase']=='VEHICLE_GREEN');passed('clearance_timeout_recovery')
        send(requests=[True,True,False]);time.sleep(.05)
        s=until(lambda s:s['phase']=='PED_GREEN',timeout=12)
        assert s['remaining_ms']>=7400,s
        began=time.monotonic()
        until(lambda s:s['phase']=='PED_CLEARANCE',timeout=10)
        assert time.monotonic()-began>=7.4;passed('accessible_green_eight_seconds')
        until(lambda s:s['phase']=='VEHICLE_GREEN')
        send(occupied=True);time.sleep(.2)
        s=send(occupied=True)
        assert s['phase']=='PROTECTED_STOP' and 'CROSSING_CONFLICT' in s['alarms'],s
        passed('green_vehicle_crossing_conflict')
        until(lambda s:s['phase']=='VEHICLE_GREEN')
        send();time.sleep(.2)
        old=copy.deepcopy(last)
        time.sleep(1.1)
        old['age_ms']=1300
        s=call(old)
        assert s['ok'] and s['fault']=='TIMEOUT' and s['phase']=='FAULT',s
        assert s['vehicle_light']==s['pedestrian_light']=='RED'
        passed('duplicate_does_not_refresh_watchdog')
        s=send(age=750)
        assert not s['ok'] and s['error']=='STALE_FRAME',s
        passed('stale_frame_rejected')
        until(lambda s:s['phase']=='VEHICLE_GREEN')
        invalid=copy.deepcopy(last);invalid['frame']+=1;invalid['tracks']=[[1,'pedestrian','crossing',None,None]]
        s=call(invalid)
        assert not s['ok'] and s['error']=='BAD_DATA',s
        passed('inconsistent_clear_frame_rejected')
        send(valid=False);time.sleep(.2)
        s=send(valid=False)
        assert s['fault']=='INVALID_DATA' and s['phase']=='FAULT',s
        passed('invalid_observation_protected_stop')
        stream=secrets.randbits(32)
        until(lambda s:s['phase']=='VEHICLE_GREEN');passed('new_stream_clear_recovery')
    finally:
        try:send(valid=False)
        finally:transport.close()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(checks=checks,samples=samples),indent=2))
    print('MCU_INTEGRATION_OK',args.output)


if __name__=='__main__':main()
