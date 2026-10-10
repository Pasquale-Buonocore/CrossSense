Responsabile Pasquale: STM32 real-time, controller, tempi, priorità, watchdog, protezione e allarmi. Contratto delle osservazioni condiviso con Gaetano in `protocol/`. L’app di smoke test in `apps/crosssense-env` non contiene questa logica.

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

Importa `crosssense-linux-led-counter.zip` in My Apps -> Import di Arduino App Lab,
seleziona CrossSense Linux LED Counter e premi Run. Questa cartella resta la sorgente
di sviluppo; lo ZIP contiene app.yaml, README.md, python/ e sketch/.
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
