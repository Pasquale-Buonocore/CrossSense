# Contratto delle osservazioni — bozza v0.1

Da concordare tra visione e firmware prima delle prime implementazioni. Non è ancora un'API RPC implementata. Un messaggio descrive un frame completo e viene applicato atomicamente; non inviare chiamate separate per ogni oggetto.

## Frame Linux → MCU

| Campo | Tipo/Unità | Semantica |
|---|---|---|
| protocol_version | intero | 1; versioni sconosciute rifiutate |
| session_id | stringa limitata | cambia al riavvio del processo di visione |
| sequence | uint32 | incremento per frame; vecchi/duplicati rifiutati; gestire wrap |
| capture_monotonic_ms | uint64, ms | clock monotono Linux; utile per delta tra frame, non confrontabile direttamente con millis() MCU |
| frame_age_ms | uint32, ms | età da acquisizione fino all'invio; il ricevitore deve includere il budget di trasporto nell'accettazione |
| perception_valid | bool | camera + inferenza + visibilità delle ROI valide; heartbeat del processo non basta |
| calibration_valid | bool | unità metriche utilizzabili; senza calibrazione non calcolare velocità/TTC in metri |
| calibration_id | stringa limitata | cambio calibrazione invalida gli storici MCU |
| crossing_state | enum | occupied / clear / unknown; clear richiede visibilità valida |
| waiting_left/right | uint16 | conteggi filtrati nelle ROI di attesa |
| approach_state | enum | present / clear / unknown; assenza di box non equivale a clear |
| tracks | array limitato | ID, classe, x_m, y_m, confidenza, position_valid |
| overflow | bool | oltre capacità: stato degradato, mai dichiarare libero per troncamento |

Coordinate: piano della strada, origine e assi documentati nella calibrazione; punto di appoggio a terra per pedoni, punto scelto e verificato per i veicoli. Conservare bounding box e traiettorie video su Linux.

Budget iniziale da misurare: massimo 32 tracce, frequenza 5–10 Hz, deadline osservazioni 1 s. Questi valori sono obiettivi per la demo, non prestazioni già dimostrate. L'occupazione prevale su errori di conteggio. Nessun verde veicolare viene autorizzato usando un frame parziale o obsoleto.

L'età inviata da Linux non copre una coda bloccata nel trasporto. Usare coda di lunghezza uno (ultimo frame), limite temporale RPC e misura del tempo di consegna; se il limite non è garantibile, invalidare l'osservazione. Ricevere heartbeat freschi non rinnova la validità di una vecchia immagine. Al cambio di sessione, reset delle stime cinematiche e nuova sequenza di recupero.

## Telemetria MCU → Linux

`protocol_version`, `mcu_uptime_ms`, `phase`, `phase_elapsed_ms`, `phase_remaining_ms` (nullable per protezione senza scadenza), `outputs`, `observation_valid`, `last_accepted_sequence`, `fault_code`, `alarm_flags`, `pending_requests`.

La dashboard legge lo stato effettivo della MCU. Eventuali pulsanti inviano richieste (pedonale/accessibile), non impostano la fase. Parametri fuori intervallo vengono rifiutati dalla MCU. Definire limiti e schema di serializzazione solo dopo aver verificato i tipi supportati e la latenza di Bridge sulla versione installata.
