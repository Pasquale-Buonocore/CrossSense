# Preparazione dello ZIP per Arduino App Lab

Il pacchetto della demo usa due riduzioni distinte:

1. Gli MP4 vengono **ricodificati prima del packaging** con lato massimo di 480 pixel. I video panoramici 716×480 diventano circa 480×322, senza deformazione. FPS, numero di frame e durata vengono conservati.
2. Nel file `python/vision-source.json` viene impostato anche `frame_size: 480`. Questo impedisce al runtime di elaborare accidentalmente frame più grandi se gli asset vengono sostituiti.

La ricodifica fisica evita che la UNO Q debba decodificare un MP4 716×480 e ridimensionare ogni frame durante `RUN`. L'ingresso del detector rimane separato: `imgsz: 320` indica l'immagine 320×320 fornita a YOLO.

## Comando consigliato

Dalla radice del repository:

```powershell
python scripts\build_applab_zip.py
```

Lo script:

- legge gli MP4 originali da `.local/demo-video-source-20261011`;
- trova automaticamente l'ambiente `.local/replay-venv` con OpenCV;
- crea copie temporanee con lato massimo 480;
- include l'export NCNN nativo 320×320 da `.local/export-320/yolo26n_ncnn_model`, zone, dashboard e sketch STM32;
- abilita `--controller-cycle`; il replay non parte e non riparte automaticamente;
- genera in `dist/` uno ZIP con timestamp;
- verifica CRC, struttura App Lab e SHA-256 di tutti gli asset.

## Avvio manuale del replay

L'app non seleziona e non avvia automaticamente alcun video. Dopo `RUN`, il controller rimane in stato protetto e la dashboard mostra il frame di riferimento. Per iniziare:

1. scegliere un file dal menu **Video simulazione**;
2. premere **Play**;
3. usare **Pausa** per sospendere l'elaborazione;
4. usare **Stop / Riavvolgi** per fermare il replay e riportarlo all'inizio.

La sola selezione non avvia l'elaborazione del video e non produce osservazioni. Dopo una pausa, **Play** riprende il file; dopo Stop o fine video, **Play** riparte dall'inizio. A ogni nuovo avvio dell'app è necessaria una scelta esplicita. Il loop a fine file è disabilitato per default.

Subito dopo `RUN`, il modello viene preparato in background senza avviare alcun replay. Questa fase importa Ultralytics/NCNN, carica i pesi in memoria, crea il predictor e ByteTrack, configura i thread NCNN e svolge un warm-up su un'immagine vuota. La dashboard mostra lo stato e il tempo effettivo di preparazione; Play resta disabilitato finché il modello non è pronto. Il modello rimane poi in memoria per tutti i replay della stessa esecuzione.

Il nome e l'hash dello ZIP vengono stampati al termine. La cartella temporanea dei video ridimensionati viene rimossa automaticamente; nello ZIP restano le copie già ridimensionate.

## Opzioni utili

```powershell
python scripts\build_applab_zip.py --help
```

Esempio con nome esplicito e un solo thread NCNN:

```powershell
python scripts\build_applab_zip.py `
  --output dist\crosssense-app-lab.zip `
  --inference-threads 1
```

Le opzioni principali sono:

- `--source`: cartella degli MP4 originali;
- `--model`: modello NCNN; la risoluzione dichiarata in `metadata.yaml` deve coincidere con `--imgsz`;
- `--zones-file`: configurazione iniziale delle ROI;
- `--output`: percorso dello ZIP finale;
- `--max-size`: lato massimo degli MP4 e valore di `frame_size`, default 480;
- `--imgsz`: ingresso YOLO, default 320;
- `--confidence`: confidenza minima, default 0,15;
- `--inference-threads`: thread NCNN, default 2;
- `--loop-video`: abilita esplicitamente la ripetizione automatica a fine replay.

Se l'output indicato esiste già, lo script si ferma senza sovrascriverlo. Usare un nome diverso.
