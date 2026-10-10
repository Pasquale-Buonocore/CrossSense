# Visione YOLO → RT → dashboard

Integrazione della detection di Gaetano (`tracking_immagine.py` e tracking
ByteTrack dei suoi script video). Modello locale YOLO26n, pedoni, biciclette,
auto, moto, autobus e camion. Nessun download automatico del modello.
`config/gaetano-zones.json` e `config/reference.jpg` provengono dalla consegna
di Gaetano; le ROI iniziali sono per la stessa inquadratura del video sintetico.

```sh
.venv/bin/python -m pip install -r vision/requirements.txt
.venv/bin/python dashboard/server.py --video /percorso/video-sintetico.mp4 --model models/yolo26n.pt --loop-video
```

Aprire http://127.0.0.1:8080. La pagina parte in Hardware quando un video è
configurato, anche senza MCU: la visione funziona e il controller risulta
disconnesso. Sulla UNO Q aggiungere `--bridge --host 0.0.0.0` nello stesso
ambiente che fornisce `arduino.app_utils`. Un solo `RTService` possiede Bridge;
il worker YOLO pubblica l'ultimo frame senza attendere la RPC. Dashboard chiusa
non interrompe elaborazione né scambi RT.

Il selettore **Video simulazione** mostra gli MP4 di `simulation/output`
(oppure della cartella indicata con `--video-dir`). Cambiare scelta avvia
il video dall'inizio, azzera ByteTrack, cambia stream RT e scarta i risultati
in elaborazione del video precedente. Le zone vengono mantenute; il selettore
è disabilitato mentre le si modifica. La scelta è condivisa dai browser e
persiste in `dashboard/.local/selected-video.json`. Solo file presenti nel
catalogo sono selezionabili: non si accettano URL o percorsi esterni.

Ogni frame decodificato viene elaborato con `model.track(..., persist=True,
tracker='bytetrack.yaml')`; se l'inferenza è più lenta del video, il replay
rallenta senza saltare frame. Il timestamp RT è monotono al momento della
lettura, mentre `video_ms` indica separatamente la posizione nel file.
`--device cpu`, `--confidence 0.30`, `--frame-size 360` e `--imgsz 360` sono i valori iniziali. Entrambi i lati dei frame restano entro 360 pixel, mantenendo il rapporto; le ROI normalizzate non cambiano. Per la sorgente di prova 1264×848 il frame è 360×242. Il lato di inferenza viene arrotondato **per difetto** allo stride: 352 per YOLO26n, così anche l'ingresso al modello resta entro 360×360. `--frame-height` è un alias compatibile di `--frame-size` e limita entrambi i lati.
Senza `--loop-video`, EOF pubblica indisponibilità; con loop riapre il file,
resetta ByteTrack e genera un nuovo stream. Errori di lettura/inferenza e stop
pubblicano un frame invalido. Un video lungo non viene accumulato in memoria.

## Zone configurabili dalla dashboard

1. Premere **Configura zone YOLO**: il frame visualizzato si ferma; inferenza e
   RT continuano. Senza video viene mostrata l'immagine di riferimento.
2. Scegliere Attesa sinistra, Attraversamento, Attesa destra o Corsia veicoli.
3. **Svuota zona**, poi cliccare i vertici in ordine. **Annulla vertice** rimuove
   l'ultimo punto; **Annulla** scarta tutte le modifiche locali.
4. **Salva zone** valida e salva tutti e quattro i poligoni atomicamente.

Da 3 a 32 punti per zona; poligoni degeneri o con lati incrociati rifiutati.
Coordinate normalizzate rispetto all'immagine: resize e diverse risoluzioni
mantengono le zone, purché l'inquadratura sia la stessa. La classificazione
usa il punto inferiore centrale della box e la distanza dal poligono,
con la tolleranza originale di Gaetano scalata alla risoluzione.
Le zone sovrapposte scelgono quella col punto più interno, come nel sorgente.

