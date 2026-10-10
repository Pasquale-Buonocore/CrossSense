# Dashboard

Vedere [avvio e demo](../README.md) e [architettura/API](../docs/architecture.md).

`python dashboard/server.py` avvia solo il simulatore UI. Il replay si abilita esplicitamente con `--video` o `--video-dir` e un modello locale; `--bridge` usa la MCU UNO Q, `--native-controller` lo stesso sketch compilato per PC. Le due opzioni trasporto sono esclusive.

Nella modalità Replay / Controller le metriche sono prodotte dal tracking, gli indicatori dal controller C++, gli allarmi dalla telemetria e l’immobilità dalle traiettorie video. Nessun GPIO, buzzer o feedback elettrico. Il simulatore UI è separato e produce dati sintetici nel browser.

ROI/layout/video selezionato sono persistenti. Contatori ed eventi sono di sessione, esportabili in JSON. Errori visione lasciano il backend disponibile. Il comando Riprova riavvia il video selezionato.
