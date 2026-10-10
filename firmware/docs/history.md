> Documento storico. Il perimetro corrente è replay dichiarato e segnali soltanto nella dashboard. Riferimenti aggiornati: README principale e docs/architecture.md. Le affermazioni di verifica sotto riportate appartengono alle prove precedenti.

# Storico di sviluppo STM32

Il [piano corrente](README.md) contiene lo stato aggiornato. Le voci seguenti conservano le decisioni della sessione del 10 ottobre 2026, nell'ordine della discussione; non assegnano orari non registrati.

## 1. Piano e responsabilità

Il piano descritto nel PDF del repository è stato trasferito nel README principale come base per architettura, scenari e presentazione. Pasquale segue la parte STM32: controller autonomo, tempi, priorità, watchdog, protezione, stime e allarmi. Linux produce le osservazioni e riceve la telemetria necessaria alla dashboard.

Decisione: l'arrivo dei dati alimenta il controller; il suo loop deve continuare anche quando Linux non comunica. Il materiale di riferimento è il [README principale](../../README.md).

## 2. Semplificazione del Bridge

Su richiesta di Pasquale, la prima proposta con più chiamate è stata sostituita da una sola RPC `crosssense_update(frame_json) -> state_json`, con stringhe JSON e frame completi. La versione vigente è in [bridge-v1.md](../../protocol/bridge-v1.md).

Concordati: un servizio Linux proprietario del Bridge, una chiamata in corso, ultimo frame disponibile, invii circa 5 Hz, massimo 8 tracce e 900 byte per JSON. Stream e frame identificano flusso e ordine; valori non disponibili restano null. Il buffer MCU contiene un solo frame in attesa e distingue accettazione da applicazione.

Chiarito `requests`: livelli `[pedestrian, accessible, vehicle_priority]`, memorizzati sul fronte false -> true. La richiesta accessibile include quella pedonale; nessuna richiesta forza direttamente le uscite.

Timeout osservazioni 1000 ms e budget trasporto 250 ms restano parametri iniziali, con verifica del trasporto ancora necessaria. Non sono prestazioni hardware dimostrate.

## 3. Piano in sei step e scelta del linguaggio

Concordato l'ordine: strutture/configurazione, scambio Bridge, FSM di base, comportamento adattivo, stime/allarmi, integrazione e taratura. Il dettaglio è nel [piano](README.md).

Pasquale ha chiesto inizialmente il motivo di C++, poi ha confermato la preferenza per la soluzione più semplice con C++. Si mantiene C++11, coerente con lo sketch Arduino e RouterBridge; nessuna riscrittura in C richiesta.

## 4. Implementazione e verifica dello step 1

Creati [crosssense_types.h](../sketch/crosssense_types.h), [crosssense_config.h](../sketch/crosssense_config.h) e [step1_test.cpp](../tests/step1_test.cpp). Le strutture non dipendono da Arduino e usano capacità fisse. I dati assenti sono espliciti, distinti dallo zero; i tempi semaforici non concordati restano a zero e rendono la configurazione incompleta.

Verifica eseguita con GCC MinGW 9.2 e `-std=c++11 -Wall -Wextra -Werror -pedantic`: superati esempi del protocollo, null/zero, limiti di rappresentazione, configurazione e stato logico iniziale.

Risultato registrato:

```text
STEP1_OK: protocol examples, unavailable values, capacity, configuration and initial logical state
Native sizes: frame=200 state=336 response=348 bytes
```

Limiti: test su PC, nessuna conferma di compilazione MCU o di GPIO/Bridge reale. Parser JSON, RPC v1, FSM, watchdog operativo e stime ancora assenti.

## 5. Preparazione per Arduino App Lab

[sketch.ino](../sketch/sketch.ino) include ora gli header dello step 1 per farli compilare anche con l'app Arduino. Il runtime resta **CrossSense Linux LED Counter**, con `crosssense_set_led` e `crosssense_get_led_change_count`; Python sceglie la sequenza LED. Gli header non introducono un ciclo semaforico.

Preparato e controllato un archivio `dist/crosssense-step1.zip` con manifest, Python, sketch, header e sorgenti dei test. Il pacchetto non esegue i test nativi. Compilazione UNO Q, caricamento e osservazione dei LED sulla scheda non sono stati verificati durante questa preparazione.

