# Quattro persone, 30 ore

| Persona | Responsabilità principale | Primo risultato integrabile | Confine di lavoro |
|---|---|---|---|
| A — Visione | Camera, modello, tracking, ROI, calibrazione | Snapshot validi/unknown da video o camera | `vision/`, asset locali |
| B — Firmware | FSM, LED/buzzer, protezione, watchdog, rischio | Ciclo completo da osservazioni sintetiche, test di timeout | `firmware/`, sketch app finale |
| C — Linux e dashboard | Bridge adapter, telemetria, contatori, UI | Stato reale MCU e log eventi, anche senza camera | `dashboard/`, Python app finale |
| D — Hardware e validazione | Plastico, cablaggio, scenari, replay e demo | Schema pin verificato, scenari deterministici e test conflitti | `simulation/`, documenti hardware |

La divisione è per persone del team; non sono stati avviati agenti automatici. Persona C integra i contributi, persona B valida qualsiasi variazione dei tempi e del protocollo.

## Sequenza

| Ore | A | B | C | D | Traguardo comune |
|---|---|---|---|---|---|
| 0–2 | Camera e frame/replay | Smoke Bridge e mappa GPIO | Ambiente e contratto | Alimentazione, carrier, componenti | Scheda accessibile, camera o fallback identificato |
| 2–6 | Benchmark detector + ROI | FSM con input sintetici | Adapter e telemetria base | Cablaggio e test invarianti | Protocollo e parametri congelati |
| 6–10 | Tracking e permanenza | Occupazione, watchdog e allarmi | Prima integrazione e dashboard | Esecuzione scenari 1/2/3/5 | Ciclo completo detection→LED |
| 10–18 | Calibrazione e direzione | Velocità/TTC con storico valido | Contatori e latenza | Collisione, guasti e reset | MVP completo e verificato |
| 18–24 | Rifinitura robustezza | Priorità e sgombero massimo | UI e log export | Confronto ciclo fisso; SUMO se c'è margine | Tutti gli scenari MVP ripetibili |
| 24–27 | Freeze e prove offline | Freeze firmware | Freeze app e backup | Plastico e narrazione demo | Nessuna nuova funzione |
| 27–30 | Supporto demo | Supporto demo | Supporto demo | Prova generale e pitch | Buffer per guasti e presentazione |

## Regole pratiche

- Un solo responsabile compila/carica firmware sulla UNO Q alla volta. Caricare uno sketch può interrompere l'app in corso.
- Gli altri sviluppano con replay e fixture condivise; evitare che più processi acquisiscano la stessa camera.
- Protocollo e parametri modificati insieme e con review A/B/C; documentare mappa pin prima dei GPIO.
- Finestra di integrazione almeno ogni 2–3 ore, non a fine hackathon.
- Se entro ora 2 non c'è un frame live, attivare replay in parallelo alla diagnosi hardware. Dichiarare la modalità usata.
- Se entro ora 6 YOLO non sostiene la latenza necessaria, ridurre risoluzione/frequenza e misurare; concordare l'eventuale ripiego.
- MVP prioritario: richiesta automatica, ciclo MCU, occupazione persistente, conflitto/allarme, watchdog, LED e telemetria. SUMO e funzioni opzionali non ritardano questa consegna.
