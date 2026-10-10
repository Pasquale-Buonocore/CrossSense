# Contratto Bridge

## Endpoint implementato

| Direzione | Nome RPC | Argomenti | Risposta |
| --- | --- | --- | --- |
| Python → MCU | crosssense_status | Nessuno | Stringa `scaffold_ready` |

Python usa `Bridge.call("crosssense_status")`; lo sketch registra `Bridge.provide`. Il callback legge uno stato costante e non modifica GPIO. Il risultato conferma soltanto che lo scaffold risponde, non che camera o luci siano operative.

Riferimenti ufficiali: [RouterBridge C++](https://github.com/arduino-libraries/Arduino_RouterBridge), [esempio Python Bridge](https://github.com/arduino/app-bricks-examples/tree/main/core-and-foundational/01-led-blink/03-blinking-an-led-from-python).

## Contratto operativo da definire

Prima di pilotare le luci, definire versione del protocollo, sequenza dei comandi, stato richiesto, conferma dello stato applicato, timeout heartbeat e comportamento di avvio/guasto. Rifiutare stati sconosciuti e combinazioni conflittuali; il controllo dei vincoli deve risiedere anche sul MCU.

Non sostituire l'endpoint diagnostico con un comando che accende luci senza aggiornare cablaggio, protocollo e prove di perdita comunicazione. Evitare RPC annidate dentro callback MCU: la libreria documenta il rischio di deadlock.
