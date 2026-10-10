"""Browser-independent dashboard/RT service inside Arduino App Lab."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'dashboard'))
from server import main

if __name__=='__main__':
    sys.argv=[sys.argv[0],'--bridge','--host','0.0.0.0','--port','8081']
    print('CrossSense RT Bridge: modalità protetta, nessun verde abilitato.',flush=True)
    main()
