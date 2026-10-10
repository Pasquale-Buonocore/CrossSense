# Interfaccia Bridge v1: un solo scambio

**Contratto v1: adapter Linux/dashboard implementato in `dashboard/rt.py`; ricevitore RPC STM32 implementato in `firmware/sketch/rt_protocol.h`.** Il firmware rimane protetto per default; è disponibile un [ciclo standard di prova sui tre semafori dashboard](../firmware/docs/standard-cycle.md), abilitato esplicitamente nel pacchetto, con lo stesso contratto e senza GPIO. Questa revisione sostituisce la proposta precedente. Pasquale sviluppa STM32, Gaetano produce le osservazioni e Matteo integra il servizio Linux e la dashboard.

## Una sola funzione

```text
crosssense_update(frame_json) -> state_json
```

Linux chiama la funzione circa **5 volte al secondo**, passando una stringa JSON con l'ultimo frame completo. STM32 deposita il frame e risponde subito con una stringa JSON contenente lo stato corrente. Il loop STM32 applica il frame, gestisce tempi e uscite e continua anche senza comunicazione. La risposta può quindi descrivere il tick precedente.

Un solo servizio Linux usa il Bridge, con una chiamata alla volta e solo l'ultimo frame in attesa. La dashboard legge la risposta tramite quel servizio. Camera e inferenza proseguono senza aspettare la RPC.

## Linux -> STM32

```json
{
  "stream": 1234,
  "frame": 42,
  "time_ms": 58210,
  "age_ms": 80,
  "valid": true,
  "crossing": "occupied",
  "approach": "present",
  "tracks": [
    [101, "pedestrian", "crossing", 1200, 450],
    [205, "vehicle", "approach", -7500, 100]
  ],
  "requests": [false, false, false]
}
```

| Campo | Significato |
| --- | --- |
| `stream` | uint32 casuale, nuovo a ogni riavvio Linux/reset tracker/cambio calibrazione. Serve ad azzerare lo storico STM32; nessuna apertura di sessione separata. |
| `frame` | uint32 crescente per nuova acquisizione o nuova segnalazione di indisponibilità. Identifica duplicati; non cambia quando si ritenta lo stesso messaggio. |
| `time_ms` | Timestamp monotono di acquisizione Linux, intero 0..2^53-1; `null` senza immagine. Serve ai delta delle posizioni, non si confronta con il clock STM32. |
| `age_ms` | Età dell'immagine, ricalcolata subito prima dell'invio; uint32 oppure `null` senza immagine. |
| `valid` | Camera, inferenza, ROI critiche e snapshot completo utilizzabili. `false` anche quando ci sono più tracce della capacità o la visibilità è insufficiente. |
| `crossing` | `occupied`, `clear`, `unknown`. `clear` richiede visibilità valida; una lista vuota di oggetti non basta. |
| `approach` | `present`, `clear`, `unknown`, con lo stesso criterio di visibilità. |
| `tracks` | Massimo 8 oggetti, tutti dello stesso frame. Un'assenza non dimostra un attraversamento completato. |
| `requests` | Tre livelli booleani: `[pedestrian, accessible, vehicle_priority]`; tutti false se non servono pulsanti. |

Ogni oggetto usa una tupla di cinque elementi:

```text
[id, class, zone, x_mm, y_mm]
```

- `id`: uint32 non nullo, persistente per l'oggetto e non riutilizzato nello stesso flusso.
- `class`: `pedestrian`, `bicycle`, `vehicle`, `other`.
- `zone`: `waiting_left`, `waiting_right`, `crossing`, `approach`, `outside`.
- `x_mm`, `y_mm`: coordinate calibrate sul piano stradale, interi tra -1.000.000 e 1.000.000 mm. Entrambe `null` quando non sono metricamente valide. Non inviare pixel in questi campi.

Linux filtra le detection e determina le zone. STM32 ricava i pedoni in attesa dalle tracce nelle due zone, filtra la permanenza e calcola velocità/direzione/rischio dalle posizioni. Origine, assi, punto a terra e ROI si concordano una volta nella calibrazione; se cambiano, cambia `stream`. Una posizione null non annulla una zona valida.

