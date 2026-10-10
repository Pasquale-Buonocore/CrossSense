# CrossSense

**HackTurin · Challenge 1 — GOMA: Smart Crossing · Arduino UNO Q**

CrossSense è un prototipo di attraversamento intelligente con computer vision e AI locale, progettato per migliorare la sicurezza dei pedoni e ottimizzare il traffico. Una singola camera MIPI, prevista nel semaforo, osserva le strisce, le zone di attesa sui due lati e i veicoli in avvicinamento. Il sistema adatta i tempi semaforici e attiva segnalazioni luminose e acustiche. L'obiettivo è eseguire l'intero sistema offline su Arduino UNO Q 4 GB.

## La Challenge 1 e la nostra proposta

La descrizione elaborata dal team prevede quattro requisiti: riconoscere le categorie di utenti, attivare le luci, contare attraversamenti e direzioni, funzionare senza Internet.

CrossSense propone di combinarli con:

- **Semaforo adattivo:** rilevare pedoni in attesa e veicoli, regolando le fasi in base al traffico e ai tempi di attesa, entro limiti prestabiliti.
- **Protezione durante lo sgombero:** mantenere il rosso ai veicoli che incrociano l'attraversamento finché qualcuno resta sulle strisce, anche quando il pedonale torna rosso.
- **Allerta anticipata:** stimare velocità, traiettorie, tempo al possibile conflitto e spazio di arresto con una camera calibrata. Un rosso lampeggiante rivolto verso l'attraversamento e luci lungo la strada segnalano situazioni critiche nel plastico.

Riconosceremo pedoni, biciclette e veicoli; eventuali classi per ausili visibili richiedono un modello adeguato. Attraversamento lento, immobilità e possibile caduta sono segnali da verificare, senza dedurre età o disabilità dall'immagine. Velocità e rischio restano stime da validare.

## Architettura e responsabilità

| Componente | Responsabilità prevista | Responsabile |
| --- | --- | --- |
| Linux / Qualcomm QRB2210 | Acquisizione MIPI CSI, YOLO, tracking multi-oggetto, ROI, calibrazione e osservazioni | Gaetano |
| STM32U585 / controllo real-time | Storico delle posizioni, velocità e direzione, distanza di arresto, rischio, macchina a stati, priorità, tempi, LED, buzzer, faro di emergenza e watchdog | Pasquale |
| Dashboard su Linux | Interfaccia web, conteggi completati, statistiche e coordinamento dell'integrazione Linux-Bridge | Matteo |
| Hardware e validazione | Cablaggio, calibrazione, scenari, simulazione e supporto all'integrazione | Quarta persona / jolly |

```text
Camera MIPI -> YOLO -> tracking -> ROI e coordinate calibrate (Linux)
                                      |
                                Bridge / RPC
                                      v
                     Storico, rischio e macchina a stati (STM32)
                                      |
                            LED, buzzer, lampeggiatore
                                      |
                         Telemetria -> dashboard Linux
```

Linux associa a ogni oggetto ID, classe, posizione, timestamp e confidenza. La calibrazione riferisce le coordinate al piano stradale. STM32 riceve le osservazioni tramite Arduino Bridge/RPC e decide le fasi; la logica critica e il servizio Bridge funzionano anche con dashboard chiusa. In assenza di osservazioni valide, il controller deve entrare in una condizione di protezione. Video, bounding box e traiettorie restano su Linux.

Dettagli in [architettura](docs/architecture.md), [contratto delle osservazioni](protocol/README.md) e [divisione del lavoro](docs/team-plan.md).

## Otto scenari funzionali

