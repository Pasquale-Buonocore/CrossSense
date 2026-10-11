# Dashboard

Vedere [avvio e demo](../README.md) e [architettura/API](../docs/architecture.md).

`python dashboard/server.py` avvia il server senza sorgente visiva. Il replay si abilita con `--video` o `--video-dir` e un modello locale; `--camera` abilita CAM0, avviabile manualmente. `--bridge` usa la MCU UNO Q, `--native-controller` lo stesso sketch compilato per PC. Le due opzioni trasporto sono esclusive.

Replay e Telecamera condividono tracking, metriche, controller C++ e telemetria. Le ROI sono salvate separatamente; per la camera vanno configurate prima che le osservazioni siano valide. Nessun GPIO, buzzer o feedback elettrico.

ROI/layout/video selezionato sono persistenti. Contatori ed eventi sono di sessione, esportabili in JSON. Errori visione lasciano il backend disponibile. Il comando Riprova riavvia il video selezionato.

La telemetria MCU tollera i buchi di rete brevi senza far lampeggiare i semafori: conserva l'ultimo stato per 4 s, disabilita le richieste manuali tra 4 e 10 s e dichiara il controller disconnesso dopo 10 s. Questa tolleranza riguarda soltanto la visualizzazione web; watchdog e stato protetto sulla STM32 mantengono le proprie deadline.

Il polling della visione interrompe una richiesta senza risposta dopo 1500 ms e riprova al successivo tick, senza accumulare richieste. Durante un breve ritardo web, lo stato attraversamento e i conteggi conservano l’ultimo dato ricevuto per 2 s. Una scadenza dichiarata dal server o un’interruzione web oltre 2 s rende subito sconosciuto lo stato; un nuovo risultato di tracking invalido non recupera un precedente risultato valido. La MCU mantiene la propria deadline e non usa questi valori di visualizzazione. Un JPEG lento non blocca il polling dei metadati.

La dashboard usa testi neutri durante i ritardi: badge, dettagli piccoli, stato Bridge, richieste e registro eventi non mostrano timeout, dati obsoleti o avvisi di ritardo. Il filtro riguarda soltanto la presentazione; validità delle osservazioni, controlli, watchdog e diagnostica nelle API e nel JSON esportato restano attivi. Gli altri allarmi continuano a essere mostrati.

La vista della visione aggiorna lo stato attraversamento, mentre quella delle metriche aggiorna i conteggi: il rendering della telemetria non azzera questi campi a ogni polling.

Ogni PC segue la sorgente condivisa sulla scheda. Aprire o ricaricare la pagina legge la modalità attuale e non invia comandi; soltanto una selezione esplicita cambia la sorgente per tutti. I cambi di modalità da un altro PC vengono applicati anche ai controlli locali.

Il server usa HTTP/1.1 con connessioni persistenti e una coda di 32 connessioni in ingresso, per evitare l’apertura di una connessione TCP per ciascun polling o JPEG e assorbire le richieste simultanee di più dashboard. Le risposte mantengono `Content-Length` e `Cache-Control: no-store`; richieste POST rifiutate prima di leggerne il corpo chiudono la connessione.
