# CrossSense RT Bridge

Il [piano degli step e punto di ripresa](docs/README.md) e lo [storico delle decisioni e verifiche](docs/history.md) sono conservati in `firmware/docs`. Step 1 completato con verifiche native; step 2 in discussione prima dell'implementazione.

## Controller STM32: step 1

Sono disponibili le strutture C++11 del [protocollo Bridge v1](../protocol/bridge-v1.md), senza dipendenze Arduino o allocazioni dinamiche:

- [`sketch/crosssense_types.h`](sketch/crosssense_types.h): frame, tracce, richieste, fase, stato, allarmi, stime e risposta RPC.
- [`sketch/crosssense_config.h`](sketch/crosssense_config.h): capacità fisse e configurazione temporale.
- [`tests/step1_test.cpp`](tests/step1_test.cpp): verifica nativa degli esempi e dei casi senza valori disponibili.

`Nullable<T>` usa `has_value` per distinguere JSON null da uno zero valido. La posizione ha una sola validità per x/y; le stime hanno validità individuale. Gli array hanno capacità 8 per tracce/stime e 4 per allarmi; solo gli elementi prima del rispettivo contatore sono attivi. Il parser dello step 2 dovrà controllare i contatori, i range e la coerenza prima di depositare il frame. `ControllerState.applied` identifica il frame applicato, mentre `UpdateResponse.frame` identifica quello ricevuto.

Lo stato logico iniziale è `FAULT`/`NO_DATA`, con entrambi i semafori rossi, nessun countdown e nessuna osservazione valida. Questo non configura GPIO: lo sketch include gli header per verificarne la compilazione anche in App Lab, mentre il comportamento resta quello della prova LED sotto.

Limiti definiti: 8 tracce, 900 byte JSON, 5 Hz; tick proposto 10 ms, timeout osservazioni 1000 ms, budget di trasporto 250 ms. Le durate semaforiche e le finestre di conferma restano a **0 = da configurare**. `isConfigurationComplete` rifiuta parametri mancanti, durate incompatibili con i confronti temporali al wrap e intervalli incoerenti; verifica solo la coerenza numerica, non hardware o garanzie del trasporto. Le soglie del rischio saranno definite nello step 5.

Verifica locale da questa cartella, con un compilatore C++11:

```sh
mkdir -p build
g++ -std=c++11 -Wall -Wextra -Werror -pedantic tests/step1_test.cpp -o build/step1_test
./build/step1_test
```

In PowerShell: `New-Item -ItemType Directory -Force build`, compilare con `-o build/step1_test.exe` ed eseguire `./build/step1_test.exe`. La cartella `build/` è ignorata da Git. I tempi nel test sono fixture, non parametri scelti per la demo. Le dimensioni stampate sono del compilatore locale e vanno misurate anche con il toolchain MCU.

Completato questo step, il prossimo è il parser/serializer e la RPC `crosssense_update`; la macchina a stati, il watchdog operativo e le stime non sono ancora implementati.

### Avvio in Arduino App Lab

Il pacchetto preparato in `../dist/crosssense-step1.zip` contiene il manifest, Python, sketch, nuovi header e test sorgenti; esclude gli eseguibili locali. Collegare la UNO Q, selezionarla in App Lab, importare lo ZIP da **My Apps -> Import**, aprire **CrossSense Linux LED Counter** e premere **Run**. App Lab compila/carica lo sketch e avvia Python sulla scheda.

Nella console Python attendere `LED_OK ... mcu_changes=...` e verificare l'alternanza dei LED3/LED4. L'avvio conferma la compilazione dei nuovi header e prova la comunicazione LED esistente; non esegue i test nativi C++ né una macchina a stati semaforica. Eventuali modifiche all'app importata sono sulla scheda, non nel checkout locale. Fonte: [formato delle app Arduino](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md).

## Prova Linux -> Bridge -> STM32