| # | Scenario | Comportamento previsto |
| --- | --- | --- |
| 1 | Pedoni in attesa | Rilevare persone sui due lati, misurare l'attesa e generare una richiesta automatica dopo una breve permanenza nella ROI. Se l'avvicinamento è validamente libero, anticipare la sequenza; con veicoli presenti rispettare il verde minimo veicolare. Conservare giallo e tutto rosso in entrambi i casi. |
| 2 | Pedone lento | Prolungare la protezione dell'attraversamento finché le strisce sono occupate, anche dopo la fine del verde pedonale. |
| 3 | Pedone fermo sulle strisce | Attivare una segnalazione luminosa di attenzione e mantenere il rosso ai veicoli; oltre il massimo di sgombero, restare in protezione con allarme. |
| 4 | Veicolo che rischia di non fermarsi | Stimare il rischio di raggiungere le strisce occupate senza arrestarsi e attivare immediatamente il rosso lampeggiante di emergenza rivolto all'attraversamento. |
| 5 | Pedone sulle strisce con verde veicolare | Rilevare il conflitto, attivare l'allarme luminoso sulle strisce e applicare la politica di arresto del controller. |
| 6 | Traffico veicolare intenso | Limitare la durata ordinaria del verde pedonale considerando coda e richieste, mantenendo la protezione delle persone già sulle strisce. La coda richiede ROI e tracking dedicati. |
| 7 | Mezzo di emergenza | Accettare una richiesta di priorità veicolare e servirla attraverso una transizione sicura, senza interrompere la protezione di un attraversamento occupato. Il riconoscimento visivo è opzionale; nel MVP la richiesta può essere simulata esplicitamente. |
| 8 | Accessibilità | Attivare una segnalazione acustica dedicata su richiesta accessibile; eventuali riconoscimenti visivi restano sperimentali. |

## Strategia semaforica e base del firmware STM32

È disponibile una [prova del ciclo standard sui semafori della dashboard](firmware/docs/standard-cycle.md):
`scripts/try_standard_cycle.py` invia osservazioni sintetiche all'API dashboard;
lo sketch STM32 decide le fasi e restituisce la telemetria. Il pacchetto si
genera con `python scripts/package_rt.py dist/crosssense-dashboard-cycle-v3 --standard-cycle --zip`.
L'app avvia automaticamente due cicli sulla parte Linux; lo sketch non usa GPIO.
Il ciclo è verificato sul PC con Bridge simulato; la verifica sulla UNO Q resta da eseguire.

Il PDF descrive il ciclo `Verde veicoli -> Giallo veicoli -> Tutto rosso -> Verde pedoni -> Giallo pedoni -> Tutto rosso -> Verde veicoli`. Per il firmware, la [revisione tecnica](docs/technical-review.md) precisa la fase finale pedonale come **sgombero con rosso pedoni**: chiude i nuovi ingressi e protegge chi è già sulle strisce. Un eventuale giallo pedonale del plastico richiede un significato esplicito prima del cablaggio.

Gli identificatori seguenti descrivono il controller completo previsto; il ciclo
dashboard implementa il sottoinsieme di base descritto nella guida della prova.

| Stato | Uscite semaforiche previste | Condizione principale di uscita |
| --- | --- | --- |
| `VEHICLE_GREEN` | Verde veicoli, rosso pedoni | Richiesta pedonale servibile secondo verde minimo, presenza veicoli e attesa massima |
| `VEHICLE_YELLOW` | Giallo veicoli, rosso pedoni | Scadenza del tempo di giallo |
| `ALL_RED_TO_PED` | Rosso veicoli e pedoni | Scadenza dell'intervallo tutto rosso, con osservazioni valide |
| `PED_GREEN` | Rosso veicoli, verde pedoni | Fine del tempo ordinario, entro i limiti configurati |
| `PED_CLEARANCE` | Rosso veicoli e pedoni | Attraversamento libero stabilmente; se scade il massimo di sgombero, passaggio a `PROTECTED_STOP` |
| `ALL_RED_TO_VEH` | Rosso veicoli e pedoni | Intervallo tutto rosso concluso e attraversamento ancora validamente libero |
| `PROTECTED_STOP` | Rosso veicoli e pedoni, allarme | Recupero solo secondo criteri di validità, attraversamento libero e riarmo da definire |
| `FAULT` | Arresto prudente fino a tutto rosso, segnalazione di guasto | Osservazioni valide e libere per una finestra continua, eventuale riarmo e transizione tutto rosso |

