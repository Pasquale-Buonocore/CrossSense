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
parser.add_argument('--video-dir',type=Path,help='Includi tutti gli MP4 della cartella nel selettore dashboard')
parser.add_argument('--model',type=Path,default=root/'models'/'yolo26n.pt')
parser.add_argument('--zones-file',type=Path,help='Configurazione salvata dalla dashboard da usare nella app')
parser.add_argument('--loop-video',action='store_true')
parser.add_argument('--imgsz',type=int,default=360)
parser.add_argument('--inference-threads',type=int,choices=range(1,5))
parser.add_argument('--frame-size','--frame-height',dest='frame_size',type=int,default=360)
parser.add_argument('--zip',action='store_true',help='Crea anche uno ZIP importabile in Arduino App Lab')
args=parser.parse_args()
if not 32 <= args.imgsz <= 2048 or not 32 <= args.frame_size <= 2160: parser.error('Risoluzione non valida')
has_video=bool(args.video or args.video_dir)
if args.standard_cycle and has_video: parser.error('Usare --controller-cycle con video: due produttori di osservazioni non possono coesistere')
if args.video and not args.video.is_file(): parser.error('Video assente')
videos=sorted(args.video_dir.rglob('*.mp4')) if args.video_dir and args.video_dir.is_dir() else []
if args.video_dir and not videos: parser.error('Catalogo MP4 vuoto o assente')
if has_video and not (args.model.is_file() or (args.model.is_dir() and all((args.model/f).is_file() for f in ('model.ncnn.param','model.ncnn.bin','metadata.yaml')))): parser.error('Modello assente')
if args.zones_file and not args.zones_file.is_file(): parser.error('Configurazione zone assente')
if args.destination.exists(): parser.error('La destinazione deve essere nuova')
if args.zip and Path(str(args.destination)+'.zip').exists(): parser.error('Lo ZIP di destinazione esiste già')
shutil.copytree(root/'firmware',args.destination,ignore=shutil.ignore_patterns('__pycache__','tests','build','dist','*.exe'))
shutil.copytree(root/'dashboard',args.destination/'python'/'dashboard',ignore=shutil.ignore_patterns('__pycache__','tests','.local'))
shutil.copytree(root/'vision',args.destination/'python'/'vision',ignore=shutil.ignore_patterns('__pycache__','tests'))
if has_video:
    assets=args.destination/'python'/'vision'/'assets'
    assets.mkdir()
    source={'loop':args.loop_video,'imgsz':args.imgsz,'frame_size':args.frame_size}
    if args.inference_threads: source['inference_threads']=args.inference_threads
    if args.video: shutil.copy2(args.video,assets/'input.mp4');source['video']='input.mp4'
    if args.video_dir:
        for video in videos:
            target=assets/'videos'/video.relative_to(args.video_dir)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(video,target)
        source['video_directory']='videos'
        source['video']='videos/'+videos[0].relative_to(args.video_dir).as_posix()
    model_name='yolo26n_ncnn_model' if args.model.is_dir() else 'yolo26n.pt'
    if args.model.is_dir(): shutil.copytree(args.model,assets/model_name)
    else: shutil.copy2(args.model,assets/model_name)
    shutil.copy2(root/'vision'/'requirements-unoq.txt',args.destination/'python'/'requirements.txt')
    source['model']=model_name
    (args.destination/'python'/'vision-source.json').write_text(json.dumps(source))
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
if has_video:
    manifest=args.destination/'app.yaml'
    manifest.write_text('name: CrossSense YOLO Video\ndescription: Video YOLO, zone configurabili e telemetria STM32 tramite Bridge v1\nicon: 🚦\nports:\n  - 8080\nbricks: []\n',encoding='utf-8')
print(args.destination.resolve())
if args.zip:
    print(shutil.make_archive(str(args.destination),'zip',args.destination))
