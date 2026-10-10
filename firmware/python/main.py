"""Browser-independent dashboard/RT service inside Arduino App Lab."""
from pathlib import Path
import json
import os
import sys
if os.environ.get('BOARD_NAME') == 'unoq':
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[name] = '1'
if os.environ.get('BOARD_NAME') == 'unoq':
    # App Lab provides headless OpenCV. Prefer it to the GUI wheel pulled by
    # Ultralytics in the app venv, which requires libGL absent from this image.
    base_site=Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
    if (base_site/'cv2').is_dir():
        sys.path.insert(0,str(base_site))
        try:
            import cv2
        finally:
            sys.path.pop(0)
sys.path.insert(0,str(Path(__file__).resolve().parent/'dashboard'))
from server import main

if __name__=='__main__':
    sys.argv=[sys.argv[0],'--bridge','--host','0.0.0.0','--port','8080']
    source=Path(__file__).resolve().parent/'vision-source.json'
    if source.exists():
        assets=source.parent/'vision'/'assets'
        config=json.loads(source.read_text())
        sys.argv+=['--video',str(assets/config.get('video','input.mp4')),'--model',str(assets/config.get('model','yolo26n.pt')),
                   '--imgsz',str(config.get('imgsz',320)),'--frame-size',str(config.get('frame_size',480)),
                   '--confidence',str(config.get('confidence',.30))]
        if config.get('loop'): sys.argv+=['--loop-video']
        if config.get('inference_threads'): sys.argv+=['--inference-threads',str(config['inference_threads'])]
        if config.get('video_directory'): sys.argv+=['--video-dir',str(assets/config['video_directory'])]
    demo=(Path(__file__).resolve().parent/'standard-cycle.enabled').exists()
    if demo and source.exists(): raise RuntimeError('Video YOLO e prova sintetica devono usare app separate')
    cycle=(Path(__file__).resolve().parent/'controller-cycle.enabled').exists()
    status='video YOLO locale, telemetria STM32, nessun GPIO.' if source.exists() else 'ciclo sintetico automatico, semafori nella dashboard, nessun GPIO.' if demo else 'ciclo STM32, in attesa di osservazioni, nessun GPIO.' if cycle else 'modalità protetta, semafori logici rossi.'
    print('CrossSense RT Bridge: '+status,flush=True)
    on_ready=None
    if demo:
        from cycle_demo import start_demo
        on_ready=start_demo
    main(on_ready=on_ready)
