# Dashboard

Vedere [avvio e demo](../README.md) e [architettura/API](../docs/architecture.md).

`python dashboard/server.py` avvia il server senza sorgente visiva. Il replay si abilita con `--video` o `--video-dir` e un modello locale; `--camera` abilita CAM0, avviabile manualmente. `--bridge` usa la MCU UNO Q, `--native-controller` lo stesso sketch compilato per PC. Le due opzioni trasporto sono esclusive.

Replay e Telecamera condividono tracking, metriche, controller C++ e telemetria. Le ROI sono salvate separatamente; per la camera vanno configurate prima che le osservazioni siano valide. Nessun GPIO, buzzer o feedback elettrico.

ROI/layout/video selezionato sono persistenti. Contatori ed eventi sono di sessione, esportabili in JSON. Errori visione lasciano il backend disponibile. Il comando Riprova riavvia il video selezionato.

La telemetria MCU tollera i buchi di rete brevi senza far lampeggiare i semafori: conserva l'ultimo stato per 4 s, mostra **Connessione instabile** solo tra 4 e 10 s e dichiara il controller disconnesso dopo 10 s. Le richieste manuali sono disabilitate durante il periodo instabile. Questa tolleranza riguarda soltanto la visualizzazione web; watchdog e stato protetto sulla STM32 mantengono le proprie deadline.
