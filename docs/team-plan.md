# Quattro persone, 30 ore

| Persona | Responsabilità | Primo risultato integrabile | Confine di lavoro |
|---|---|---|---|
| Gaetano — Visione | YOLO26n, tracking, ID persistenti, ROI e osservazioni | Snapshot validi/unknown da video o camera | `vision/`, asset locali |
| Pasquale — STM32 / real-time | FSM, LED/buzzer, protezione, watchdog e rischio | Ciclo completo da osservazioni sintetiche, test di timeout | `firmware/`, sketch app finale |
| Due persone jolly | Supporto flessibile su integrazione Linux–Bridge, dashboard, hardware, calibrazione, scenari e validazione | Sbloccare le dipendenze e verificare l’integrazione | `dashboard/`, `simulation/`, Python app finale e documenti hardware |

Gaetano e Pasquale concordano il [contratto delle osservazioni](../protocol/README.md): coordinate, timestamp, validità, occupazione e tracce perse. Pasquale valida le variazioni dei tempi del controller. I due jolly si assegnano di volta in volta le attività più urgenti, indicando chi segue ogni integrazione; non hanno aree esclusive fisse.

## Sequenza

| Ore | Gaetano | Pasquale | Attività disponibili per i due jolly | Traguardo comune |
|---|---|---|---|---|
| 0–2 | Camera e frame/replay | Smoke Bridge e mappa GPIO | Ambiente, contratto, alimentazione e componenti | Scheda accessibile, camera o fallback identificato |
| 2–6 | Benchmark YOLO26n + ROI | FSM con input sintetici | Adapter, telemetria, cablaggio e test invarianti | Protocollo e parametri congelati |
| 6–10 | Tracking, ID e permanenza | Occupazione, watchdog e allarmi | Prima integrazione, dashboard e scenari 1/2/3/5 | Ciclo completo detection→LED |
| 10–18 | Coordinate calibrate e direzione | Velocità/TTC con storico valido | Supporto calibrazione, contatori, latenza, collisione, guasti e reset | MVP completo e verificato |
| 18–24 | Rifinitura robustezza | Priorità e sgombero massimo | UI, log export, confronto ciclo fisso; SUMO se c’è margine | Tutti gli scenari MVP ripetibili |
| 24–27 | Freeze e prove offline | Freeze firmware | Freeze app, backup, plastico e narrazione demo | Nessuna nuova funzione |
| 27–30 | Supporto demo | Supporto demo | Prova generale, pitch e supporto dove necessario | Buffer per guasti e presentazione |

## Regole pratiche

- Un solo responsabile compila/carica firmware sulla UNO Q alla volta. Caricare uno sketch può interrompere l'app in corso.
- Gli altri sviluppano con replay e fixture condivise; evitare che più processi acquisiscano la stessa camera.
- Protocollo e parametri modificati insieme e con review di Gaetano, Pasquale e del jolly che segue l’integrazione; documentare mappa pin prima dei GPIO.
- Finestra di integrazione almeno ogni 2–3 ore, non a fine hackathon.
- Se entro ora 2 non c'è un frame live, attivare replay in parallelo alla diagnosi hardware. Dichiarare la modalità usata.
- Se entro ora 6 YOLO non sostiene la latenza necessaria, ridurre risoluzione/frequenza e misurare; concordare l'eventuale ripiego.
- MVP prioritario: richiesta automatica, ciclo MCU, occupazione persistente, conflitto/allarme, watchdog, LED e telemetria. SUMO e funzioni opzionali non ritardano questa consegna.