Senza una nuova immagine, Linux invia un messaggio con nuovo `frame`, `time_ms=null`, `age_ms=null`, `valid=false`, stati `unknown` e `tracks=[]`. Riceve comunque la telemetria. Senza calibrazione, può inviare ROI valide e coordinate null. Se supera 8 tracce, invia `valid=false` e mantiene eventuale evidenza positiva di occupazione; il frame parziale non autorizza il rilascio veicolare. Con `valid=false` non dichiarare clear; con un'immagine nuova il timestamp deve crescere nello stesso flusso. Un nuovo `stream` deve essere diverso dal precedente.

## STM32 -> Linux

```json
{
  "frame": 42,
  "ok": true,
  "error": null,
  "applied_stream": 1234,
  "applied_frame": 41,
  "uptime_ms": 2100,
  "phase": "PED_CLEARANCE",
  "remaining_ms": null,
  "vehicle_light": "RED",
  "pedestrian_light": "RED",
  "buzzer": false,
  "beacon": false,
  "observation_valid": true,
  "fault": null,
  "alarms": [],
  "estimates": [[205, 5000, 0, 1500, 6500]]
}
```

| Campo | Significato |
| --- | --- |
| `frame`, `ok`, `error` | Esito dell'invio: frame ricevuto, accettazione nel buffer, eventuale errore. `frame=null` se non leggibile. Accettazione non significa fase già cambiata. |
| `applied_stream`, `applied_frame` | Osservazione realmente applicata dal loop, oppure entrambi `null` prima del primo frame. Evita di attribuire alla fase gli effetti di un frame ancora in attesa. |
| `uptime_ms` | uint32, tempo MCU tramite `millis()`; si azzera al riavvio e può fare wrap. Linux usa un proprio timer per la freschezza della dashboard. |
| `phase`, `remaining_ms` | Fase effettiva e tempo alla prossima scadenza programmata; `null` se non c'è scadenza di uscita. Il residuo non promette che una guardia sarà soddisfatta. |
| `vehicle_light`, `pedestrian_light` | `RED`, `YELLOW`, `GREEN`, `OFF`; uscite comandate, senza feedback elettrico. Il giallo pedonale resta inutilizzato finché non concordato. |
| `buzzer`, `beacon` | bool, stato comandato degli attuatori al tick. |
| `observation_valid` | L'osservazione applicata è ancora utilizzabile, con età e stati critici noti. La sola calibrazione assente non invalida le ROI. |
| `fault` | `null`, `NO_DATA`, `INVALID_DATA`, `TIMEOUT`; guasto percettivo/comunicazione prevalente. L'assenza di errore RPC non implica assenza di guasto. |
| `alarms` | Fino a quattro allarmi attivi: `CROSSING_CONFLICT`, `COLLISION_RISK`, `PEDESTRIAN_STOPPED`, `CLEARANCE_TIMEOUT`. |
| `estimates` | Fino a 8 stime veicolari del frame applicato, senza pagine o storico. |

Fasi: `VEHICLE_GREEN`, `VEHICLE_YELLOW`, `ALL_RED_TO_PED`, `PED_GREEN`, `PED_CLEARANCE`, `ALL_RED_TO_VEH`, `PROTECTED_STOP`, `FAULT`.

Ogni stima è `[id, vx_mm_s, vy_mm_s, ttc_ms, stop_mm]`. Valori non disponibili: `null`. La dashboard ricava velocità e direzione da vx/vy; non mostra null come zero. Limiti di rappresentazione proposti: componenti di velocità +/-1.000.000 mm/s, TTC 0..600.000 ms, arresto 0..1.000.000 mm; una stima fuori intervallo diventa null. Non sono soglie dell'allarme. I conteggi completati, le statistiche e lo storico degli allarmi vengono calcolati/conservati su Linux, usando le transizioni della lista `alarms`; questo storico può perdere eventi durante una disconnessione.

## Le regole essenziali

