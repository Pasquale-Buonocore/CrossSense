# Contratto Linux–controller

RPC attiva: `crosssense_update(frame_json) -> state_json`. Vedere [Bridge v1](bridge-v1.md) per schema e [architettura](../docs/architecture.md) per comportamento attuale.

Linux produce osservazioni replay e metriche; la MCU decide le fasi logiche. Il browser visualizza segnali e allarmi, senza oggetti fisici. Lo stesso controller è eseguibile sul PC per sviluppo e test. Il ciclo è implementato e si abilita con `--controller-cycle` nel pacchetto.

8 tracce, payload 900 byte, polling obiettivo 5 Hz, deadline osservazione 1000 ms comprendente budget trasporto 250 ms. Nessuna calibrazione: x/y null, estimates vuoto. Duplicati non rinnovano il watchdog. Richieste nuove attendono una nuova acquisizione. Campi buzzer/beacon riservati false.
