Responsabile Pasquale: STM32 real-time, controller, tempi, priorità, watchdog, protezione e allarmi. Contratto delle osservazioni condiviso con Gaetano in `protocol/`. L’app di smoke test in `apps/crosssense-env` non contiene questa logica.

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

Questa cartella contiene ora un'app Arduino App Lab per UNO Q:

```text
firmware/
├── app.yaml
├── python/main.py
└── sketch/
    ├── sketch.ino
    └── sketch.yaml
```

Linux definisce la sequenza in `python/main.py` e invia un comando RPC
`Bridge.call("crosssense_set_led", led, color)` alla STM32 per ogni passo.
La STM32 controlla soltanto i due LED RGB integrati, LED3 e LED4; non contiene
una sequenza autonoma. Non servono cablaggi. LOW accende e HIGH spegne.

Il comando seleziona LED 3 o 4 e colore 1=rosso, 2=verde, 3=blu. Prima di
accendere il canale selezionato, la STM32 spegne tutti gli altri. Il comando
(0, 0) spegne entrambi i LED. Parametri non validi restituiscono -1 senza
modificare le uscite. La risposta valida vale `led * 10 + color`, ad esempio
31 per LED3 rosso; viene inviata dopo l'applicazione del comando.

La STM32 conserva anche `ledChangeCount`. Linux lo legge dopo ogni comando
con `Bridge.call("crosssense_get_led_change_count")` e lo stampa come
`mcu_changes`. Il contatore aumenta una volta per cambio di stato: il primo
LED acceso vale 1, passare a un altro LED/colore aggiunge 1 e spegnere un
LED acceso aggiunge 1. Ripetere lo stesso comando, leggere il contatore o
inviare parametri invalidi non lo incrementa. I sei canali spenti all'avvio
valgono 0; il contatore si azzera al riavvio dello sketch/MCU. Non è salvato
in memoria permanente. Il valore conta stati comandati, senza sensori ottici.

Il callback usa `Bridge.provide_safe`, disponibile in RouterBridge 0.4.3,
per eseguire sul thread del loop. Il loop restituisce il controllo ogni
10 ms al servizio RPC e non avanza autonomamente i LED.

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

La risposta conferma che la MCU ha eseguito la scrittura GPIO; il controllo
visivo verifica che il LED sia effettivamente acceso. `roundtrip_ms` misura
il tempo totale delle due RPC (comando e lettura contatore). Se fallisce la
lettura del contatore, Python riprova lo stesso passo: la MCU non conta due
volte il medesimo stato.

Per provare che è Linux a decidere la sequenza, cambia soltanto `SEQUENCE`
in Python, ad esempio `[(3, 1), (0, 0), (4, 3), (0, 0)]`, o cambia
`STEP_SECONDS` a `1.0`, poi premi Run. Non serve modificare lo sketch.

Se Linux si arresta o il collegamento si interrompe, la sequenza si ferma
e la MCU mantiene l'ultimo stato ricevuto. Questa prova non implementa un
watchdog di comunicazione. All'avvio dello sketch entrambi i LED sono spenti
fino al primo comando valido.

Compilazione con il core UNO Q, caricamento e comunicazione sulla scheda
restano da verificare: ADB non rilevava dispositivi USB durante la preparazione.

Verifica locale riuscita con lo sketch compilato tramite GCC su PC e GPIO/
Bridge simulati, collegato alla sequenza Python: avvio con LED spenti,
selezione dei sei canali, comando di spegnimento, rifiuto dei parametri
invalidi, ripetizione della sequenza e tentativi dopo timeout o risposta
inattesa, lettura del contatore MCU e assenza di doppi incrementi durante
i tentativi ripetuti. Questa verifica non sostituisce la compilazione con il core UNO Q
né la prova del trasporto Bridge reale.

Questa prova non implementa ancora il controller semaforico.
