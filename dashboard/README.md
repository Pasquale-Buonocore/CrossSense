# Dashboard CrossSense

Prima dashboard locale, senza dipendenze esterne.

```sh
python3 dashboard/server.py --port 8080
```

Aprire http://127.0.0.1:8080. Il server ascolta solo sul computer locale; `--host 0.0.0.0` permette accesso dalla rete locale.

## Funzioni

- Schema animato con ROI, pedoni e veicolo simulati, separato da un video reale.
- Fasi veicoli, transizione, pedoni e sgombero; richieste pedonali/accessibili con ID univoco.
- Conteggi per direzione, attesa delle richieste servite, registro eventi, esportazione CSV.
- Scenari di affluenza, pedone fermo e perdita telemetria; pausa della demo.
- Durante perdita telemetria stato sconosciuto, countdown nascosto e richieste disabilitate.

Tutti i dati sono **simulati**: non vengono chiamati Bridge, camera o GPIO. Le richieste sono accettate solo dal simulatore del browser. Le statistiche restano in memoria e si azzerano ricaricando la pagina; la pausa ferma il tempo simulato. L’attesa media misura i secondi simulati tra richiesta e apertura della successiva fase pedonale.

## Integrazione successiva

`static/app.js` gestisce rendering e interazioni; `static/providers.js` espone `DemoProvider` e `HardwareProvider`, senza accesso al DOM. Il selettore Demo/Hardware crea un nuovo provider e azzera vista e registro, evitando di presentare dati demo come dati reali. Il provider hardware è esplicitamente disconnesso: nessuna chiamata RPC o HTTP inventata, metriche indisponibili, richieste ed esportazione disabilitate.

Interfaccia provider: `snapshot()`, `tick()`, `request(type, requestId)` e `dispose()`. Solo il demo espone `setScenario()` e `togglePause()`. Lo snapshot attuale è un modello della vista, non il formato definitivo del protocollo MCU. Per l’integrazione reale, aggiungere un adapter di trasporto e validazione al provider hardware: video e conteggi da Linux; fase, uscite comandate, validità ed eventi dalla MCU. Il contratto funzionale è in `protocol/README.md`; serializzazione e metodi RPC non sono ancora implementati. Il servizio Bridge deve vivere indipendentemente dal browser. Non usare il simulatore come controller hardware.

## Verifica

```sh
node dashboard/tests/providers.test.cjs
```

Copre duplicazione delle richieste pendenti, perdita telemetria, sgombero prolungato e isolamento della modalità hardware.