1. **Frame atomico:** controllare formato, range, ID univoci e coerenza prima del deposito. Traccia in crossing con `crossing=clear`, o veicolo in approach con `approach=clear`, è incoerente. `valid=false` e stati unknown sono dati validi del protocollo, ma inutilizzabili per autorizzare il verde veicolare.
2. **Un buffer in attesa:** se il loop non ha consumato il frame precedente, rispondere `ok=false, error="BUSY"`; nessuna sovrascrittura di un'occupazione accettata. Al prossimo giro Linux usa l'ultimo frame disponibile.
3. **Duplicati:** stessa coppia stream/frame dell'ultimo frame accettato restituisce nuovamente `ok=true` senza riapplicare dati/richieste o rinnovare il watchdog; un retry conserva contenuto e timestamp, aggiornando solo l'età. Stessa coppia con contenuto diverso: `BAD_DATA`. Frame più vecchi: `OLD_FRAME`. Confronto uint32: `0 < ((nuovo - ultimo) mod 2^32) < 2^31`. Nuovo stream azzera lo storico e richiede recupero protetto.
4. **Richieste come livelli:** STM32 memorizza una richiesta solo al passaggio false -> true. Linux mantiene true fino a `ok=true`, poi invia false; dopo un errore ritenta senza generare un nuovo impulso. La richiesta accessibile include quella pedonale. Le richieste non forzano fasi/GPIO, restano soggette alle guardie del controller. Al nuovo stream/reset non riprodurre automaticamente vecchi pulsanti.
5. **Watchdog:** limite iniziale 1000 ms sull'età totale. Aggiungere ad `age_ms` il budget di trasporto e il tempo trascorso sulla MCU; i dati invalidi o i duplicati non rinnovano la validità. In assenza di dati utilizzabili, entrare in protezione secondo la macchina a stati. Nessun timeout libera veicoli su strisce occupate.
6. **Errori semplici:** `BAD_DATA`, `OLD_FRAME`, `STALE_FRAME`, `BUSY`; `error=null` quando `ok=true`. Un messaggio malformato non viene applicato e non rinnova il watchdog. Errori del Bridge sono eccezioni Linux; dopo timeout ripartire con l'ultimo frame e uno stato di trasporto ripulito, senza chiamate precedenti ancora in volo.

Una RPC tardiva non è databile dalla MCU usando solo i due clock locali. Questa versione semplice assume **consegna entro 250 ms**, da verificare/garantire nella catena Bridge prima di usare dati clear per il rilascio. Un timeout Python da solo non garantisce che la vecchia chiamata non venga eseguita dopo. Se il limite non è garantibile, la sola RPC semplice non prova la freschezza: mantenere la protezione e risolvere il trasporto prima di abilitare il rilascio. Il budget di 250 ms si sottrae alla deadline, non si aggiunge ai 1000 ms consentiti.

Linux marca la dashboard obsoleta dopo 1000 ms senza una risposta RPC nuova; leggere la sua cache non rinnova questo timer. Un riavvio/perdita collegamento richiede recupero protetto sulla MCU; le osservazioni ripetute non equivalgono a immagini nuove.

## Prima prova condivisa

- Stringa JSON compatta in ingresso/uscita: **massimo 900 byte** ciascuna, inclusi tutti i campi; anche l'envelope RPC deve rientrare nel buffer compilato. Limite da controllare su Linux prima dell'invio.
- 8 tracce, 5 Hz, timeout osservazioni 1000 ms, budget trasporto 250 ms: parametri iniziali da misurare sul plastico, non prestazioni già dimostrate.
- Provare frame normale, occupato, camera assente, calibrazione assente, duplicato, overflow, riavvio e RPC bloccata. Verificare che il loop continui e che le strisce occupate restino protette.

I [sorgenti RPClite 0.3.1](https://github.com/arduino-libraries/Arduino_RPClite/blob/0.3.1/src/Arduino_RPClite.h) dichiarano un decoder predefinito da 1024 byte. RouterBridge 0.4.3 imposta però il buffer RPC a 256 byte e negozia tale limite con Linux: non basta la capacità del decoder. Il profilo dello sketch include la copia MPL-2.0 in `firmware/sketch/libraries/Arduino_RouterBridge`, con buffer RPC 1024 e stack worker 4096 byte in tutte le unità di compilazione. Il JSON resta limitato a 900 byte per lasciare spazio all'envelope MsgPack. Le app LED e ping precedenti mantengono le loro RPC di prova.
