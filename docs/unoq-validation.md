# Collaudo e stato della demo UNO Q — 480/320

Sessione 10–11 ottobre 2026. **Il percorso replay → YOLO → Bridge → MCU → dashboard funziona sulla UNO Q. Il conteggio completo degli attraversamenti non supera ancora il collaudo a 320.** La demo del controllo logico è utilizzabile; una demo che promette i conteggi esatti dei cinque video non è pronta.

## Perimetro, ambiente e deployment

Replay dichiarato, cinque MP4 locali, tutto mostrato nella dashboard, nessun GPIO applicativo per LED/buzzer/attuatori. I video non reagiscono al semaforo: gli allarmi mostrano anche gli ingressi durante il verde veicolare. Nessuna camera live o inferenza cloud. Il browser è esterno; Linux esegue backend e visione, STM32 esegue il controller C++.

Scheda raggiunta via SSH a `192.168.1.196`, hostname `CrossSense`, Linux aarch64 `6.16.7-g0dd6551ae96b`, 3,6 GiB RAM. App precedente `crosssense-yolo-360` conservata e arrestata. App separata installata e lasciata attiva: `/home/arduino/ArduinoApps/crosssense-replay-dashboard`; dashboard `http://192.168.1.196:8080`.

- Video entro **480×480**: cinque asset 480×322, 30 FPS, 360/390/300/510/420 frame. Originali conservati; tutti i 1980 frame presenti negli asset ridotti.
- Inferenza entro **320×320**, YOLO26n NCNN locale esportato a 320, due thread, confidenza 0,15. Stessi pesi ufficiali della prova host; dettagli in [replay-assets.md](replay-assets.md).
- App Lab `python-apps-base:0.12.0`, Python 3.13.14, torch 2.8.0, torchvision 0.23, Ultralytics 8.4.175, NCNN 1.0.20260526, lap 0.5.13, OpenCV headless 4.13.
- `arduino-app-cli app start` ha compilato e caricato lo sketch Zephyr: 113604 byte di programma, 47660 byte di globali. È stato ricaricato anche il binario compilato per verificare il recupero del Bridge.
- Il pacchetto finale usa `loop=true`; il confronto dei conteggi è stato eseguito con `loop=false` per osservare separatamente EOF e fine di ciascun video. Il loop finale è stato collaudato a parte.

Architettura corrente, clock, API e protocollo in [architecture.md](architecture.md). I risultati host 960/640 in [validation.md](validation.md) sono storici e non provano l'accuratezza attuale.

## Risultati dei cinque replay sulla scheda

Due esecuzioni complete a 480/320 hanno entrambe contato **2/0/1/1/0**, contro **4/0/1/3/0**. `simulation/expected-events.json` resta invariato. Il test è terminato con errore sulle asserzioni dei video 1 e 4; non si dichiara che tutti i test siano passati.

| Video | Attesi SX→DX / DX→SX | Osservati SX→DX / DX→SX | Inferenza mediana / p95 | RPC p95 / massimo | FPS mediani pipeline |
|---|---:|---:|---:|---:|---:|
| `output_1.mp4` | 2 / 2 | **1 / 1** | 174,0 / 193,0 ms | 196,3 / 208,2 ms | 5,2 |
| `output_2.mp4` | 0 / 0 | 0 / 0 | 170,1 / 185,8 ms | 189,2 / 198,5 ms | 5,4 |
| `output_3.mp4` | 1 / 0 | 1 / 0 | 163,4 / 173,8 ms | 178,4 / 190,3 ms | 5,6 |
| `output_4.mp4` | 2 / 1 | **0 / 1** | 175,3 / 195,8 ms | 195,4 / 202,1 ms | 5,2 |
| `output_5.mp4` | 0 / 0 | 0 / 0 | 179,1 / 190,7 ms | 196,5 / 204,0 ms | 5,2 |

Questi sono campioni HTTP di frame/uptime distinti, non ogni inferenza/RPC. Il p95 dell'età inviata è 354–391 ms; limite RPC 250 ms e watchdog 1000 ms rimangono invariati. Nessuna disconnessione o errore di trasporto nei campioni dei cinque replay; nessun campione con entrambi i verdi. Il campionamento non esclude transitori non osservati. I 30 FPS sono il tempo del file: il replay elaborato rallenta a circa 5–6 FPS.

Gli episodi `INVALID_DATA` dovuti a tracking incompleto producono arresto protetto. Non si maschera una detection senza ID come osservazione sicuramente libera. Le correzioni applicate separano validità RT e traiettorie pedonali, conservano recenti ID ByteTrack entro un gate limitato e applicano la confidenza del file di configurazione. Una verifica diagnostica host di soglie detector/ByteTrack più basse non ha recuperato tutti i transiti e non è stata adottata.

