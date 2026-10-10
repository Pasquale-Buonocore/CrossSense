"""Browser-independent dashboard/RT service inside Arduino App Lab."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'dashboard'))
from server import main

if __name__=='__main__':
    sys.argv=[sys.argv[0],'--bridge','--host','0.0.0.0','--port','8080']
    source=Path(__file__).resolve().parent/'vision-source.json'
    if source.exists():
        assets=source.parent/'vision'/'assets'
        sys.argv+=['--video',str(assets/'input.mp4'),'--model',str(assets/'yolo26n.pt')]
        if json.loads(source.read_text()).get('loop'): sys.argv+=['--loop-video']
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
