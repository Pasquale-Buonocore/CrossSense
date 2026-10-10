"""UNO Q cached cold app startup with Docker network none; restores the main app."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    app=args.app.resolve()
    if str(app)!='/home/arduino/ArduinoApps/crosssense-replay-dashboard':
        raise ValueError('Only the dedicated replay test app is supported')
    main_container='crosssense-replay-dashboard-main-1'
    offline='crosssense-offline-check'
    def command(*parts):return subprocess.run(parts,check=True,capture_output=True,text=True).stdout
    image=command('docker','inspect',main_container,'--format','{{.Config.Image}}').strip()
    report={};created=False
    command('docker','stop',main_container)
    try:
        command('docker','run','-d','--name',offline,'--network','none','--user','1000:1000',
                '-e','BOARD_NAME=unoq','-e','UV_OFFLINE=1','-e','APP_HOME='+str(app),
                '-v',str(app)+':/app','-v','/run/arduino-router.sock:/run/arduino-router.sock',
                '--entrypoint','/run.sh',image)
        created=True;began=time.monotonic();samples=[]
        query="import json,urllib.request; print(json.dumps({p:json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/'+p,timeout=5)) for p in ('config','vision','rt')}))"
        while time.monotonic()-began<120:
            try:
                value=json.loads(command('docker','exec',offline,'/usr/local/bin/python','-c',query))
                rt=value['rt'];vision=value['vision']
                if rt['state']:assert not(rt['state']['vehicle_light']=='GREEN' and rt['state']['pedestrian_light']=='GREEN')
                if rt['connected'] and rt['state']['observation_valid'] and vision['fresh']:
                    samples.append(value)
                    if len(samples)>=3 and samples[-1]['vision']['frame']['video_frame']>samples[0]['vision']['frame']['video_frame']+5:break
            except (subprocess.CalledProcessError,json.JSONDecodeError):pass
            time.sleep(1)
        else:raise AssertionError('Offline vision/Bridge startup did not recover in 120 seconds')
        assert value['config']['controller']=='bridge' and value['config']['source']=='replay'
        assert max(value['vision']['frame'][k] for k in ('width','height'))<=480
        assert value['vision']['frame']['inference_size']<=320
        network=command('docker','inspect',offline,'--format','{{.HostConfig.NetworkMode}}').strip()
        interfaces=command('docker','exec',offline,'ls','/sys/class/net').split()
        assert network=='none' and interfaces==['lo'],(network,interfaces)
        report=dict(ok=True,seconds=round(time.monotonic()-began,2),network=network,interfaces=interfaces,
                    samples=samples,scope='cached Linux app cold startup; not initial provisioning or Linux OS reboot')
        print('UNOQ_OFFLINE_OK',report['seconds'],flush=True)
    finally:
        if created:
            report['startup_log']=command('docker','logs',offline)[-8000:]
            command('docker','stop',offline);command('docker','rm',offline)
        command('docker','start',main_container)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