La configurazione persiste in `dashboard/.local/vision-zones.json`, configurabile
con `--zones-file`; viene condivisa dai browser e sopravvive al riavvio.
Salvare una revisione superata restituisce 409: annullare e riaprire l'editor
per acquisire le modifiche dell'altro browser. Un salvataggio riuscito cambia
stream, invalida subito lo snapshot precedente e resetta il tracker. Risultati
in elaborazione sulla revisione vecchia vengono scartati.

## Osservazioni e API

`GET /api/vision`: stato, freschezza, errore, configurazione e ultimo frame,
con detection `{id, class, label, confidence, bbox, zone}`, tempo di inferenza,
indice nel video e osservazione [Bridge v1](../protocol/bridge-v1.md), oltre
a `videos` e `selected_video`. `POST /api/vision/source`: `{video: id}`
seleziona un ID del catalogo e invalida subito le osservazioni precedenti.
`GET /api/vision/frame.jpg?serial=N`: JPEG annotato di quel preciso snapshot;
cache limitata agli ultimi quattro JPEG. `GET /api/vision/reference.jpg`:
immagine per configurare le ROI senza video. `GET /api/vision/zones` e
`POST /api/vision/zones`: `{revision, config: {zones, tolerance}}`.

Il worker produce `[id,class,zone,null,null]`: senza calibrazione metrica non
invia pixel nei campi millimetrici. Confidenza e bounding box restano su Linux;
non aggiunge campi al payload STM32. Più di 8 tracce, ID assenti/duplicati o
snapshot incompleto danno `valid=false`, con evidenza positiva di occupazione
conservata e senza dichiarazioni `clear`. Fine video e guasti danno
`time_ms=null`, stati `unknown`, nessuna traccia. L'adapter ricalcola l'età e
scambia l'ultima osservazione a 5 Hz; senza nuova immagine comunica indisponibilità.
ROI visibili e inquadratura corretta sono prerequisiti: l'occlusione della camera
non è rilevata automaticamente da questo MVP.

Con video attivo, `/api/observations` e l'avvio della prova sintetica sono
rifiutati: non devono coesistere due produttori di osservazioni. In Hardware
occupazione e attese vengono dalle detection fresche; le uscite semaforiche
vengono esclusivamente dalla MCU. Conteggi di attraversamenti completati,
velocità e attese medie restano indisponibili finché non implementati.

## Pacchetto UNO Q

```sh
python3 scripts/package_rt.py .local/crosssense-video --video /percorso/video.mp4 --model models/yolo26n.pt --controller-cycle --loop-video --zip
```

Includere eventualmente `--zones-file dashboard/.local/vision-zones.json` per
trasferire le ROI modificate. Il pacchetto comprende sorgenti, video, modello
e `python/requirements.txt` con le versioni CPU per ARM di `vision/requirements-unoq.txt`. `--controller-cycle` abilita il ciclo logico STM32
esistente senza avviare il generatore sintetico; nessun GPIO configurato.
Il firmware protetto rimane il default senza questa opzione. `--standard-cycle`
con video viene rifiutato. Dipendenze/modello devono essere preparati sulla
scheda prima dell'uso offline.

Sulla UNO Q il modello consegnato viene esportato in NCNN FP32 per ridurre
il tempo di inferenza. La conversione mantiene i pesi e avviene prima del
deployment, senza download di modelli durante l'esecuzione:

```sh
.venv/bin/python -c 'from ultralytics import YOLO; YOLO("models/yolo26n.pt").export(format="ncnn", imgsz=352, device="cpu")'
python3 scripts/package_rt.py .local/crosssense-video-ncnn --video-dir simulation/output --model models/yolo26n_ncnn_model --controller-cycle --loop-video --zip
```

La dimensione di export deve corrispondere a quella di inferenza; riesportare
se si cambia `--imgsz`. L'entry point UNO Q usa OpenCV headless già presente
nell'immagine App Lab, evitando il requisito libGL del wheel GUI installato
come dipendenza transitiva di Ultralytics. NCNN è incluso nei requirements
ARM. La libreria RouterBridge locale dichiarata dal profilo dello sketch usa
buffer RPC da 1024 byte e stack worker da 4096 byte per i payload Bridge v1.

## Verifica

