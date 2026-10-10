# Architettura prevista

## Catena di elaborazione

```text
Camera / video di prova
        ↓
Linux: rilevamento → tracking → zone e attraversamenti
        ↓
Linux: politica semaforica + valutazione del rischio
        ↓ Bridge RPC locale
MCU: validazione del comando → controllo luci del plastico
        ↓
Conferma dello stato applicato → statistiche locali
```

Il runtime Python e lo sketch sono organizzati secondo il [formato Arduino App Lab](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md). La UNO Q combina [Linux e MCU](https://docs.arduino.cc/hardware/uno-q/); i due lati comunicano con [RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge).

## Moduli da sviluppare in python/crosssense/

| Modulo previsto | Responsabilità |
| --- | --- |
| perception | Acquisizione, inferenza locale e qualità delle rilevazioni |
| tracking | Identificativi temporanei e traiettorie di pedoni/veicoli |
| crossing | Zone di attesa/strisce, occupazione, ingressi, uscite e direzioni |
| controller | Tempi adattivi e transizioni della macchina a stati |
| risk | Stime calibrate di velocità, conflitto e arresto |
| telemetry | Eventi, metriche e risultati aggregati |
| bridge | Comandi, heartbeat e conferma dello stato MCU |

Sono responsabilità progettate: nella base iniziale è implementato soltanto `config.py`.

## Macchina a stati da implementare

| Stato | Veicoli | Pedoni | Condizione di uscita |
| --- | --- | --- | --- |
| VEHICLE_FLOW | Verde | Rosso | Richiesta pedoni e tempo minimo veicoli completato |
| VEHICLE_CLEARANCE | Giallo, poi rosso | Rosso | Tempo di transizione completato |
| PEDESTRIAN_CROSSING | Rosso | Verde | Durata pedonale prevista completata |
| PEDESTRIAN_CLEARANCE | Rosso | Rosso | Strisce libere per una finestra stabile di conferma |
| FAULT | Stato di guasto del plastico da definire | Rosso | Ripristino verificato e transizione esplicita |

L'allerta lampeggiante è un'uscita separata dalle fasi, così non abilita il verde veicoli. La perdita del video/tracking o della comunicazione non deve essere interpretata come strisce libere. Non introdurre un timeout che riapra automaticamente ai veicoli durante un'occupazione incerta; passare a una condizione di guasto definita per la demo.

I limiti delle fasi, il timeout heartbeat, l'isteresi e le soglie saranno configurati dopo misure sul plastico. Nessun valore operativo è deciso nello scaffold.

## Dati e offline

Usare un clock monotono per durate e latenza. Tenere gli identificativi di tracking nella sessione; conservare per default solo eventi e aggregati. Video di test e pesi restano locali, con manifest della provenienza. Non usare servizi cloud nel percorso di rilevamento e attuazione.
