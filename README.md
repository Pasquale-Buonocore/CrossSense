# CrossSense

**HackTurin · Challenge 1 — GOMA: Smart Crossing · Arduino UNO Q**

CrossSense è un prototipo di attraversamento intelligente con computer vision e AI locale. Una camera osserva le strisce, le zone di attesa e la strada da cui arrivano i veicoli, per adattare il semaforo e attivare segnalazioni luminose.

## La Challenge 1 e la nostra proposta

La descrizione elaborata dal team prevede quattro requisiti: riconoscere le categorie di utenti, attivare le luci, contare attraversamenti e direzioni, funzionare senza Internet.

CrossSense propone di combinarli con:

- **Semaforo adattivo:** rilevare pedoni in attesa e veicoli, regolando le fasi in base al traffico e ai tempi di attesa, entro limiti prestabiliti.
- **Protezione durante lo sgombero:** mantenere il rosso ai veicoli che incrociano l'attraversamento finché qualcuno resta sulle strisce, anche quando il pedonale torna rosso.
- **Allerta anticipata:** stimare velocità, traiettorie, tempo al possibile conflitto e spazio di arresto con una camera calibrata. Un rosso lampeggiante rivolto verso l'attraversamento e luci lungo la strada segnalano situazioni critiche nel plastico.

Riconosceremo pedoni, biciclette e veicoli; eventuali classi per ausili visibili richiedono un modello adeguato. Attraversamento lento, immobilità e possibile caduta sono segnali da verificare, senza dedurre età o disabilità dall'immagine. Velocità e rischio restano stime da validare.

## Struttura essenziale

```text
CrossSense/
├── README.md
├── app.yaml                 # Manifest Arduino App Lab
├── .gitignore
├── python/
│   └── main.py              # Avvio Python e diagnostica Bridge
├── sketch/
│   ├── sketch.ino           # Sketch MCU UNO Q
│   └── sketch.yaml          # Profilo Arduino Zephyr
└── docs/
    └── architecture.md      # Architettura e decisioni tecniche
```

Python sulla parte Linux gestirà camera, AI e logica; il microcontrollore gestirà le luci. La comunicazione avviene tramite Bridge RPC. Vedi [architettura](docs/architecture.md).

## Avvio

Sul PC, con Python 3.10 o successivo:

```sh
python python/main.py --check
python -m compileall -q python
```

`--check` verifica soltanto l'avvio Python senza il runtime Arduino e senza hardware.

Sulla UNO Q:

1. Collegare la scheda con un cavo USB-C dati e aprire Arduino App Lab.
2. Importare l'app con la modalità disponibile nella versione installata, oppure creare un'app e copiarvi `app.yaml`, `python/` e `sketch/`, mantenendo i percorsi.
3. Avviare: Python interroga ogni secondo `crosssense_status`; lo sketch risponde `scaffold_ready`.

Riferimenti: [manuale UNO Q](https://docs.arduino.cc/tutorials/uno-q/user-manual/) e [formato delle app Arduino](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md). Installazione e download iniziali possono richiedere Internet; l'esecuzione offline andrà provata dopo aver predisposto le risorse locali.

## Stato e prossimi passi

È disponibile la base Arduino App Lab con diagnostica Bridge, senza GPIO attivi. Camera, AI, tracking, conteggi, controllo semaforico e stime del rischio sono da implementare. Compilazione dello sketch e funzionamento su UNO Q restano da verificare sulla scheda.

Per la demo partiremo da rilevamento → segnalazione → conteggio, poi aggiungeremo adattamento e allerte. Mostreremo un passaggio normale, un pedone fermo, direzioni opposte e un veicolo in avvicinamento, misurando latenza, falsi allarmi e continuità della protezione. Le prove si svolgeranno sul plastico e in ambiente controllato.
