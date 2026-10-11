"""Run on UNO Q: inject Linux/Bridge faults into a dedicated test app only.

Stops/restarts the named container and creates then removes one invalid replay.
Use --mcu-upload to reflash the existing cached sketch and verify MCU recovery.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--container',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mcu-upload',action='store_true')
    args=parser.parse_args();checks=[]
    if args.container!='crosssense-replay-dashboard-main-1':
        raise ValueError('Only the dedicated replay test container is supported')
    if args.app.resolve()!=Path('/home/arduino/ArduinoApps/crosssense-replay-dashboard'):
        raise ValueError('Only the dedicated replay test app is supported')
    def command(*parts):
        return subprocess.run(parts,check=True,capture_output=True,text=True).stdout
    def call(path,data=None):
        request=urllib.request.Request('http://127.0.0.1:8080'+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
    def wait(predicate,timeout=45):
        began=time.monotonic();last=None
        while time.monotonic()-began<timeout:
            try:
                last=call('/api/rt')
                if last['state']:
                    assert not(last['state']['vehicle_light']=='GREEN' and last['state']['pedestrian_light']=='GREEN')
                if predicate(last):return last
            except (OSError,ValueError):pass
            time.sleep(.05)
        raise AssertionError(('condition timeout',last))
    def healthy(r):return r['connected'] and r['state']['observation_valid']
    def select_and_play(name):
        call('/api/vision/source',{'video':name})
        call('/api/vision/play',{})
    def passed(name,**evidence):
        checks.append(dict(check=name,**evidence));print('RESILIENCE_OK',name,flush=True)
    bad=args.app/'python/vision/assets/videos/test-invalid.mp4'
    paused=False;asset_created=False
    try:
        select_and_play('output_2.mp4');before=wait(healthy)
        event=before['events'][-1]['id'] if before['events'] else 0
        rows=command('docker','top',args.container,'-eo','pid,args').splitlines()
        workers=[int(r.split()[0]) for r in rows if '/dashboard/bridge_worker.py' in r]
        assert len(workers)==1,rows
        command('kill','-STOP',str(workers[0]))
        restarted=wait(lambda r:any(e['id']>event and e['type']=='RESTART' and 'Trasporto' in e['message'] for e in r['events']))
        recovery=wait(healthy)
        passed('blocked_bridge_worker_restarted',events=restarted['events'][-4:],stream=recovery['state']['applied_stream'])
        command('docker','pause',args.container);paused=True;time.sleep(1.4)
        # A malformed read-only RPC does not replace accepted observations.
        # Query the MCU independently while every main-app process is frozen.
        image=command('docker','inspect',args.container,'--format','{{.Config.Image}}').strip()
        query="import sys; sys.path.insert(0,'/app/python/dashboard'); from native import BridgeController; t=BridgeController(); t.timeout=2; print(t('crosssense_update','{\"frame\":1}')); t.close()"
        raw=command('docker','run','--rm','--name','crosssense-watchdog-check','--network','none','--user','1000:1000',
            '-v',str(args.app)+':/app','-v','/run/arduino-router.sock:/run/arduino-router.sock',
            '--entrypoint','/app/.cache/.venv/bin/python',image,'-c',query)
        watchdog=json.loads(raw)
        assert watchdog['error']=='BAD_DATA' and watchdog['fault']=='TIMEOUT' and watchdog['phase']=='FAULT',watchdog
        assert watchdog['vehicle_light']=='RED' and watchdog['pedestrian_light']=='RED',watchdog
        command('docker','unpause',args.container);paused=False
        wait(healthy)
        passed('linux_pause_watchdog_and_recovery',fault=watchdog['fault'],state=watchdog)
        if bad.exists():raise ValueError('Test asset already exists')
        bad.write_bytes(b'invalid replay for controlled test')
        asset_created=True
        select_and_play(bad.name)
        wait(lambda r:r['state'] and r['state']['phase']=='FAULT')
        began=time.monotonic()
        while time.monotonic()-began<15:
            vision=call('/api/vision')
            if vision['status']=='error':break
            time.sleep(.1)
        assert vision['status']=='error' and not vision['fresh'],vision
        select_and_play('output_2.mp4');wait(healthy)
        bad.unlink();asset_created=False;passed('invalid_video_error_and_recovery',error=vision['error'])
        before=wait(healthy)
        command('docker','restart',args.container)
        began=time.monotonic()
        while True:
            try:
                select_and_play('output_2.mp4');break
            except OSError:
                if time.monotonic()-began>120:raise
                time.sleep(.5)
        after=wait(healthy,timeout=120)
        assert before['state']['applied_stream']!=after['state']['applied_stream']
        passed('linux_process_restart',new_stream=after['state']['applied_stream'])
        if args.mcu_upload:
            before=wait(healthy);event=before['events'][-1]['id']
            upload=command('arduino-cli','upload','--fqbn','arduino:zephyr:unoq','--input-dir',str(args.app/'.cache/sketch'),'--profile','default',str(args.app/'sketch'))
            reboot=wait(lambda r:any(e['id']>event and e['type']=='RESTART' for e in r['events']),timeout=60)
            wait(healthy,timeout=120)
            passed('mcu_reflash_reconnect',upload=upload[-1200:],events=reboot['events'][-6:])
    finally:
        if paused:command('docker','unpause',args.container)
        if asset_created and bad.exists():
            try:call('/api/vision/source',{'video':'output_2.mp4'})
            finally:bad.unlink()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(checks=checks),indent=2))
    print('UNOQ_RESILIENCE_OK',args.output)


if __name__=='__main__':main()