### Regole del controller

- Richiesta pedonale automatica dopo conferma della permanenza nella zona di attesa, oppure manuale tramite pulsante. Le richieste restano pendenti fino alla gestione prevista.
- Tempi minimi e massimi configurabili; con una richiesta pedonale persistente, l'attesa massima limita il verde veicolare. Senza richieste pedonali e con condizioni valide, il verde veicolare può essere mantenuto.
- Il verde pedonale ordinario non si estende indefinitamente in presenza di una richiesta veicolare. Alla scadenza si chiudono i nuovi ingressi, mantenendo il rosso ai veicoli finché le strisce sono occupate.
- Il superamento del massimo di sgombero attiva protezione e allarme: un timeout non autorizza il verde veicolare su un attraversamento occupato.
- Nessuna coppia di verdi conflittuali, anche durante boot, reset, priorità e modifica dei parametri. La priorità di un mezzo di emergenza non annulla la protezione dei pedoni.
- Frame mancanti, obsoleti, parziali, ROI occultate e overflow non equivalgono ad attraversamento libero. Con verde veicolare e senza conflitto immediato, la revisione prevede giallo di chiusura e poi tutto rosso; il conflitto attiva subito l'allarme. La politica di arresto va verificata sul plastico.
- Allerta luminosa separata dalle fasi semaforiche. La dashboard invia richieste con esito, senza scrivere direttamente fasi o GPIO.

### Ingressi, uscite e organizzazione del codice

| Area STM32 | Contratto da rispettare |
| --- | --- |
| Ricezione osservazioni | Un frame completo applicato atomicamente: flusso, numero del frame, timestamp, età, validità, occupazione, avvicinamento e tracce; attese derivate dalle zone, coordinate metriche null quando indisponibili |
| Storico e stime | ID, classe, posizione e timestamp per velocità/direzione; invalidazione al cambio di sessione, calibrazione o traccia non affidabile |
| Richieste | Automatiche dalle osservazioni; manuali, accessibili e priorità simulata come livelli booleani nello stesso frame, con rilevamento false -> true |
| Controllo | Macchina a stati deterministica, tempi, richieste pendenti e guardie di transizione |
| Attuazione | LED semaforici, buzzer e faro/lampeggiatore; mappa pin, polarità, driver e alimentazione ancora da definire |
| Guasti e watchdog | Validità delle osservazioni, timeout di comunicazione, protezione e recupero; un heartbeat non rinnova la validità di una vecchia immagine |
| Telemetria | Fase effettiva, tempi, uscite comandate, ultima osservazione accettata, guasti, allarmi, richieste e stime con relativa validità |

Il loop deve essere temporizzato e non bloccante, con buffer limitati e callback RPC brevi che depositano lo snapshot. Verificare la concorrenza del Bridge prima di condividere dati con il loop. La [proposta Bridge v1 semplificata](protocol/bridge-v1.md) usa una sola RPC `crosssense_update`, con frame JSON in ingresso e stato corrente in risposta; è ancora da concordare e implementare.

Budget iniziale del protocollo da misurare: **8 tracce, 5 Hz, massimo 900 byte JSON per messaggio, deadline delle osservazioni 1 s**. Le 32 tracce restano un obiettivo futuro. I clock Linux e MCU non sono direttamente confrontabili; lo storico usa i timestamp di acquisizione per i delta. Il budget di trasporto di 250 ms deve essere garantito/verificato e incluso nella deadline. Sono parametri proposti, non prestazioni dimostrate.

### Parametri da fissare prima dell'implementazione

- Permanenza minima nelle ROI di attesa, verde minimo veicolare e attesa massima pedonale.
- Verde pedonale minimo/massimo, giallo veicolare, intervalli tutto rosso e massimo di sgombero.
- Finestra di attraversamento libero stabile, timeout osservazioni, condizioni di recupero e guasti con riarmo manuale.
- Finestra dello storico, soglie di immobilità, confidenza/validità, TTC, reazione, decelerazione, margine e isteresi dell'allarme.
- Mappa GPIO, uscite di boot/reset, frequenza del lampeggio e modalità del buzzer accessibile.

