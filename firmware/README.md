# CrossSense HackTurin Demo

CrossSense è una demo per Arduino UNO Q dedicata agli attraversamenti pedonali intelligenti. Due replay MP4 vengono elaborati localmente con YOLO e ByteTrack; le osservazioni raggiungono tramite Bridge il controller logico sulla STM32 e vengono presentate in una dashboard web.

## Cosa vedrai

- Il replay selezionato con riquadri, classi e confidenza delle rilevazioni.
- Quattro zone configurabili: attesa sinistra, attraversamento, attesa destra e corsia veicoli.
- Semafori logici per veicoli e pedoni, fase corrente, tempo residuo e protezioni.
- Persone in attesa, attraversamenti osservati, direzione, attesa media ed eventi della sessione.
- Stato del collegamento tra Linux e STM32, inclusi timeout e allarmi.

## Come avviare la demo

1. Premi **RUN** in Arduino App Lab.
2. Apri la dashboard esposta dalla porta **8080**.
3. Lascia la sorgente su **Replay / Controller**.
4. Scegli un file dal menu **Video simulazione**. La selezione da sola non avvia il replay.
5. Premi **Play** per iniziare.

All'avvio non viene selezionato né riprodotto alcun video. CrossSense prepara YOLO in background e mostra nel frame le istruzioni **Seleziona un video** e **Premi Play**. Il controller rimane in stato protetto finché non arrivano osservazioni valide. Alla fine del file il replay si ferma e può essere riavviato con Play.

## Cosa puoi fare

- **Play**: avvia il video scelto o riprende dopo una pausa.
- **Pausa**: sospende il replay; le osservazioni scadono e il controller torna protetto.
- **Stop / Riavvolgi**: ferma il replay e lo riporta all'inizio.
- **Configura zone YOLO**: ridisegna e salva i poligoni direttamente sul frame.
- **Richiesta pedonale**: invia una richiesta manuale al controller.
- **Tempo accessibile**: richiede un verde pedonale esteso.
- **Priorità veicoli simulata**: mantiene temporaneamente il verde veicolare nei limiti del controller.
- **Posiziona semafori**: cambia soltanto la posizione grafica degli indicatori.
- **Esporta dati**: salva lo stato e le metriche disponibili della sessione.

Anche senza un clic manuale, una persona o bicicletta osservata nella zona di attesa per 800 ms genera una richiesta automatica. I due semafori pedonali condividono lo stesso stato logico.

## Profilo della demo

- Video inclusi: `fotoRealVideo.mp4` e `postProcessingVideo.mp4`.
- Asset video: lato massimo 480 pixel, circa 480×322 per questi replay.
- Detector: YOLO26n NCNN esportato nativamente a 320×320.
- Confidenza: 0,15; due thread NCNN.
- Controller: macchina a stati C++ sulla STM32, osservazioni via RouterBridge.
- Uscite: semafori mostrati nella dashboard; nessun GPIO o attuatore fisico.

## Cosa non dimostra

I video sono preregistrati: le persone e i veicoli ripresi non reagiscono ai semafori calcolati. La demo non usa una camera live, non controlla un impianto stradale reale e non costituisce una certificazione di sicurezza o accuratezza. Il controller e il watchdog usano tempo reale; le statistiche delle traiettorie usano il tempo del video.

Se compare **Controller disconnesso**, controlla lo stato del Bridge e dello sketch STM32. Se compare **Osservazioni obsolete**, verifica che il replay sia in Play e che YOLO stia producendo nuovi frame.
