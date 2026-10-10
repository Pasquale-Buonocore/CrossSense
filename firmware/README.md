# CrossSense RT Bridge

App Arduino App Lab per UNO Q: ricevitore STM32 Bridge v1 e servizio Linux
con dashboard su porta 8081. La precedente prova LED è conservata in
`apps/crosssense-led-counter/`.

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

Con ArduinoJson disponibile:

```sh
c++ -std=c++17 -I /percorso/ArduinoJson/src firmware/tests/rt_protocol_test.cpp -o /tmp/crosssense-rt-test
/tmp/crosssense-rt-test
python3 -m unittest discover -s dashboard/tests -p 'test_*.py'
node dashboard/tests/providers.test.cjs
```

Copertura MCU: buffer atomico/BUSY, frame applicato, duplicati e contenuto
alterato, timestamp, frame vecchi/scaduti, fronti richieste, nuovo stream,
watchdog, wrap sequenze/clock, dati malformati e uscite protette.
