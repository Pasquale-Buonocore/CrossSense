# Prova quantizzazione e video 480p — 11 ottobre 2026

**Su questa UNO Q il candidato INT8 provato non conviene:** il guadagno a 320 è piccolo e non stabile tra le due finestre, mentre i conteggi peggiorano. FP16 dimezza il file dei pesi e conserva i conteggi host, ma non dà un'accelerazione utile. Il modello della demo resta NCNN FP32 a 320.

## Prestazioni misurate sulla scheda

NCNN 1.0.20260526, Ultralytics 8.4.175, due thread, Qualcomm Kryo-V2 a quattro core. NCNN rileva NEON ma `cpu_support_arm_asimdhp() = 0`: manca il calcolo FP16 nativo. L'export Ultralytics installato supporta `quantize=16` per NCNN, non `quantize=8`; INT8 è stato prodotto con gli strumenti NCNN della stessa versione.

| Ingresso | Pesi | File pesi | Mediana | p95 |
|---|---|---:|---:|---:|
| 320 | FP32 | 9.21 MiB | 133.4 ms | 141.4 ms |
| 320 | FP16 | 4.64 MiB | 132.7 ms | 140.4 ms |
| 320 | INT8 | 2.38 MiB | 129.1 ms | 137.1 ms |
| 384 | FP32 | 9.21 MiB | 191.7 ms | 210.7 ms |
| 384 | INT8 | 2.38 MiB | 192.2 ms | 209.1 ms |

Misure del solo forward NCNN, incluse le copie degli output, **non FPS della pipeline**. Ogni modello riceve gli stessi 36 frame dei due video attualmente installati, con ordine alternato e quattro warmup. La demo continua a girare in un altro processo, quindi sono confronti sotto carico e non un benchmark a CPU libera. In una prima finestra di 12 frame INT8 era leggermente più lento di FP32 (135.6 contro 134.5 ms): il piccolo vantaggio della seconda finestra non dimostra un'accelerazione stabile.

384 richiede indicativamente 1.44 volte il lavoro di 320; la latenza misurata aumenta di circa il 44%. Non c'è un guadagno da quantizzazione sufficiente a compensarlo. Gli FPS effettivi e le deadline RPC richiedono comunque una prova della pipeline completa prima di adottare un altro ingresso.

## Qualità: verifica limitata ai replay sintetici

INT8 PTQ con calibrazione KL su 66 frame dei cinque `output_*.mp4`, uno ogni 30 frame. Input `.npy`: limite lato sorgente 480, letterbox quadrata con padding 114, RGB CHW float32 diviso 255. Nessuna deformazione del rapporto d'aspetto in calibrazione. Pesi e attivazioni delle convoluzioni quantizzati dagli strumenti NCNN; gli altri operatori possono restare floating point.

La pipeline `VisionService` effettiva, con ByteTrack e confidenza 0.15, è stata eseguita sul Mac su tutti i 1980 frame per variante, senza MCU. I numeri sotto sono totali degli attraversamenti completi per video; le direzioni dettagliate restano nel JSON.

| Modello | Video 1 | Video 2 | Video 3 | Video 4 | Video 5 |
|---|---:|---:|---:|---:|---:|
| Attesi | 4 | 0 | 1 | 3 | 0 |
| FP32 320, host | 2 | 0 | 1 | 0 | 0 |
| FP16 320, host | 2 | 0 | 1 | 0 | 0 |
| INT8 320, host | 0 | 0 | 0 | 0 | 0 |
| FP32 384, host | 3 | 0 | 1 | 2 | 0 |
| INT8 384, host | 0 | 0 | 0 | 0 | 0 |

Questi conteggi non sono mAP, precision o recall delle box. Non equivalgono al precedente collaudo ARM: anche FP32 320 sul Mac differisce per il video 4. La calibrazione è piccola, sintetica e derivata dagli stessi video della verifica; manca un dataset annotato indipendente. L'esito boccia **questo candidato INT8**, non dimostra che ogni possibile calibrazione o QAT fallirà. Per promettere poca perdita di accuracy servono annotazioni separate, calibrazione rappresentativa anche dei nuovi video e validazione sulla scheda.