Al checkpoint di documentazione lo ZIP non risulta più presente: per importare nuovamente l'app occorre rigenerarlo dai sorgenti. La cartella firmware rimane il riferimento di sviluppo.

## 6. Stato Linux osservato al checkpoint

Nel repository è presente l'adapter Linux/dashboard in [dashboard/rt.py](../../dashboard/rt.py), introdotto dal commit `e920f47`. Espone lo scambio verso la RPC v1 e la gestione delle richieste per la dashboard; il [README dashboard](../../dashboard/README.md) documenta l'avvio.

Questa voce registra la presenza del codice e della documentazione. Non è una verifica di integrazione sul Bridge reale. Lo sketch LED attuale non espone ancora la RPC che l'adapter attende.

## 7. Documentazione persistente e avvio della discussione sullo step 2

Pasquale ha richiesto di conservare gli step e lo storico in `firmware/docs`, poi ha confermato lo step 1 completato e chiesto di discutere l'obiettivo dello step 2 prima del codice.

Creati il [piano con punto di ripresa](README.md) e questo storico. Lo step 2 è registrato come **in discussione**, con obiettivo proposto: ricezione/validazione JSON, deposito atomico, gestione ordine/duplicati/richieste e risposta compatibile con Linux. Le transizioni semaforiche restano allo step 3.

Prossimo passo: concordare il perimetro dello step 2 e poi implementare il confine Bridge. In questa sessione di documentazione non è stato aggiunto codice operativo né ripetuta la verifica nativa dello step 1.

## 8. Ciclo standard con API dashboard — 10 ottobre 2026

Richiesto uno script Python e la parte STM32 per provare il ciclo standard
attraverso l'API rilasciata nella dashboard. A questo checkpoint il ricevitore
Bridge v1 e il watchdog erano già presenti in `rt_protocol.h`; il firmware
manteneva entrambi i LED rossi.

Aggiunto `standard_cycle.h`: ciclo su richiesta pedonale, tempi demo separati,
avvio/recupero tutto rosso, sgombero vincolato all'occupazione, arresto su dati
invalidi/scaduti, conflitto ROI e timeout di sgombero latched. LED3 veicoli,
LED4 pedoni, active LOW; giallo ottenuto da rosso + verde. Il ciclo viene
abilitato nella copia App Lab con `scripts/package_rt.py --standard-cycle`;
il comportamento protetto resta quello predefinito delle sorgenti.

`scripts/try_standard_cycle.py` usa solo HTTP: osservazioni sintetiche a 10 Hz,
richiesta con ID deduplicabile, verifica delle fasi/uscite reali nella telemetria,
due o più cicli configurabili e conferma dell'arresto dopo perdita delle
osservazioni. `RTService` resta l'unico proprietario del Bridge. Nessuna modifica
al formato JSON o agli endpoint API.

Verifiche su PC: test C++11 di step 1, protocollo RT, ciclo e sketch in modalità
protetta/demo; 7 test Python dello script, 5 test dell'adapter e test provider
JavaScript. Il controllo `scripts/check_standard_cycle.py` ha eseguito due
cicli completi attraverso il server HTTP e `RTService` effettivi, collegati allo
sketch nativo con GPIO/RouterBridge simulati, terminando con `CYCLE_OK 2/2`,
`STOP_OK fault=INVALID_DATA` e `HTTP_SKETCH_OK`.

ADB non rileva schede collegate. Nessun caricamento STM32, compilazione Zephyr
o prova dei LED fisici eseguito in questa sessione. Restano da verificare
trasporto entro 250 ms, colori/tempi sulla UNO Q e integrazione visione. Buzzer,
beacon, priorità veicolare e stime cinematiche restano fuori dalla prova.

Punto di ripresa: importare lo ZIP generato in `dist/`, avviare l'app e seguire
la [guida della prova](standard-cycle.md) con l'IP reale della scheda.

## 9. Correzione: tre semafori dashboard e avvio automatico — 10 ottobre 2026

L'utente ha chiarito che la prova deve aggiornare i tre semafori visualizzati,
senza accendere i LED integrati. L'interpretazione precedente era errata.
Rimosse tutte le chiamate GPIO da `sketch.ino`; ciclo e watchdog rimangono
sulla STM32 e la risposta conserva esattamente il contratto Bridge v1.

