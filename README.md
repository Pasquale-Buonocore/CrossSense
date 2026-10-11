# CrossSense — replay e telecamera su Arduino UNO Q

CrossSense elabora **replay MP4 dichiarati** e offre una sorgente **Telecamera CAM0** avviabile manualmente. Entrambe usano YOLO, ByteTrack, ROI, Bridge e lo stesso controller STM32. Replay è la modalità iniziale. I semafori sono indicatori logici nella dashboard: nessun LED, buzzer o attuatore fisico è comandato. Gli attori dei replay non reagiscono ai semafori calcolati.

## Demo in tre minuti

La strada più breve per un valutatore con Arduino UNO Q è:

1. generare il pacchetto con `python scripts/build_applab_zip.py`;
2. importare lo ZIP prodotto in `dist/` da **Arduino App Lab → My Apps → Import**;
3. premere **RUN** e aprire la dashboard sulla porta **8080**;
4. scegliere uno dei due replay e premere **Play**;
5. osservare rilevamenti, ROI, richiesta pedonale automatica, fasi STM32 e metriche;
6. provare **Pausa**, **Stop / Riavvolgi**, le richieste manuali e la modifica delle zone.

Nessun video parte automaticamente. Dopo RUN, YOLO viene caricato e riscaldato in background mentre il frame invita a scegliere un video; il tempo effettivo di preparazione viene mostrato nella dashboard. Senza osservazioni fresche il controller porta i segnali logici nello stato protetto. La guida mostrata dentro App Lab è il `firmware/README.md`; la procedura completa di packaging è in [Preparazione dello ZIP per Arduino App Lab](docs/app-lab-package.md).

Per provare CAM0, scegliere **Telecamera** e premere **Avvia telecamera**. Non viene salvato alcun MP4. La cattura conserva solo il frame più recente, fino a 5 Hz, e scarta quelli intermedi se l'inferenza è più lenta. Le ROI della camera sono indipendenti da quelle dei replay: finché non vengono salvate sul frame live, le osservazioni inviate alla STM32 restano invalide e il controller rimane protetto. La cattura nella app containerizzata e le prestazioni reali richiedono ancora una verifica sulla scheda.

## Cosa valutare

| Area | Evidenza nella demo |
|---|---|
| Visione locale | YOLO26n NCNN e ByteTrack sui replay inclusi, senza download a runtime |
| Interpretazione della scena | ROI di attesa, attraversamento e approccio veicolare configurabili |
| Controllo embedded | Macchina a stati C++ sulla STM32, alimentata via RouterBridge |
| Protezione | Tutto rosso su dati assenti/obsoleti, conflitto o timeout di sgombero |
| Interazione | Play/Pausa/Stop, richieste pedonali, accessibilità e priorità simulata |
| Osservabilità | Fasi, tempi, rilevamenti, metriche, allarmi, errori Bridge ed export JSON |

Il percorso è `replay o CAM0 → AI → Bridge → MCU → dashboard`. Il replay usa il tempo del file per le statistiche; la camera usa il tempo reale di cattura. Il watchdog MCU usa sempre tempo reale.

## Perimetro e limiti dichiarati

- I replay sono preregistrati e i loro attori non reagiscono ai semafori calcolati.
- I segnali sono logici e visibili nella dashboard; non vengono comandati GPIO o impianti reali.
- Non sono disponibili calibrazione metrica, velocità fisiche, TTC o certificazione di sicurezza.
- Il controller e la dashboard sono stati collaudati sulla UNO Q; l'accuratezza dei conteggi a 320 non supera tutte le asserzioni dei replay noti.
- Modello e video di distribuzione non sono versionati nel repository: il processo di preparazione ne controlla formato e coerenza.

## Percorso applicativo

`MP4 o CAM0 → YOLO26n / ByteTrack → ROI → crosssense_update → controller C++ → dashboard`

Sulla UNO Q la visione e il server HTTP girano su Linux; il controller logico gira sulla STM32. Per sviluppo e prove senza scheda si compila **lo stesso sketch** per PC e lo si collega al backend con `--native-controller`.

Funzioni:

