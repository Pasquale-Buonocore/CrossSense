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

In modalità Demo tutti i dati sono **simulati**: non vengono chiamati Bridge, camera o GPIO. Le richieste sono accettate solo dal simulatore del browser. Le statistiche restano in memoria e si azzerano ricaricando la pagina; la pausa ferma il tempo simulato. L’attesa media misura i secondi simulati tra richiesta e apertura della successiva fase pedonale.

## Provider

`static/providers.js` separa dati e azioni dalla vista: `DemoProvider` mantiene
la simulazione, `HardwareProvider` usa l'API HTTP del servizio Linux descritta
sotto. Cambiare modalità azzera vista e registro. Il simulatore non controlla
l'hardware; in Hardware le metriche Linux non ancora disponibili restano vuote.

## Verifica

```sh
node dashboard/tests/providers.test.cjs
```

Copre duplicazione delle richieste pendenti, perdita telemetria, sgombero prolungato e isolamento della modalità hardware.

## Semafori sul frame

L’anteprima usa `static/example-frame.jpg`, foto di riferimento fornita dal team, non un video live. `static/signals.js` disegna tre indicatori: pedoni sinistra/destra condividono `snapshot.outputs.pedestrian`; veicoli usa `snapshot.outputs.vehicle`. Questi valori rappresentano uscite comandate, non feedback elettrico. Il provider demo li genera dalla fase; il provider hardware disconnesso restituisce `null`, visualizzato come stato sconosciuto. L’adapter hardware dovrà mappare le uscite effettive MCU a questi campi solo con telemetria valida e fresca.

Attivare **Posiziona semafori**, poi trascinare un indicatore oppure selezionarlo e cliccare sul frame. Sono disponibili coordinate X/Y percentuali e frecce della tastiera sull’indicatore (Shift per spostamenti maggiori). Le posizioni sono salvate sul server e condivise da tutti i browser della stessa dashboard; mantengono l’allineamento al ridimensionamento e si possono ripristinare per tutti. I browser aggiornano la disposizione ogni 2 secondi; durante il posizionamento mantengono la propria modifica fino al salvataggio. Non vengono inviate al controller. La sostituzione con frame camera dovrà mantenere immagine e overlay nello stesso contenitore, senza ritaglio del frame.

## Adapter dashboard / RT implementato (Bridge v1)

Avvio sulla UNO Q con il runtime Arduino disponibile:

```sh
python3 dashboard/server.py --bridge --port 8080
```

Senza `--bridge` la modalità Hardware rimane disconnessa. Il firmware deve
esporre `crosssense_update(String) -> String` secondo `protocol/bridge-v1.md`:
l’app `firmware/` espone questa RPC in modalità protetta. La prova LED precedente è in `apps/crosssense-led-counter/`. Non viene
caricato né modificato firmware dalla dashboard.

Il servizio `rt.py` possiede il Bridge e scambia JSON compatti a 5 Hz con
una sola chiamata in volo; una chiamata bloccata non avvia altre RPC.
La telemetria scade dopo 1000 ms; risposte oltre 250 ms o malformate
invalidano subito il collegamento. Il controllo del tempo totale RPC rileva
ritardi ma non garantisce il limite di consegna del trasporto: la protezione
MCU e la validazione su hardware restano necessarie.

API HTTP sulla stessa origine della dashboard:

- `GET /api/rt`: `{connected, age_ms, state, error}`. Leggere la cache non
  rinnova l'età della risposta MCU.
- `POST /api/observations`: JSON del frame Bridge v1, con `requests` tutte
  false. Il produttore visione invia solo nuove acquisizioni; il servizio
  conserva l'ultima, controlla ordine/timestamp e ricalcola l'età. Le identità
  del flusso e dei frame sul Bridge sono assegnate dal servizio, perché
  comprende anche nuovi messaggi di indisponibilità. Un cambio di flusso
  visione cambia il flusso Bridge e azzera le richieste pendenti.
- `POST /api/requests`: `{"type":"pedestrian","request_id":"id-univoco"}`;
  tipi `pedestrian`, `accessible`, `vehicle_priority`. Risposta `queued`
  significa in coda sul servizio, non richiesta già servita dalla MCU.
  Gli ID sono deduplicati negli ultimi 256 comandi della sessione.

I POST richiedono `Content-Type: application/json`. Richieste browser da
origini diverse vengono rifiutate. L'ascolto predefinito rimane localhost;
non è presente autenticazione per accesso dalla rete locale.

I pulsanti diventano livelli booleani: true fino a `ok=true`, poi false fino
alla relativa conferma; nuovi pulsanti durante uno scambio/reset vengono
rifiutati e possono essere riprovati. Errori conservano il livello pendente.
Senza nuova immagine il servizio invia un nuovo frame invalido, senza
riutilizzare l'immagine come osservazione fresca. Non deduce occupazione,
conteggi o tempi d'attesa dalle fasi: questi dati restano indisponibili in
Hardware. Mostra fase, uscite comandate e residuo reale (anche null).
Video live, statistiche Linux e controller MCU non sono implementati qui.

Verifica adapter:

```sh
python3 -m unittest discover -s dashboard/tests -p 'test_*.py'
node dashboard/tests/providers.test.cjs
```

Le prove usano un Bridge simulato: formato, coerenza ROI, coordinate,
ordinamento, nuovo flusso, impulsi richieste, errori, ritardi e scadenza cache.
Non sostituiscono la verifica del trasporto e del controller sulla UNO Q.


## Posizioni condivise

`GET /api/signal-layout` restituisce `{positions, revision}`.
`POST /api/signal-layout` salva una mappa parziale degli indicatori, ad esempio
`{"ped-left":{"x":25.51,"y":53.09}}`. Ogni punto deve avere X tra 5 e 95,
Y tra 12 e 88. Modifiche a indicatori diversi vengono unite; sullo stesso
indicatore prevale l'ultimo salvataggio. Ripristina applica i valori iniziali
a tutti i browser. Errori di salvataggio sono mostrati e ritentati.

Il file persistente predefinito è `dashboard/.local/signal-layout.json`,
separato dai file pubblici. `--layout-file /percorso/layout.json` permette
un percorso diverso. Riavvio e aggiornamento dei sorgenti conservano il file.
I vecchi salvataggi personali non vengono più usati. La disposizione della
UNO Q è stata inizializzata con le posizioni presenti nel browser del team.