**Confermato:** le traiettorie complete richieste dall'algoritmo mancano nei risultati correnti. **Inferenza ragionevole:** piccole box, occlusioni e cambi ID a bassa risoluzione contribuiscono alle perdite. **Non misurato:** precision/recall per box, accuratezza generale su persone reali e percentuale di errore fuori da questi cinque video. Nessuna modifica dei contatori per farli coincidere con il copione del replay.

Un campione `docker stats` durante replay riportava 182,43% CPU e 300,1 MiB; temperature lette 48,2–54,5 °C. Sono istantanee, non massimi certificati. Il precedente tentativo 960/640 sulla scheda era troppo lento per la deadline ed è stato interrotto; non è un'opzione del deployment corrente.

## Test superati e problemi corretti

| Verifica | Esito / evidenza |
|---|---|
| `scripts/check_all.py` finale | `ALL_CHECKS_OK`: 59 test Python individuati, 58 superati, 1 symlink saltato per privilegi Windows; quattro suite JavaScript; sei configurazioni C++ compilate con warning trattati come errori |
| `scripts/check_mcu.py` sulla MCU reale | 12 verifiche, 201 risposte: recupero iniziale, richieste, sgombero occupato oltre 10 s, priorità senza rilascio su occupazione, verde accessibile 8 s, conflitto, duplicato senza rinnovo watchdog, frame scaduto, clear incoerente, dato invalido, nuovo stream |
| Contratti HTTP | Sette verifiche superate: path esterno, produttore esterno escluso, POST cross-origin, revisione ROI e conflitto/readback, retry, deduplicazione, annullamento al cambio sorgente |
| Richieste sul backend finale | Accessibile servita in 9,83 s, priorità in 10,11 s, pedonale in 8,17 s; alla verifica accessibile restavano 7855 ms di verde |
| Browser Edge via IP / HTTP | JPEG, stato Bridge, selezione video, richiesta accessibile servita, export JSON reale; interruzione API simulata nel browser → stato disconnesso e comandi disabilitati → recupero; nessuna eccezione JS nell'esecuzione finale |
| Resilienza app / MCU | Worker SDK congelato → timeout/restart e recupero; pausa Linux → `FAULT` / `TIMEOUT` ed entrambi rossi letti direttamente dalla MCU con una RPC malformata che non sostituisce le osservazioni → recupero; video corrotto → errore esplicito e recovery; processo Linux riavviato; firmware ricaricato e Bridge riconnesso |
| Avvio app senza Internet | Container con `--network none`, unica interfaccia `lo`, `UV_OFFLINE=1`, modello/dipendenze già installati: visione fresca e Bridge valido in 21,02 s; avvio reale attraverso `/run.sh`, nessuna installazione necessaria |
| Loop del pacchetto finale | `UNOQ_LOOP_OK`: rollover osservato dopo 70 s, ripresa al frame 1 con nuovo stream visione e MCU, nessun doppio verde nei campioni |
| Integrità | ZIP, hash degli asset, configurazione 480/320/0,15, metadata modello 320, sorgenti distribuiti e AST Python controllati; nessuna cache Python nel pacchetto |

Il collaudo ha trovato e corretto tre problemi pratici del percorso dashboard:

1. `dashboard/rt.py`: clic durante RPC/reset rifiutati. Ora restano in coda; l'ACK consuma solo i comandi inclusi nel messaggio, mantenendo un frame con livelli false tra due fronti. Test di concorrenza aggiunto.
2. `dashboard/static/app.js`: `crypto.randomUUID()` assente su HTTP via IP. Fallback con `getRandomValues`, verificato in browser e test JavaScript.
3. `dashboard/static/vision.js`: osservazioni del video precedente visibili durante la selezione. Ora vengono invalidate subito; comandi bloccati durante cambio sorgente/salvataggio ROI. La prova browser attende la conferma della selezione.

## Gap e piano di completamento

| Requisito | Stato corrente | Priorità e lavoro restante | Criterio di accettazione |
|---|---|---|---|
| Replay → inferenza → MCU → dashboard | Implementato e collaudato | P1: prova generale sulla rete della presentazione | Stato MCU, JPEG e richieste senza interventi manuali di recupero |
| Limiti video/inferenza 480/320 | Implementati nel profilo distribuito | P0: conservarli negli esperimenti | Ogni lato video ≤480, inferenza/export ≤320 |
| Conteggi/direzioni dei cinque replay | **Parziale; test fallito** | **P0, medio/grande:** annotare perdite, migliorare detector/tracking a 320 | 4/0/1/3/0 e direzioni originali, nessun conteggio inventato né duplicato |
| Occupazione, conflitti e protezione | Implementati e collaudati funzionalmente | P1: ampliare casi di falsi negativi/occlusione | Nessun rilascio su occupazione osservata; non interpretare guasto come clear |
| Richieste manuali e accessibilità | Implementate, fix LAN/concorrenza collaudati | P1: includere la sequenza nella prova generale | Queued → served o cancelled con motivo, nessun comando perso durante RPC |
| Runtime offline già preparato | Collaudato | P1, piccolo: documentare provisioning e startup al boot | Stesso esito dopo installazione replicata e riavvio OS completo |
| Statistiche metriche / TTC / coda veicoli | Mancanti nella proposta originale, fuori dal demo minimo attuale | P2, grande: calibrazione/dati/validazione | Unità fisiche verificate e qualità misurata prima di mostrarle |
| Camera / LED / buzzer / oggetti fisici | Esclusi per decisione dell'utente | Nessuno | Solo dashboard nel percorso attivo |