- Replay locale, selezione video, preview annotata e ROI modificabili/persistenti.
- Richiesta automatica dopo 800 ms di attesa nelle ROI; conferma per gruppo, senza ripetere continuamente lo stesso impulso. Il gruppo si riarma dopo 1 s senza utenti in attesa.
- Ciclo logico MCU, verde veicolare minimo 5 s con veicoli presenti / 1 s con avvicinamento libero, giallo e tutto rosso.
- Protezione con attraversamento occupato, conflitto, timeout osservazioni e timeout di sgombero.
- Richieste manuali, tempo accessibile di 8 s e priorità veicolare simulata limitata a 5 s. Nessuna uscita fisica.
- Attraversamenti completati per direzione, attesa osservata prima dell’ingresso e immobilità nel replay.
- Allarmi, fasi, stato richieste, errori del collegamento e esportazione JSON nella dashboard.

I conteggi richiedono la sequenza osservata dello stesso ID `strisce → attesa sx oppure dx`, confermata nella stessa area di uscita per 150 ms di video, una sola volta per ID e replay. È sufficiente comparire sulle strisce; non serve osservare l’attesa iniziale. La direzione deriva dal lato di uscita: destra → sx→dx, sinistra → dx→sx. Anche un ritorno al lato di partenza conta secondo questa definizione di uscita, senza certificare il transito completo da un marciapiede all’altro. Chi proviene dalle strisce non viene conteggiato in attesa; una sparizione da sola non completa un attraversamento. Le statistiche usano il tempo del video; il controller e il watchdog usano tempo reale. Il replay può rallentare: non si stimano velocità metriche o TTC.

## Avvio locale

Python 3.11+, dipendenze in `vision/requirements.txt`; modello `models/yolo26n.pt` preparato prima dell’uso offline. I pesi non sono versionati. Vedere [asset e riproducibilità](docs/replay-assets.md).

Solo server e dashboard, senza sorgente configurata:

```sh
python dashboard/server.py
```

Replay completo con controller nativo (G++ e ArduinoJson 7.4.3 disponibili):

```sh
python scripts/build_native.py --arduino-json /percorso/ArduinoJson --output .local/replay-controller
python dashboard/server.py --native-controller .local/replay-controller --video-dir .local/replays-480 --model models/yolo26n.pt --frame-size 480 --imgsz 320 --confidence 0.15 --inference-threads 2
```

Su Windows usare `.local/replay-controller.exe`. Aprire `http://127.0.0.1:8080`. La dashboard identifica il controller nativo. Il catalogo non seleziona né avvia implicitamente un replay: scegliere un video e premere Play. Un modello mancante viene mostrato come errore senza abbattere il server. Per abilitare CAM0 su Linux aggiungere `--camera`; l'acquisizione parte soltanto dal pulsante nella dashboard.

## App Lab / UNO Q

Per creare con un solo comando uno ZIP App Lab verificato, con i due MP4 fisicamente ridimensionati entro 480 pixel e `frame_size=480`:

```sh
python scripts/build_applab_zip.py
```

La procedura, la distinzione tra risoluzione degli MP4 e input YOLO e tutte le opzioni sono descritte in [Preparazione dello ZIP per Arduino App Lab](docs/app-lab-package.md).

```sh
python scripts/prepare_replays.py --source simulation/output --destination .local/replays-480 --max-size 480
python scripts/package_rt.py dist/crosssense-unoq-480-320 --video-dir .local/replays-480 --model /percorso/yolo26n_320_ncnn_model --controller-cycle --frame-size 480 --imgsz 320 --confidence 0.15 --inference-threads 2 --zip
```

Importare lo ZIP in App Lab e avviare l’app. Nessun replay parte automaticamente: scegliere un video nella dashboard e premere **Play**; sono disponibili anche **Pausa** e **Stop / Riavvolgi**. Il pacchetto contiene `app.yaml`, `python/main.py`, dashboard, visione, video, modello e sketch. Il profilo corrente, concordato per la UNO Q, è video entro **480×480** (480×322 per questi replay), inferenza **320×320**, export NCNN nativo a 320, due thread e confidenza 0,15. Gli asset ridotti preservano tutti i frame e gli FPS del file; la riproduzione elaborata può rallentare. Non mescolare export e risoluzioni diverse: il generatore ora rifiuta automaticamente un modello NCNN incompatibile. Il profilo firmware include la copia RouterBridge con buffer 1024 byte. Tutti i manifest usano `bricks: []`.