Nessun valore temporale, pin o limite fisico è fissato dal PDF. Vanno concordati e validati sul prototipo.

## Stima del rischio di collisione

Per ogni veicolo in avvicinamento, STM32 stima distanza dall'attraversamento, velocità, direzione, tempo al conflitto (TTC) e spazio di arresto dallo storico delle posizioni calibrate.

```text
D_arresto = v * t_reazione + v^2 / (2 * decelerazione)
```

Usare `v` in m/s, `t_reazione` in s e decelerazione positiva in m/s²; aggiungere un margine di sicurezza configurabile. La distanza va misurata lungo la traiettoria verso l'attraversamento. Il TTC è utilizzabile solo con velocità valida e componente di avvicinamento positiva; un veicolo fermo o in allontanamento non produce un TTC attendibile.

Quando la traiettoria interseca le strisce occupate e distanza/TTC indicano rischio, attivare il rosso lampeggiante rivolto all'attraversamento. Considerare età delle osservazioni, errore di calibrazione e isteresi. Senza calibrazione mantenere protezione e allarme di conflitto basati sulle ROI, indicando le stime metriche come indisponibili. Il lampeggiatore segnala il rischio e non arresta fisicamente il veicolo.

Le stime sono destinate alla dimostrazione sperimentale sul plastico e in ambiente controllato, non al controllo di un incrocio reale.

## Dashboard web e metriche

La dashboard sarà ospitata su Linux e accessibile tramite browser. Mostrerà lo stato effettivo ricevuto dalla MCU; in assenza di telemetria aggiornata indicherà lo stato obsoleto e non presenterà un countdown attendibile.

| Metrica | Contenuto previsto |
| --- | --- |
| Pedoni in attesa | Conteggio per lato |
| Pedoni in attraversamento | Numero, direzione e stato |
| Attraversamenti completati | Conteggio per direzione, deduplicato tramite tracking |
| Veicoli transitati | Conteggio e flusso nel tempo |
| Velocità media dei veicoli | Segmenti calibrati e validi, con esclusione esplicita della fase iniziale di accelerazione |
| Tempi medi di attesa | Pedoni e veicoli; per questi ultimi serve osservare e tracciare la coda |
| Allarmi generati | Numero di episodi e tipologia, senza contare ogni frame come un nuovo allarme |
| Latenza | Tempo tra acquisizione, elaborazione e azione MCU |
| Stato semaforico | Fase attiva e tempo residuo; residuo non disponibile durante protezione senza scadenza |

Funzionalità aggiuntiva: video elaborato in tempo reale con bounding box, ID, traiettorie e ROI. Linux gestisce video, conteggi e aggregazioni; STM32 fornisce fasi, stime cinematiche e allarmi. I pulsanti della dashboard inviano richieste secondo il [contratto](protocol/README.md).

## Priorità per le 30 ore

| Livello nel PDF | Risultato previsto |
| --- | --- |
| MVP obbligatorio | Acquisizione camera, detection/tracking, ROI, richiesta pedonale automatica, macchina a stati STM32, protezione dell'attraversamento occupato, allarme di collisione, LED e dashboard base |
| Seconda priorità | Stima della velocità calibrata, statistiche avanzate, confronto tramite SUMO e scenari dedicati con pedoni fermi |
| Opzionali | Riconoscimento dei mezzi di emergenza, accessibilità visiva sperimentale e visualizzazione avanzata delle traiettorie |

Non è previsto training dei modelli AI. Il [piano del team](docs/team-plan.md) dettaglia consegne e integrazione nelle 30 ore.

Due dipendenze da chiarire nell'implementazione: la protezione di un pedone fermo deve valere già nel MVP, anche se il PDF colloca gli scenari dedicati nella seconda priorità; l'allarme metrico di collisione richiede calibrazione e velocità valida, pur essendo la stima calibrata elencata nella seconda priorità. Finché questi prerequisiti non sono verificati, la demo deve distinguere l'allarme di conflitto per ROI dalla previsione metrica.

