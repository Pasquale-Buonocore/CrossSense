# Controller logico CrossSense

`sketch/sketch.ino` registra `crosssense_update(String) -> String` con `provide_safe`. Il controller attivo è `CrossSense::RTCore` in `rt_protocol.h`, con `StandardCycle` in `standard_cycle.h`.

Il firmware non configura GPIO e non interagisce con LED, buzzer o oggetti fisici. I segnali logici sono visualizzati nella dashboard. Abilitare con `--controller-cycle` nel packaging; `--standard-cycle` aggiunge la prova sintetica. La compilazione senza flag conserva la modalità protetta per i test.

Tempi, comportamento e recupero sono descritti nel [documento di architettura](../docs/architecture.md). La permanenza nelle attese genera richieste automatiche; accessibilità prolunga il verde pedonale e priorità simulata mantiene temporaneamente il verde veicolare senza interrompere sgombero o protezione.

`crosssense_types.h` e `crosssense_config.h` sono riferimenti preliminari: non configurano il runtime attivo. `docs/history.md` e le guide precedenti sono materiale storico.

Il profilo usa core Zephyr 1.0.0, ArduinoJson 7.4.3 e RouterBridge locale con buffer RPC 1024 / stack 4096. Lo stesso sketch è compilabile sul PC con `scripts/build_native.py`, sostituendo solo Arduino/Bridge con stub e senza duplicare la FSM.