Il firmware espone `crosssense_update(String) -> String` con il formato di
`protocol/bridge-v1.md`. Valida il frame completo prima del deposito, mantiene
un solo buffer, rifiuta dati incoerenti, frame vecchi e immagini scadute.
I duplicati identici confermano la ricezione senza riapplicare richieste o
rinnovare il watchdog; solo `age_ms` può differire. Timestamp e sequenze
vengono controllati anche attraverso messaggi di indisponibilità; wrap uint32
supportato. La risposta distingue ricezione e frame applicato dal loop.

Le richieste sono memorizzate su fronte false → true; accessible include
pedestrian. Il watchdog usa età immagine + 250 ms di budget + tempo MCU,
con deadline 1000 ms. La sola durata RPC misurata da Linux non garantisce
il limite di consegna sulla MCU.

**Modalità di integrazione protetta:** LED3 (veicoli) e LED4 (pedoni) sono
entrambi rossi. Con dati validi la fase è `PROTECTED_STOP`, altrimenti `FAULT`
con `NO_DATA`, `INVALID_DATA` o `TIMEOUT`. Residuo null, buzzer/beacon false,
stime/allarmi vuoti. Le richieste restano pendenti e non aprono il verde.
Non sono ancora implementati macchina semaforica, stime cinematiche,
attuatori esterni o camera/inferenza. Nessun altro RPC può forzare i GPIO.

## Preparazione e caricamento

Il pacchetto include una copia della dashboard ottenuta dalle sorgenti,
senza mantenere una seconda versione nel repository:

```sh
python3 scripts/package_rt.py /tmp/crosssense-rt-bridge
python3 scripts/board.py push /tmp/crosssense-rt-bridge /home/arduino/ArduinoApps/
python3 scripts/board.py shell 'TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/crosssense-rt-bridge'
```

L'avvio compila e carica lo sketch STM32; cambia il firmware attivo sulla
scheda. Le altre app sono conservate. Dipendenze del profilo: ArduinoJson
7.4.3 e RouterBridge 0.4.3 con dipendenze transitive esplicite. Il primo
avvio può richiedere download. Lo sketch usa `provide_safe` per mantenere
il buffer e il loop sullo stesso thread.

Aprire `http://IP-DELLA-SCHEDA:8081` e scegliere **Hardware**. Il servizio
scambia dati anche senza browser: in assenza di visione invia osservazioni
invalide e riceve la telemetria reale del controller protetto. L'API non
ha autenticazione; la porta è esposta sulla rete locale per la demo.

## Verifica locale

Con ArduinoJson disposnibile:

La sequenza predefinita alterna LED3 rosso, LED4 rosso, LED3 verde,
LED4 verde, LED3 blu, LED4 blu. Linux attende 0,5 secondi dopo ogni conferma.
In caso di errore o risposta inattesa stampa LED_ERROR e riprova lo stesso
passo dopo un secondo. Ripetere un comando applica lo stesso stato.

Importa `crosssense-step1.zip` in My Apps -> Import di Arduino App Lab,
seleziona CrossSense Linux LED Counter e premi Run. Questa cartella resta la sorgente
di sviluppo; lo ZIP contiene app.yaml, README.md, python/, sketch/ e tests/.
Il profilo include RouterBridge e le dipendenze transitive nelle versioni
già usate da crosssense-env, con il core Zephyr 1.0.0.

Nella Console -> Main (Python) devono comparire righe come:

```text
LED_OK step=1 led=3 color=rosso ack=31 mcu_changes=1 roundtrip_ms=...
LED_OK step=2 led=4 color=rosso ack=41 mcu_changes=2 roundtrip_ms=...
```

Copertura MCU: buffer atomico/BUSY, frame applicato, duplicati e contenuto
alterato, timestamp, frame vecchi/scaduti, fronti richieste, nuovo stream,
watchdog, wrap sequenze/clock, dati malformati e uscite protette.