Ordine operativo STM32: concordare protocollo, parametri e GPIO; realizzare il ciclo con osservazioni sintetiche; aggiungere protezione e watchdog; integrare Bridge e telemetria; aggiungere storico, stime e allarmi; verificare priorità e richieste accessibili. SUMO e funzioni opzionali non devono ritardare il ciclo completo.

## Dimostrazione e presentazione finale

La demo prevista combina un prototipo fisico con LED semaforici, buzzer e allarme luminoso, una dashboard e computer vision su video live o preregistrato. Gli scenari vengono attivati in sequenza mostrando osservazioni, fase MCU e uscite. Dichiarare sempre se la prova usa camera live, replay o dati sintetici.

Il confronto software con un semaforo tradizionale usa gli stessi arrivi, vincoli di protezione e finestre di misura, riportando tempi di attesa, flusso e gestione dei conflitti. SUMO resta una seconda priorità; una simulazione non dimostra una riduzione degli incidenti reali.

Traccia riutilizzabile per la presentazione:

1. **Problema e obiettivo:** attraversamenti lenti o occupati e tempi fissi; proposta di adattamento locale con protezione persistente.
2. **Soluzione:** una camera, AI offline su UNO Q e controllo real-time STM32 indipendente dalla dashboard.
3. **Architettura:** osservazioni Linux -> Bridge -> decisioni STM32 -> attuatori e telemetria.
4. **Comportamento:** otto scenari, distinguendo funzioni dimostrate e opzionali; spiegare ammissione pedonale e sgombero.
5. **Demo e risultati:** ciclo normale, pedone lento/fermo, conflitto e perdita delle osservazioni; riportare solo misure raccolte di latenza, attesa, flusso e falsi allarmi.
6. **Limiti e prossimi passi:** calibrazione, qualità delle osservazioni, soglie da validare e completamento delle funzioni successive.

Prima della demo verificare: assenza di verdi conflittuali; veicoli sempre rossi con strisce occupate oltre la scadenza; richieste automatiche/manuali e tempi minimi/massimi; allarme di conflitto e rischio con stime valide; timeout, frame vecchi/duplicati/fuori ordine, ROI occultata, overflow, riavvii e recupero; dashboard chiusa senza interruzione del controllo. Preparare tutte le risorse locali e provare l'esecuzione senza Internet. I casi dettagliati sono nella [revisione tecnica](docs/technical-review.md).

## Struttura del repository

```text
CrossSense/
├── README.md
├── CrossSense.pdf           # Piano funzionale del progetto
├── app.yaml                 # Manifest in radice; app da completare
├── .gitignore
├── apps/crosssense-env/     # App di smoke test Bridge Linux-MCU
│   ├── app.yaml
│   ├── python/main.py
│   └── sketch/              # Sketch e profilo Arduino Zephyr
├── firmware/               # Area controller STM32
├── vision/                 # Pipeline e calibrazione
├── dashboard/              # Telemetria e interfaccia web
├── protocol/               # Contratto delle osservazioni
├── simulation/             # Replay e confronto
├── data/                   # Dati per prove
├── models/                 # Modelli locali
├── scripts/                # Diagnostica e accesso alla scheda
└── docs/                   # Architettura, ambiente e piano del team
```

Le cartelle dei componenti sono aree di lavoro; la loro presenza non indica che le funzioni siano già implementate.

## Avvio

L'app disponibile per la diagnostica è `apps/crosssense-env`. Il manifest in radice non dispone attualmente di `python/` e `sketch/`: l'app finale va completata prima di usarlo.

Sulla UNO Q:

1. Collegare la scheda con un cavo USB-C dati e aprire Arduino App Lab.
2. Importare `apps/crosssense-env` con la modalità disponibile nella versione installata, oppure creare un'app e copiarvi il suo `app.yaml`, `python/` e `sketch/`, mantenendo i percorsi.
3. Avviare: Python interroga ogni secondo `crosssense_ping`; lo sketch restituisce l'uptime MCU. Il log riporta `BRIDGE_OK` e il tempo di andata/ritorno RPC, oppure `BRIDGE_ERROR`.