Le cinque attività più utili da iniziare, in ordine:

1. **Annotare i quattro transiti persi** nei video 1 e 4, con frame, box, classe e cambio ID. File: nuovi dati di validazione, `vision/pipeline.py`, `identity.py`. P0, sforzo medio; prerequisito per una correzione motivata.
2. **Confrontare un detector/tracker adatto ai soggetti piccoli a 320**, conservando esempi separati per validazione. P0, medio/grande; dipende dalle annotazioni. Accettazione: conteggi/direzioni originali su tutti i video e nessun nuovo falso transito.
3. **Ripetere prestazioni e deadline sulla UNO Q dopo ogni cambio del modello**, prima di distribuirlo. P0, medio; dipende dal candidato. Accettazione: 480/320, RPC nel budget e osservazioni fresche sotto carico del browser.
4. **Provare riavvio OS/power cycle e predisporre l'avvio riproducibile** se richiesto dalla presentazione. P1, piccolo/medio. Avvio manuale App Lab già funziona; autostart al boot non configurato nel repository.
5. **Eseguire una prova generale registrata con export** e comunicare il limite dei conteggi se ancora presente. P1, piccolo; dipende dall'esito P0. Nessuna promessa di accuratezza che i test non confermano.

Non servono nuovi microservizi o una riscrittura della FSM. Il blocco attuale riguarda la qualità delle traiettorie a 320, non il collegamento Linux–MCU.

## Evidenze, riproduzione e limiti delle prove

Risultati salvati nel repository in [validation-results/](validation-results/): `unoq-replays-final-320.json` conserva le asserzioni fallite, `unoq-api-final.json`, `unoq-requests-final.json`, `mcu-board-summary.json`, `resilience.json`, `resilience-final.json` (lettura diretta TIMEOUT), `offline.json`, `unoq-loop.json`. Le 201 risposte MCU integrali sono in `.local/mcu-board-check.json`; screenshot/JSON browser in `.local/dashboard-unoq.png` e `.local/dashboard-unoq-export.json`. Non sono salvate credenziali negli artefatti.

Per i conteggi a fine file usare una app di collaudo con `vision-source.json` impostato a `loop=false`, poi riavviare il container. `scripts/check_unoq.py` cambia sorgente e invia richieste: nessun altro tester deve cambiare il video durante la prova. Per il pacchetto finale con loop usare `check_unoq_loop.py` oppure `check_unoq.py --requests-only`. `check_unoq_api.py` cambia ROI con gli stessi poligoni e incrementa la revisione. Gli script di resilienza/offline si eseguono sulla scheda e interrompono il solo container di test. `check_mcu.py` richiede che la pipeline principale sia arrestata; non avere due produttori attivi.

Pacchetto finale: **`dist/crosssense-unoq-480-320.zip`**, 25550853 byte, SHA256 **`839c2aa74e45dfccfd21481e827590c070bbf6c50898e190da9d9360b47391d1`**. Conservato anche in `/home/arduino/` sulla scheda. I pacchetti precedenti restano intermedi/storici. `dist/`, modelli e virtualenv sono esclusi da Git; il README contiene il comando per rigenerare la distribuzione.

Non eseguiti: riavvio dell'intero Linux OS, power cycle, endurance lunga, confronto fra browser diversi, accuratezza su scene reali annotate, misure di precision/recall, TTC e velocità fisiche. Il riavvio del processo Linux e il ricaricamento MCU sono stati eseguiti separatamente. Offline significa app già preparata senza Internet, non prima installazione senza cache. Gli attuatori fisici non sono parte della demo.

Restano due decisioni che cambierebbero il piano: se il demo debba mostrare **conteggi esatti** o possa dichiarare conteggi degli attraversamenti osservati; se velocità/TTC/coda della proposta iniziale siano richiesti oltre al controllo per ROI. Nel profilo attivo non viene calcolata una velocità delle persone in m/s: `IdentityTracker.update` stima moto normalizzato per associare gli ID, mentre `estimates` MCU resta vuoto.
