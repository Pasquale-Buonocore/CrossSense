> Documento storico. Il perimetro corrente è replay dichiarato e segnali soltanto nella dashboard. Riferimenti aggiornati: README principale e docs/architecture.md. Le affermazioni di verifica sotto riportate appartengono alle prove precedenti.

# Prova del ciclo standard — API dashboard e STM32

La prova aggiorna i **tre semafori della dashboard**, senza pilotare GPIO o LED
fisici della UNO Q. Usa l'API rilasciata in `dashboard/`, senza modificare gli endpoint.
Python produce osservazioni **sintetiche** a 10 Hz e una richiesta pedonale;
`RTService` è l'unico proprietario del Bridge, a 5 Hz. La macchina a stati e
i tempi sono sulla STM32, nel loop da 10 ms. La dashboard può restare chiusa.

```text
Python Linux → API observations/requests → RTService → Bridge → STM32
STM32 → risposta JSON Bridge v1 → cache RTService → GET /api/rt
HardwareProvider → TrafficSignals → veicoli + pedoni SX + pedoni DX
```

La STM32 restituisce `vehicle_light` e `pedestrian_light`. Linux riceve la
risposta RPC e il browser legge l'API. Non esiste un ulteriore POST per impostare
le luci. I due pedonali condividono lo stesso valore, come previsto da Bridge v1.

## Avvio con Arduino App Lab

Dalla radice del repository, anche in PowerShell:

```sh
python scripts/package_rt.py dist/crosssense-dashboard-cycle-v3 --standard-cycle --zip
```

Importare `dist/crosssense-dashboard-cycle-v3.zip` con **My Apps → Import**, aprire
**CrossSense Dashboard Cycle** e premere **Run**. App Lab compila/carica il
firmware, avvia l'unico servizio dashboard/API/Bridge sulla porta **8080** e lancia automaticamente
due cicli sintetici dopo il bind del server. Il profilo già presente
include core Zephyr 1.0.0, RouterBridge 0.4.3 e ArduinoJson 7.4.3; il primo avvio
può richiedere il download delle dipendenze.

Non occorre lanciare comandi dal PC: la prova usa `http://127.0.0.1:8080`
dentro l'app. Per ripeterla manualmente dopo la conclusione dei cicli automatici,
dalla directory del pacchetto sul lato Linux della UNO Q:

```sh
python python/try_standard_cycle.py --url http://127.0.0.1:8080
```

Il file si trova accanto a `python/main.py`. Non avviare la prova manuale mentre
è in corso quella automatica. Avviare una sola sorgente di osservazioni:
durante questa prova spegnere eventuali produttori visione/replay. I frame
sintetici dichiarano entrambe le ROI libere e sostituiscono le osservazioni
camera. La prova non richiede camera, inferenza o cablaggio esterno.

Prima di avviare questa app, ferma la vecchia app di prova che pubblicava sulla
8081 e il processo dashboard già in ascolto sulla 8080. Il pacchetto aggiornato
esegue i sorgenti di `dashboard/` con Bridge abilitato sulla stessa porta 8080:
pagina, API, telemetria e prova appartengono a un unico servizio. Non avviare
anche una dashboard standalone. Apri `http://192.168.23.19:8080/` per vedere i
colori ricevuti dalla STM32; viene selezionato **Hardware automaticamente**.
Se la 8080 è occupata, l'avvio fallisce prima della prova e non passa a un'altra
porta. I pacchetti precedenti che pubblicavano sulla 8081 sono superati.

Se apri la pagina dopo la conclusione dei due cicli vedrai i semafori rossi.
Premi **Ripeti prova STM32** per rilanciare due cicli mentre guardi gli indicatori.
Durante la prova il pulsante è disabilitato. L'avviso distingue prova in corso,
completata e interrotta; mostra anche il servizio dal quale legge la telemetria.
Le risposte non vengono memorizzate dal browser, così gli aggiornamenti dell'app
non riutilizzano vecchi script. I poll HTTP riusciti non riempiono la console.

Se usi lo script dal PC, `--url` deve contenere l'IP o il nome reale della scheda.
`IP-DELLA-UNO-Q` era un segnaposto. `getaddrinfo failed` significa che l'host
non viene risolto: nessuna richiesta HTTP è arrivata all'API. L'avvio automatico
locale evita questo problema.

## Ciclo e semafori sul frame

| Fase | Semaforo veicoli | Semafori pedoni SX e DX | Durata demo |
| --- | --- | --- | --- |
| `VEHICLE_GREEN` | Verde | Rosso | Minimo 5 s; attende una richiesta |
| `VEHICLE_YELLOW` | Giallo | Rosso | 2 s |
| `ALL_RED_TO_PED` | Rosso | Rosso | 1 s |
| `PED_GREEN` | Rosso | Verde | 5 s |
| `PED_CLEARANCE` | Rosso | Rosso | Minimo 1 s, attende strisce libere stabili |
| `ALL_RED_TO_VEH` | Rosso | Rosso | 1 s, con strisce ancora libere |

Il provider hardware traduce `RED/YELLOW/GREEN` in `red/amber/green`;
`TrafficSignals.render()` aggiorna i tre indicatori. Lo sketch non usa
`pinMode`, `digitalWrite` o pin LED. Tempi centralizzati in `sketch/standard_cycle.h`,
separati dalla configurazione futura del controller completo.

