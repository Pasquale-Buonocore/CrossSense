"""Browser-independent dashboard/RT service inside Arduino App Lab."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'dashboard'))
from server import main

if __name__=='__main__':
    sys.argv=[sys.argv[0],'--bridge','--host','0.0.0.0','--port','8080']
    demo=(Path(__file__).resolve().parent/'standard-cycle.enabled').exists()
    print('CrossSense RT Bridge: '+('ciclo sintetico automatico, semafori nella dashboard, nessun GPIO.' if demo else 'modalità protetta, semafori logici rossi.'),flush=True)
    on_ready=None
    if demo:
        from cycle_demo import start_demo
        on_ready=start_demo
    main(on_ready=on_ready)