```sh
python3 -m unittest discover -s vision/tests -p 'test_*.py'
python3 -m unittest discover -s dashboard/tests -p 'test_*.py'
node dashboard/tests/app.test.cjs
node dashboard/tests/providers.test.cjs
# ArduinoJson 7.4.3 deve essere già disponibile in una cartella locale:
.venv/bin/python scripts/check_video.py --video /percorso/prova.mp4 --arduino-json /percorso/include
```

Verificati sul Mac Intel: Ultralytics 8.4.175, ByteTrack, YOLO26n della consegna,
video MP4 di prova ottenuto dall'immagine di riferimento, box/classe/confidenza,
editor web e cambio revisione. `scripts/check_video.py` compila lo sketch reale
sul Mac, sostituendo il trasporto Bridge: verifica accettazione delle
osservazioni, cambio stream delle ROI, indisponibilità a EOF e assenza di verdi
conflittuali. Il test è passato sia con frame validi sia con overflow di tracce. I vincoli NumPy/OpenCV per Intel macOS evitano
l'incompatibilità di PyTorch 2.2 con NumPy 2. Il catalogo di replay contiene
i cinque MP4 aggiunti in `simulation/output`.
Documentazione dell'API tracking: [Ultralytics](https://docs.ultralytics.com/modes/track/).

## Configurazione UNO Q aggiornata: video 480, detection 320

Il deployment `crosssense-yolo-360` mantiene il nome storico, ma usa
`frame_size=480`, `imgsz=320` e `inference_threads=2` in `vision-source.json`.
Per i replay 2528×1696 il frame e il JPEG annotato sono 480×322. YOLO lavora
su 320×320 e riporta le coordinate delle box al frame video; box e label
vengono disegnati a 480×322. Gli FPS mostrati accanto all’inferenza sono la
media dei frame completati negli ultimi 30 campioni, includendo decodifica,
inferenza, tracking e JPEG. A sorgente non fresca vengono mostrati come `—`.

Il modello NCNN va esportato a 320, perché contiene reshape legati alla
risoluzione. Conservare l’export 352 se si vuole tornare alla configurazione
precedente. Per replicare il deployment con il nuovo modello:

```sh
python3 scripts/package_rt.py .local/crosssense-480-320 --video-dir .local/performance/videos-480 --model models/yolo26n_320_ncnn_model --controller-cycle --loop-video --frame-size 480 --imgsz 320 --inference-threads 2 --zip
```

Le copie dei cinque MP4 sono ridotte a 480×322 (H.264 CRF 18), così la scheda
non deve decodificare 2528×1696 a ogni frame. Gli originali restano in
`simulation/output` e nel backup `.local/backup-480-320/videos-original`
dell’app sulla scheda. Le ROI normalizzate e la scelta del video sono conservate.
NCNN carica i pesi con due thread; PyTorch, OpenCV e BLAS usano un thread
per evitare concorrenza eccessiva con Bridge e HTTP.

L’adapter interroga la MCU con duplicati identici fra due immagini, senza
rinnovarne la validità; EOF e guasti restano invalidanti. Il limite RPC di
250 ms e il watchdog di 1000 ms restano attivi. `/api/rt` espone `rpc_ms`
e `sent_age_ms` per distinguere ritardi RPC da osservazioni vecchie.

La dashboard interroga le osservazioni ogni 200 ms, separatamente dal
caricamento asincrono dei JPEG. Un JPEG non più presente nella cache viene
ritentato senza azzerare lo stato YOLO. La soglia di freschezza della visione
resta 750 ms; un’immagine lenta non blocca il polling delle osservazioni.
Test di regressione frontend: `node dashboard/tests/vision.test.cjs`.

La preview scarica ogni JPEG una sola volta e lo visualizza tramite un Blob
URL locale, evitando una seconda richiesta `no-store` dopo il precaricamento.
Gli URL sostituiti vengono rilasciati. Un errore temporaneo nel polling
conserva l’ultimo snapshot fino alla normale scadenza dei 750 ms; non rinnova
la sua età e non modifica lo stato ricevuto dalla MCU.