Il percorso esistente è già completo: `crosssense_update` restituisce JSON,
`RTService` lo valida e lo espone su `GET /api/rt`, `HardwareProvider` converte
i colori e `TrafficSignals` disegna veicoli e pedoni SX/DX. Non è stato aggiunto
un endpoint per forzare luci o fasi; i due pedonali condividono il valore previsto
dal protocollo.

Aggiunto `firmware/python/cycle_demo.py`, avviato dopo il bind riuscito del
server tramite un callback opzionale. Il pacchetto demo parte con due cicli
sintetici usando `127.0.0.1`; non richiede lo script sul PC né risoluzione DNS.
Il precedente errore `getaddrinfo failed` era una mancata risoluzione dell'host
prima della richiesta HTTP. Lo script manuale ora spiega anche il segnaposto
`IP-DELLA-UNO-Q`.

Verifiche: 11 test Python di script/avvio automatico, 8 test dashboard; test
dello sketch in entrambe le modalità con zero chiamate GPIO; due cicli automatici
con sketch nativo, server e RTService reali, terminati con `DEMO_OK` e
`HTTP_SKETCH_OK`. Il test JavaScript usa il renderer effettivo per verificare
i colori di tutti e tre gli indicatori in ogni fase. Bridge reale e compilazione
Zephyr restano da verificare sulla UNO Q.

Il nuovo archivio è `dist/crosssense-dashboard-cycle.zip`, app **CrossSense
Dashboard Cycle**. Il vecchio archivio LED resta un artefatto superato; per la
prova importare quello nuovo e selezionare Hardware nella dashboard dell'app.

## 10. Dashboard osservata sulla porta sbagliata e prova ripetibile — 10 ottobre 2026

L'utente ha mostrato `CYCLE_OK 2/2`, `STOP_OK` e `DEMO_OK` dalla scheda, ma
guardava `http://192.168.23.19:8080/`. Lettura diretta delle API: 8080 senza
Bridge (`state=null`), 8081 collegata alla STM32, `FAULT/INVALID_DATA` e campi
luce rossi dopo il termine della prova. La discordanza era fra due servizi.

La pagina ora parte in Hardware quando il server usa il Bridge, indica il
servizio sorgente e permette di ripetere la prova con un pulsante. Il produttore
sintetico mantiene un solo test alla volta, espone stato/esito e si rilancia
tramite HTTP locale. Aggiunti controlli cache e ridotto il rumore dei poll nella
console, mantenendo gli errori e le transizioni MCU. Il formato Bridge v1 e il
firmware STM32 rimangono invariati rispetto alla correzione senza GPIO.

Verifiche: 12 test Python del produttore, 11 test dashboard, test JavaScript
della vista e dei tre indicatori; due cicli automatici con sketch nativo e
server reali. Un tentativo di produzione sintetica dal PC verso la scheda ha
ricevuto timeout HTTP; la prova da usare rimane quella locale nell'app.
Nuovo archivio: `dist/crosssense-dashboard-cycle-v2.zip`.

## 11. Unico servizio dashboard/API/Bridge sulla 8080 — 10 ottobre 2026

L'utente ha chiarito che la porta 8081 non deve esistere. La scelta di un
secondo servizio per la prova era errata: dashboard e API devono restare sulla
8080, con il Bridge attivo nello stesso processo. Le indicazioni della voce 10
sulla porta da aprire sono quindi superate.

Corretti `firmware/app.yaml`, l'avvio Python App Lab e l'URL predefinito dello
script manuale per usare la 8080. Nessuna porta alternativa o fallback. Il
produttore automatico continua a usare la porta effettivamente associata al
server; se il bind fallisce, non viene avviato. Firmware, protocollo Bridge v1
e mappatura dei tre semafori non cambiano.

Verifiche PC: 12 test Python script/avvio, 11 test dashboard, test JavaScript
della vista e dei provider superati. Pacchetto aggiornato:
`dist/crosssense-dashboard-cycle-v3.zip`. Per applicarlo sulla scheda fermare
la vecchia app sulla 8081 e il processo dashboard standalone sulla 8080, quindi
avviare l'app aggiornata e aprire `http://192.168.23.19:8080/`. Questa sessione
non ha arrestato o sostituito i processi sulla UNO Q.

## Modello per la prossima voce

```text
Data e step:
Richiesta/obiettivo:
Decisioni e motivazione:
File modificati:
Verifiche eseguite ed esito (PC o scheda):
Limiti e decisioni ancora aperte:
Prossimo punto di ripresa:
```