Il profilo 960/640 verificato in precedenza sul PC è storico. A 320 il collaudo sulla scheda ha contato 2/0/1/1/0 invece di 4/0/1/3/0: consultare i risultati effettivi del [collaudo UNO Q](docs/unoq-validation.md), senza attribuire al profilo attuale i conteggi del precedente. Il controllo e la dashboard sono collaudati; le asserzioni di accuratezza non sono tutte superate. Lo ZIP corrente va sempre rigenerato con `build_applab_zip.py`, perché `dist/` è esclusa da Git.

Aggiornamento dell'11 ottobre: i due video della demo (`fotoRealVideo.mp4` e `postProcessingVideo.mp4`) sono disponibili a **716×480**, ma il profilo App Lab corrente usa il default `frame_size=480`. La pipeline conserva le proporzioni e li elabora quindi a circa **480×322**; il modello resta NCNN FP32 a 320. Il precedente pacchetto sperimentale con `frame_size=716` non è il default perché aumenta il carico sulla UNO Q. FP16 e il candidato INT8 non hanno dato un'accelerazione utile, e INT8 ha peggiorato i conteggi host. Misure e limiti sono documentati in [quantizzazione e video 480p](docs/quantization.md).

Il manifest alla radice è solo descrittivo: usare il pacchetto generato. La porta dell’app è 8080. Installazioni, build e download iniziali vanno eseguiti prima della prova senza Internet. Il runtime della visione disabilita rete e installazioni automatiche Ultralytics.

`--standard-cycle` produce invece una prova sintetica separata di due cicli. Senza opzioni ciclo il pacchetto firmware rimane protetto. Le app in `apps/` sono diagnostiche storiche, non componenti della demo finale; avviarle sostituisce lo sketch sulla scheda.

## Verifica

```sh
python scripts/check_all.py --arduino-json /percorso/ArduinoJson --node /percorso/node
python scripts/check_standard_cycle.py --arduino-json /percorso/ArduinoJson
python scripts/check_replays.py --controller .local/replay-controller --model /percorso/yolo26n_320_ncnn_model --video-dir .local/replays-480 --assert-counts --output .local/replay-validation.json
python scripts/check_unoq.py --url http://192.168.1.196:8080 --output .local/unoq-validation.json
```

`check_all.py`, `check_standard_cycle.py` e `check_replays.py` usano processi host. `check_unoq.py` seleziona video e invia richieste alla app sulla scheda: eseguirlo senza altri produttori che cambino la sorgente. Le asserzioni dei conteggi restano quelle delle traiettorie note, anche quando il detector a 320 le perde: un fallimento va riportato, non sostituito con un valore inferiore.

Il pacchetto demo corrente ha loop disabilitato: a fine file il replay si ferma. Per collaudare esplicitamente il rollover, generare un pacchetto separato con `build_applab_zip.py --loop-video` e usare `scripts/check_unoq_loop.py`. Procedure e risultati delle interruzioni controllate e del runtime offline sono nel documento di collaudo.

## Mappa del repository

| Percorso | Contenuto |
|---|---|
| `vision/` | Pipeline YOLO/ByteTrack, identità, ROI e metriche replay |
| `dashboard/` | Server HTTP, adapter Bridge e interfaccia web |
| `firmware/` | App Lab di base, sketch STM32 e macchina a stati C++ |
| `protocol/` | Contratto JSON Bridge v1 tra Linux e STM32 |
| `scripts/` | Packaging, verifiche host e collaudi UNO Q |
| `simulation/` | Generazione scenari e replay dichiarati |
| `docs/` | Architettura, validazione, prestazioni e decisioni tecniche |
| `apps/` | App diagnostiche storiche, non parte della demo finale |

## Documenti

- [Architettura software](docs/architecture.md): componenti, startup, dati, concorrenza, errori e decisioni.
- [Protocollo Bridge v1](protocol/bridge-v1.md): `crosssense_update`.
- [Asset e riproducibilità](docs/replay-assets.md).
- [Validazione e stato](docs/validation.md).
- [Collaudo UNO Q e profilo 480/320](docs/unoq-validation.md).

`docs/environment.md`, `docs/technical-review.md`, `docs/team-plan.md` e `firmware/docs/history.md` registrano il percorso precedente: i riferimenti a camera, GPIO, PDF e calibrazione non definiscono il perimetro attuale.
