"""Build the standalone App Lab directory without duplicating dashboard sources."""
import argparse
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination',type=Path)
parser.add_argument('--standard-cycle',action='store_true',help='Abilita il ciclo STM32 e avvia due cicli sintetici per i semafori dashboard')
parser.add_argument('--zip',action='store_true',help='Crea anche uno ZIP importabile in Arduino App Lab')
args=parser.parse_args()
if args.destination.exists(): parser.error('La destinazione deve essere nuova')
if args.zip and Path(str(args.destination)+'.zip').exists(): parser.error('Lo ZIP di destinazione esiste già')
shutil.copytree(root/'firmware',args.destination,ignore=shutil.ignore_patterns('__pycache__','tests','build','dist','*.exe'))
shutil.copytree(root/'dashboard',args.destination/'python'/'dashboard',ignore=shutil.ignore_patterns('__pycache__','tests'))
if args.standard_cycle:
    sketch=args.destination/'sketch'/'sketch.ino'
    sketch.write_text('#define CROSSSENSE_STANDARD_CYCLE 1\n'+sketch.read_text(encoding='utf-8'),encoding='utf-8')
    manifest=args.destination/'app.yaml'
    manifest.write_text(manifest.read_text(encoding='utf-8').replace('CrossSense RT Bridge','CrossSense Dashboard Cycle').replace('Bridge v1 dashboard e ricevitore STM32 in arresto protetto','Ciclo STM32 automatico tramite Bridge v1 e semafori dashboard, nessun GPIO'),encoding='utf-8')
    shutil.copy2(root/'scripts'/'try_standard_cycle.py',args.destination/'python'/'try_standard_cycle.py')
    (args.destination/'python'/'standard-cycle.enabled').touch()
print(args.destination.resolve())
if args.zip:
    print(shutil.make_archive(str(args.destination),'zip',args.destination))
