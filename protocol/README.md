# Contratto delle osservazioni — specifica funzionale v0.2

Ripartizione funzionale concordata: Gaetano gestisce acquisizione, YOLO26n, tracking, ROI e coordinate calibrate su Linux; Pasquale gestisce storico delle posizioni, velocità, direzione, rischio e macchina a stati sulla STM32; Matteo gestisce dashboard e statistiche. Formato di serializzazione e metodi Bridge devono ancora essere concordati e implementati. Il servizio Linux–Bridge continua a funzionare anche con dashboard chiusa. Un messaggio descrive un frame completo e viene applicato atomicamente; non inviare chiamate separate per ogni oggetto.

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
| tracks | array limitato | ID, classe, x_m, y_m, confidence, position_valid, zone |
| overflow | bool | oltre capacità: stato degradato, mai dichiarare libero per troncamento |

Ogni traccia usa un ID persistente nella sessione e una classe esplicita (pedone, bicicletta, veicolo o altra classe concordata). `zone` identifica attesa sinistra/destra, attraversamento, avvicinamento o esterno. `confidence` è la confidenza della detection, non una misura dell’accuratezza della posizione. `position_valid` indica se la posizione metrica è utilizzabile. In assenza di calibrazione le zone restano utilizzabili, ma velocità, TTC e distanza di arresto metrici sono indisponibili.

Pasquale deriva permanenza nelle zone, richieste automatiche, velocità, direzione e rischio dallo storico delle osservazioni. I conteggi e gli stati aggregati nel frame sono osservazioni percettive: non impongono richieste o fasi al controller. Un frame vuoto valido è distinto da un frame invalido, parziale o con ROI non visibile.

Coordinate: piano della strada, origine e assi documentati nella calibrazione; punto di appoggio a terra per pedoni, punto scelto e verificato per i veicoli. Conservare bounding box e traiettorie video su Linux.

Budget iniziale da misurare: massimo 32 tracce, frequenza 5–10 Hz, deadline osservazioni 1 s. Questi valori sono obiettivi per la demo, non prestazioni già dimostrate. L'occupazione prevale su errori di conteggio. Nessun verde veicolare viene autorizzato usando un frame parziale o obsoleto.

L'età inviata da Linux non copre una coda bloccata nel trasporto. Usare coda di lunghezza uno (ultimo frame), limite temporale RPC e misura del tempo di consegna; se il limite non è garantibile, invalidare l'osservazione. Ricevere heartbeat freschi non rinnova la validità di una vecchia immagine. Al cambio di sessione, reset delle stime cinematiche e nuova sequenza di recupero.

## Telemetria MCU → Linux

| Campo | Contenuto |
|---|---|
| protocol_version, mcu_session_id, telemetry_sequence, mcu_uptime_ms | Versione, identificazione dei riavvii e ordinamento telemetria |
| phase, phase_elapsed_ms, phase_remaining_ms | Fase reale e tempi; residuo nullable durante protezione senza scadenza |
| outputs | Uscite comandate per LED, buzzer e lampeggiatore; non feedback elettrico |
| observation_valid, last_accepted_sequence, observation_age_ms | Validità ed età dell’ultima osservazione accettata, misurata sul controller |
| fault_code, alarm_flags, pending_requests | Guasti, allarmi e richieste pendenti |
| vehicle_estimates | Per ID: velocità, direzione, TTC, distanza di arresto e validità delle singole stime; valori invalidi non mostrati come zero |

Gli eventi di allarme hanno sessione MCU, ID progressivo, timestamp MCU, tipo e attivazione/cessazione. Linux deduplica gli eventi e segnala eventuali lacune nella sequenza. Attraversamenti completati, flussi e aggregazioni statistiche restano su Linux.

## Richieste dashboard → MCU

I pulsanti inviano richieste pedonali, accessibili o di priorità simulata con `request_id`. Il controller risponde accepted/rejected con motivo e gestisce la transizione sicura. Le richieste ripetute con lo stesso ID non devono produrre azioni duplicate. Nessuna scrittura diretta della fase o dei GPIO dalla dashboard. Parametri fuori intervallo rifiutati dalla MCU.

La dashboard mostra telemetria effettiva e marca lo stato come obsoleto quando scade; in quel caso non continua a presentare un countdown come attendibile. Video, bounding box e traiettorie arrivano direttamente da Linux. Il servizio Bridge e il loop MCU non dipendono dalla presenza di un browser.

Definire limiti, enum numerici, serializzazione e metodi RPC dopo aver verificato i tipi supportati sulla versione Bridge installata. Questa specifica non rappresenta un’API già implementata.
