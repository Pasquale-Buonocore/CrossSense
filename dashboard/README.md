# Dashboard

Vedere [avvio e demo](../README.md) e [architettura/API](../docs/architecture.md).

`python dashboard/server.py` avvia il server senza sorgente visiva. Il replay si abilita con `--video` o `--video-dir` e un modello locale; `--camera` abilita CAM0, avviabile manualmente. `--bridge` usa la MCU UNO Q, `--native-controller` lo stesso sketch compilato per PC. Le due opzioni trasporto sono esclusive.

Replay e Telecamera condividono tracking, metriche, controller C++ e telemetria. Le ROI sono salvate separatamente; per la camera vanno configurate prima che le osservazioni siano valide. Nessun GPIO, buzzer o feedback elettrico.

ROI/layout/video selezionato sono persistenti. Contatori ed eventi sono di sessione, esportabili in JSON. Errori visione lasciano il backend disponibile. Il comando Riprova riavvia il video selezionato.

La telemetria MCU tollera i buchi di rete brevi senza far lampeggiare i semafori: conserva l'ultimo stato per 4 s, mostra **Connessione instabile** solo tra 4 e 10 s e dichiara il controller disconnesso dopo 10 s. Le richieste manuali sono disabilitate durante il periodo instabile. Questa tolleranza riguarda soltanto la visualizzazione web; watchdog e stato protetto sulla STM32 mantengono le proprie deadline.

Il polling della visione interrompe una richiesta senza risposta dopo 750 ms e riprova al successivo tick, senza accumulare richieste. **Aggiornamento osservazioni…** indica che la copia nel browser è scaduta in attesa di nuovi metadati; **Osservazioni obsolete** indica invece che il server ha segnalato un’acquisizione scaduta. In entrambi i casi i dati scaduti non vengono mostrati come osservazioni correnti. Un JPEG lento non blocca il polling dei metadati.

Il server usa HTTP/1.1 con connessioni persistenti e una coda di 32 connessioni in ingresso, per evitare l’apertura di una connessione TCP per ciascun polling o JPEG e assorbire le richieste simultanee di più dashboard. Le risposte mantengono `Content-Length` e `Cache-Control: no-store`; richieste POST rifiutate prima di leggerne il corpo chiudono la connessione.