A boot, nuovo stream o recupero dal guasto: tutto rosso, almeno **500 ms di
osservazioni valide con attraversamento libero**, poi **1 s tutto rosso** prima
del verde veicoli. Una richiesta prima dei 5 s resta pendente; viene consumata
all'apertura del verde pedonale. Richieste successive possono avviare un altro
ciclo. Accessible include la richiesta pedonale, ma buzzer, priorità veicolare,
richieste automatiche dalle tracce e stime cinematiche non fanno parte di questa
prova. Buzzer/beacon restano false; gli attuatori esterni non sono configurati.

Lo sgombero mantiene entrambi i rossi se l'attraversamento è occupato; servono
500 ms liberi continui per uscirne. Oltre **10 s**, `PROTECTED_STOP` con
`CLEARANCE_TIMEOUT` resta latched fino a un nuovo stream o riavvio, seguito dal
recupero protetto. Occupazione durante verde/giallo veicoli causa arresto con
`CROSSING_CONFLICT`; rioccupazione nel tutto rosso finale impedisce il rilascio.

Dati invalidi o scaduti causano `FAULT` e rosso nei campi della telemetria.
La dashboard lo mostra con collegamento fresco, altrimenti indica stato
sconosciuto. Il watchdog esistente considera
età immagine + budget trasporto 250 ms + tempo MCU, entro 1000 ms. Il limite
di consegna Bridge resta da verificare sull'hardware.

## Esito dello script

Lo script usa `POST /api/observations`, `POST /api/requests` e `GET /api/rt`.
Le richieste rifiutate durante RPC/reset vengono ritentate con lo stesso ID;
`queued` è solo la conferma della coda Linux. Ogni fase viene verificata dalle
uscite comandate e dalla telemetria MCU, senza dedurre la fase dai timer Python.

```text
SYNTHETIC: ROI libere simulate, nessuna camera. Controllo fasi sulla STM32.
PHASE VEHICLE_GREEN vehicle=GREEN pedestrian=RED remaining_ms=None
REQUEST_QUEUED id=... (in attesa del verde pedonale MCU)
PHASE VEHICLE_YELLOW vehicle=YELLOW pedestrian=RED remaining_ms=...
...
CYCLE_OK 1/2
...
CYCLE_OK 2/2
STOP_OK fault=INVALID_DATA vehicle=RED pedestrian=RED
```

Dopo l'ultimo ciclo smette di inviare osservazioni e richiede conferma di `FAULT`
con entrambi i rossi entro 3 s. L'adapter può segnalare `INVALID_DATA` prima che
scada il watchdog; `TIMEOUT` è accettato. In uscita, anche con Ctrl+C, prova a
pubblicare un frame invalido. Codice di uscita 0 solo dopo cicli e arresto
confermati; errori, fasi saltate, guasti/allarmi o luci incoerenti producono
`CYCLE_ERROR` e codice 1. `--timeout` imposta il limite totale dei cicli.

## Verifica sul PC

```sh
python -m unittest discover -s scripts/tests -p 'test_*.py'
python -m unittest discover -s dashboard/tests -p 'test_*.py'
python scripts/check_standard_cycle.py --arduino-json DIRECTORY-CON-ARDUINOJSON-H
```

L'ultimo comando compila lo **sketch effettivo** con g++ e Bridge simulato,
avvia il server HTTP e `RTService` reali, avvia la prova automatica di due cicli
e verifica l'arresto. ArduinoJson 7.4.3 va fornito come header disponibile
localmente; gli eseguibili finiscono in `.local/cycle-check/`.

I test `tests/standard_cycle_test.cpp` verificano anche occupazione, sgombero
prolungato, allarme al timeout, recupero, reset del flusso e wrap di `millis()`.
`tests/sketch_cycle_test.cpp` verifica la risposta dello sketch in modalità protetta
e demo e l'assenza di chiamate GPIO. Si compilano con `-std=c++11 -Wall -Wextra
-Werror -pedantic`, includendo la directory ArduinoJson e, per lo sketch,
`tests/stubs`. La demo richiede `-DCROSSSENSE_STANDARD_CYCLE=1`.

I test provider JavaScript verificano il renderer dei tre indicatori per ogni
fase. Queste prove sul PC sostituiscono il trasporto e non confermano il
toolchain Zephyr o i tempi del Bridge sulla UNO Q.

I test `dashboard/tests/app.test.cjs` verificano selezione iniziale Hardware,
colori MCU e pulsante Ripeti; i test HTTP verificano configurazione, stato della
prova, rifiuto di avvii sovrapposti e cache disabilitata. `GET /api/config`
espone la modalità iniziale; `GET /api/trial` espone lo stato del test;
`POST /api/trial` con `{}` avvia due cicli attraverso gli endpoint esistenti.
Questi endpoint coordinano il produttore sintetico e non modificano Bridge v1
né permettono di forzare una fase STM32.

## Modalità protetta

`scripts/package_rt.py` senza `--standard-cycle` conserva il firmware con
entrambi i rossi logici. Il flag abilita il ciclo soltanto nella copia destinata ad
App Lab (`CROSSSENSE_STANDARD_CYCLE=1`), avvia la prova automatica e identifica la
modalità nella console Python. La dashboard non può cambiare fasi o GPIO.