Riferimenti: [manuale UNO Q](https://docs.arduino.cc/tutorials/uno-q/user-manual/) e [formato delle app Arduino](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md). Installazione e download iniziali possono richiedere Internet; l'esecuzione offline andrà provata dopo aver predisposto le risorse locali.

## Stato attuale e prossimi passi

Sono disponibili la dashboard Demo/Hardware e l’app RT Bridge in `firmware/`: ricevitore STM32 `crosssense_update`, validazione, buffer atomico e watchdog. L'app RT mantiene i campi semaforici rossi in modalità protetta; il ciclo standard dashboard si abilita nel pacchetto e non pilota GPIO. AI/tracking, conteggi e stime del rischio restano da implementare. La prova LED precedente è conservata in `apps/crosssense-led-counter/`, la diagnostica senza GPIO in `apps/crosssense-env/`. Vedi [avvio dell’app RT](firmware/README.md). I documenti di ambiente registrano acquisizione IMX219 e comunicazione Bridge verificate sulla scheda.

Per la demo partiremo da rilevamento → segnalazione → conteggio, poi aggiungeremo adattamento e allerte. Mostreremo un passaggio normale, un pedone fermo, direzioni opposte e un veicolo in avvicinamento, misurando latenza, falsi allarmi e continuità della protezione. Le prove si svolgeranno sul plastico e in ambiente controllato.

## Ambiente verificato e strumenti del team


```sh
python3 -m venv .venv
.venv/bin/python scripts/check_host.py
python3 scripts/board.py shell 'hostname; free -h; v4l2-ctl --list-devices'
```

`scripts/board.py` trova ADB nel PATH o nell'installazione Arduino locale. Seleziona la scheda con `--serial` in presenza di più dispositivi. Non richiede password SSH.

La prima app, `apps/crosssense-env`, verifica solo RPC Linux–MCU. Non pilota GPIO né implementa il controller semaforico. Per copiarla e avviarla sulla scheda:

```sh
python3 scripts/board.py push apps/crosssense-env /home/arduino/ArduinoApps/
python3 scripts/board.py shell 'TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/crosssense-env'
python3 scripts/board.py shell 'arduino-app-cli app logs /home/arduino/ArduinoApps/crosssense-env --tail 20'
```

Avviare un'app con sketch carica nuovo firmware MCU. Arresto:

```sh
python3 scripts/board.py shell 'arduino-app-cli app stop /home/arduino/ArduinoApps/crosssense-env'
```

L'ambiente locale di base non richiede pacchetti esterni. La dashboard usa la libreria standard Python; la visione richiede ancora benchmark e scelta del runtime; l'SDK `arduino.app_utils` viene usato nel runtime App Lab sulla scheda, non nel venv del Mac.

## Documenti

- [Piano funzionale originale in PDF](CrossSense.pdf)
- [Architettura e decisioni tecniche](docs/architecture.md)
- [Stato verificato dell'ambiente](docs/environment.md)
- [Revisione tecnica](docs/technical-review.md)
- [Divisione del lavoro e piano 30 ore](docs/team-plan.md)
- [Contratto delle osservazioni, bozza](protocol/README.md)
- [Proposta di interfaccia Bridge v1 da concordare](protocol/bridge-v1.md)

Cartelle riservate: `vision/` pipeline e calibrazione, `firmware/` controller MCU, `dashboard/` telemetria, `simulation/` replay e confronto.

## Integrazione video YOLO di Gaetano

La pipeline MP4 → YOLO26n/ByteTrack → ROI → Bridge v1 è disponibile nel servizio
dashboard. Mostra box con ID, classe e confidenza, occupazione e attese correnti.
**Configura zone YOLO** consente di ridisegnare e salvare i quattro poligoni
condivisi; modifica delle ROI e loop video creano un nuovo stream RT.
Avvio, dipendenze e pacchetto UNO Q in [vision/README.md](vision/README.md).
