# Asset del replay e riproducibilità

I cinque file `simulation/output/output_1.mp4` … `output_5.mp4` sono replay sintetici da sprite, rispettivamente 360, 390, 300, 510, 420 frame a 30 FPS. Il controller non controlla gli attori del video.

Modello preparato durante lo sviluppo: YOLO26n pretrained ufficiale, [Ultralytics](https://docs.ultralytics.com/models/yolo26/).

- URL: https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt
- Destinazione: `models/yolo26n.pt`, esclusa da Git.
- SHA256: `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`.
- Runtime test host: Ultralytics 8.4.175, lap 0.5.13, PyTorch CPU 2.14.1, torchvision CPU 0.29.1. Non equivale a benchmark ARM.
- Classi effettive: COCO; il progetto inoltra person, bicycle, car, motorcycle, bus, truck. Nessuna classe dedicata per ambulanza o ausili.
- Licenza e condizioni dei pesi/software: riferimenti ufficiali Ultralytics; conservare le attribuzioni nella distribuzione.

Preparare virtualenv, dipendenze e modello mentre la rete è disponibile. Il runtime imposta `YOLO_OFFLINE=true` e `YOLO_AUTOINSTALL=false` prima di importare Ultralytics. Non attende un download implicito all’avvio. La configurazione Ultralytics è locale all’app.

Per UNO Q si usano i requirements ARM in `vision/requirements-unoq.txt`. Il profilo corrente usa video entro **480×480** e inferenza entro **320×320**. Esportare NCNN a **320** e passare a `--model` la directory contenente `model.ncnn.param`, `model.ncnn.bin`, `metadata.yaml`. Export eseguito con PNNX 20260526 e NCNN 1.0.20260526. Il pacchetto contiene cinque video ridotti a 480×322, modello e manifest SHA256 dei nove asset. `scripts/prepare_replays.py` conserva tutti i 1980 frame e i 30 FPS dei file; la pipeline li elabora più lentamente.

Runtime effettivamente provato sulla scheda: Python 3.13.14, PyTorch 2.8.0, torchvision 0.23, Ultralytics 8.4.175, NCNN 1.0.20260526, lap 0.5.13 e OpenCV headless 4.13 nell'immagine App Lab `python-apps-base:0.12.0`. Prima installazione e compilazione richiedono dipendenze/cache preparate. Risultati di conteggio e prestazioni in [unoq-validation.md](unoq-validation.md); le prove host 960/640 sono storiche.