## Video aggiornati a 480p

Su richiesta dell'utente gli originali 2528×1696 sono stati riesportati a **716×480**: 480 indica ora l'altezza, non il massimo dei due lati. Tutti i sette video sono disponibili in `.local/replays-480p`, con manifest SHA256. I due video attualmente usati dalla demo, `fotoRealVideo.mp4` e `postProcessingVideo.mp4`, sono stati codificati direttamente dagli originali in H.264 CRF 18; entrambi conservano 180 frame e 15 FPS. I cinque replay sintetici conservano 1980 frame complessivi e 30 FPS.

I file sorgente della demo conservano la risoluzione 716×480. Il profilo App Lab corrente usa però il default `frame_size=480`, quindi la pipeline li riduce a circa 480×322 mantenendo le proporzioni; il detector riceve il suo ingresso a 320. Il precedente pacchetto sperimentale con `frame_size=716` conserva più dettaglio nella preview ma aumenta il carico sulla UNO Q e non è più il default. Non si attribuisce alla sola preview maggiore un miglioramento misurato dell'accuracy.

Backup sulla scheda: `/home/arduino/ArduinoApps/crosssense-replay-dashboard/.cache/video-480p-backup-20261011`, con video precedenti, configurazione e manifest. Il manifest attivo è stato aggiornato; il solo container Linux è stato riavviato.

Verifica API dopo l'aggiornamento: 30 campioni freschi del video selezionato `postProcessingVideo.mp4`, tutti a 716×480 con inferenza a 320 e collegamento MCU attivo. Inferenza mediana della pipeline 166.7 ms, FPS mediani 5.3. Nessun campione con entrambi i verdi. È una breve verifica operativa; non certifica accuratezza, assenza di transitori o prestazioni di lunga durata. Verificati inoltre tutti i frame dei sette export e superati i 18 test vision esistenti.

## Riproduzione

`scripts/prepare_replays.py` accetta ora `--height 480` in alternativa a `--max-size 480`. Il suo encoder resta MP4V; per i due video della demo si è usato H.264 dagli originali:

```sh
python scripts/prepare_replays.py --source simulation/output --destination .local/replays-480p --height 480
ffmpeg -i simulation/output/fotoRealVideo.mp4 -map 0:v:0 -vf scale=-2:480 -c:v libx264 -crf 18 -pix_fmt yuv420p -an -movflags +faststart .local/replays-480p/fotoRealVideo.mp4
```

Per il confronto dei modelli, `scripts/benchmark_ncnn.py` offre `calibrate`, `timing` e `replays`. Il benchmark rifiuta un `imgsz` diverso dall'export. `timing` usa i video presenti, `replays` verifica i cinque scenari con conteggi noti; non cambia il modello della demo né comunica con la MCU.

```sh
python scripts/benchmark_ncnn.py calibrate --video-dir .local/performance/videos-480 --imgsz 320 --output .local/quantization/calibration-320
ncnn2table model.ncnn.param model.ncnn.bin .local/quantization/calibration-320/inputs.txt model.table 'shape=[320,320,3]' thread=2 method=kl type=1
ncnn2int8 model.ncnn.param model.ncnn.bin int8.ncnn.param int8.ncnn.bin model.table
python scripts/benchmark_ncnn.py timing --video-dir .local/performance/videos-480 --model models/yolo26n_320_ncnn_model .local/quantization/yolo26n_fp16_320_ncnn_model .local/quantization/yolo26n_int8_320_ncnn_model --output .local/quantization/timing-host.json
```

Gli export sperimentali sono in `.local/quantization`, esclusi da Git. Evidenze conservate: [benchmark e conteggi](validation-results/quantization-20261011.json). Fonti ufficiali: [export NCNN Ultralytics](https://docs.ultralytics.com/integrations/ncnn/), [PTQ INT8 NCNN](https://github.com/Tencent/ncnn/wiki/quantized-int8-inference).
