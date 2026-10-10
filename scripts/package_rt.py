"""Build the standalone App Lab directory without duplicating dashboard sources."""
import argparse
import json
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination',type=Path)
parser.add_argument('--standard-cycle',action='store_true',help='Abilita il ciclo STM32 e avvia due cicli sintetici per i semafori dashboard')
parser.add_argument('--controller-cycle',action='store_true',help='Abilita il ciclo STM32 senza il generatore di osservazioni sintetiche')
parser.add_argument('--video',type=Path,help='Includi un MP4 nella app e avvia YOLO')
parser.add_argument('--model',type=Path,default=root/'models'/'yolo26n.pt')
parser.add_argument('--zones-file',type=Path,help='Configurazione salvata dalla dashboard da usare nella app')
parser.add_argument('--loop-video',action='store_true')
parser.add_argument('--zip',action='store_true',help='Crea anche uno ZIP importabile in Arduino App Lab')
args=parser.parse_args()
if args.standard_cycle and args.video: parser.error('Usare --controller-cycle con --video: due produttori di osservazioni non possono coesistere')
if args.video and (not args.video.is_file() or not args.model.is_file()): parser.error('Video o modello assente')
if args.zones_file and not args.zones_file.is_file(): parser.error('Configurazione zone assente')
if args.destination.exists(): parser.error('La destinazione deve essere nuova')
if args.zip and Path(str(args.destination)+'.zip').exists(): parser.error('Lo ZIP di destinazione esiste già')
shutil.copytree(root/'firmware',args.destination,ignore=shutil.ignore_patterns('__pycache__','tests','build','dist','*.exe'))
shutil.copytree(root/'dashboard',args.destination/'python'/'dashboard',ignore=shutil.ignore_patterns('__pycache__','tests','.local'))
shutil.copytree(root/'vision',args.destination/'python'/'vision',ignore=shutil.ignore_patterns('__pycache__','tests'))
if args.video:
    assets=args.destination/'python'/'vision'/'assets'
    assets.mkdir()
    shutil.copy2(args.video,assets/'input.mp4')
    shutil.copy2(args.model,assets/'yolo26n.pt')
    shutil.copy2(root/'vision'/'requirements.txt',args.destination/'python'/'requirements.txt')
    (args.destination/'python'/'vision-source.json').write_text(json.dumps({'loop':args.loop_video}))
if args.zones_file:
    local=args.destination/'python'/'dashboard'/'.local'
    local.mkdir(parents=True,exist_ok=True)
    shutil.copy2(args.zones_file,local/'vision-zones.json')
if args.standard_cycle or args.controller_cycle:
    (args.destination/'python'/'controller-cycle.enabled').touch()
    sketch=args.destination/'sketch'/'sketch.ino'
    sketch.write_text('#define CROSSSENSE_STANDARD_CYCLE 1\n'+sketch.read_text(encoding='utf-8'),encoding='utf-8')
    manifest=args.destination/'app.yaml'
    manifest.write_text(manifest.read_text(encoding='utf-8').replace('CrossSense RT Bridge','CrossSense Dashboard Cycle').replace('Bridge v1 dashboard e ricevitore STM32 in arresto protetto','Ciclo STM32 automatico tramite Bridge v1 e semafori dashboard, nessun GPIO'),encoding='utf-8')
if args.standard_cycle:
    shutil.copy2(root/'scripts'/'try_standard_cycle.py',args.destination/'python'/'try_standard_cycle.py')
    (args.destination/'python'/'standard-cycle.enabled').touch()
print(args.destination.resolve())
if args.zip:
    print(shutil.make_archive(str(args.destination),'zip',args.destination))
