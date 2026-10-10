# CrossSense

**HackTurin · Challenge 1 — GOMA: Smart Crossing · Arduino UNO Q**

CrossSense è un prototipo di attraversamento intelligente con computer vision e AI locale. Una camera fissa osserva le strisce, le zone di attesa e la strada di avvicinamento dei veicoli; il sistema collega ciò che rileva alla gestione del semaforo e alla segnalazione luminosa.

## La proposta

La proposta sviluppata per la Challenge 1 combina tre funzioni:

1. **Gestione adattiva del semaforo:** rilevare i pedoni in attesa, contare i veicoli e regolare le fasi in base al traffico e all'attesa accumulata, entro limiti prestabiliti.
2. **Protezione durante lo sgombero:** quando il pedonale torna rosso, mantenere il rosso ai veicoli che incrociano l'attraversamento finché qualcuno è ancora sulle strisce, anche se procede lentamente o si ferma.
3. **Allerta anticipata:** stimare velocità e traiettorie dei veicoli, tempo al possibile conflitto e spazio di arresto con una camera calibrata. Nel prototipo, un rosso lampeggiante rivolto verso l'attraversamento e punti luminosi lungo la strada richiamano l'attenzione in caso di rischio o possibile difficoltà del pedone.

L'accessibilità si basa su segnali osservabili: attraversamento lento, immobilità, possibile caduta e ausili visibili, ove supportati dal modello. Età e disabilità non vengono dedotte dall'immagine. Velocità, conflitti e spazio di arresto sono **stime**, da verificare con calibrazione e prove controllate.

## Requisiti della challenge

| Requisito condiviso dal team | Risposta prevista di CrossSense |
| --- | --- |
| Riconoscere le categorie di utenti | Pedoni, biciclette, veicoli; eventuali classi per ausili visibili da validare |
| Attivare la segnalazione luminosa | Luci presso le strisce e lungo la strada di avvicinamento |
| Contare attraversamenti e direzioni | Tracking con ingressi/uscite, conteggi per direzione e gestione dei ritorni |
| Funzionare senza Internet | Inferenza, logica e controllo locali; modelli e dipendenze disponibili sulla scheda |

Questa sintesi riprende la descrizione elaborata dal team, senza presentarla come trascrizione del bando ufficiale. Dettagli e speech: [Challenge 1](docs/challenge-1.md).

## Stato del progetto

Il repository contiene la **base di sviluppo**, non ancora l'algoritmo di attraversamento. Sono presenti la struttura Arduino App Lab, un controllo locale della configurazione e uno sketch con un endpoint Bridge diagnostico. Camera, inferenza, tracking, conteggi, controllo semaforico, GPIO e stime del rischio sono da implementare. Importazione App Lab, compilazione dello sketch e funzionamento su UNO Q richiedono verifica sulla scheda.

## Architettura su UNO Q

- **Linux / Python, Qualcomm Dragonwing QRB2210:** acquisizione immagini, inferenza, tracking, zone, politica adattiva e statistiche locali.
- **MCU STM32U585 / sketch Arduino:** controllo delle uscite, vincoli sulle combinazioni delle luci e gestione della perdita di comunicazione.
- **Bridge RPC:** collegamento locale tra Python e sketch, con comandi e risposte espliciti.

La separazione Python/sketch segue il [formato ufficiale delle app Arduino](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md). Vedi [architettura](docs/architecture.md) e [protocollo Bridge](docs/bridge.md).

## Struttura

```text
CrossSense/
├── app.yaml                    # Manifest Arduino App Lab
├── python/
│   ├── main.py                 # Avvio e diagnostica Bridge
│   ├── requirements.txt        # Dipendenze aggiuntive
│   └── crosssense/             # Moduli Python del progetto
├── sketch/
│   ├── sketch.ino              # Entry point MCU UNO Q
│   └── sketch.yaml             # Profilo Arduino Zephyr
├── config/crossing.example.json
├── docs/                       # Challenge, setup, architettura, demo, roadmap
├── hardware/                   # Cablaggio e distinta componenti
├── models/                     # Provenienza e requisiti dei modelli
├── data/                       # Manifest dei dati; video e risultati esclusi da Git
└── .github/                    # Controlli automatici e template PR
```

## Avvio rapido sul PC

Richiede Python 3.10 o successivo; il controllo non usa librerie Arduino né hardware:

```sh
python python/main.py --check
python -m compileall -q python
```

Il primo comando valida la configurazione di esempio e mostra lo stato dello scaffold. Non esegue inferenza e non aziona luci.

## Avvio su Arduino UNO Q

1. Collegare UNO Q con un cavo USB-C dati e aprire Arduino App Lab.
2. Importare l'app secondo la modalità disponibile nella versione installata, oppure creare un'app e copiarvi `app.yaml`, `python/`, `sketch/` e `config/`, mantenendo i percorsi. Questi quattro elementi costituiscono l'app minima.
3. Avviare l'app: Python interroga ogni secondo `crosssense_status`; lo sketch risponde `scaffold_ready`. Nessun pin esterno viene pilotato.
4. Seguire [setup UNO Q](docs/setup-uno-q.md) per passare alla camera, al modello locale e alle uscite del plastico.

Installazione e download iniziali possono richiedere Internet. Il funzionamento offline va dimostrato dopo aver predisposto tutte le risorse locali.

## Demo e obiettivi

La demo dovrà mostrare un attraversamento normale, una persona ferma sulle strisce, persone in direzioni opposte, traffico variabile e un veicolo in avvicinamento a un possibile conflitto. Misureremo conteggi, direzioni, attese, latenza, falsi allarmi e continuità della protezione. Piano: [validazione](docs/validation.md); priorità: [roadmap](docs/roadmap.md).

Il progetto è destinato al plastico e a prove controllate per l'hackathon. L'integrazione con impianti stradali reali non fa parte di questa base.

## Collaborare

Usare branch brevi come `feature/tracking` o `docs/demo`, aprire una PR e indicare cosa è verificato sul PC e cosa sulla scheda. Vedi [CONTRIBUTING.md](CONTRIBUTING.md). Il materiale CAD già prodotto dal team può essere aggiunto in `hardware/cad/` dopo aver verificato cablaggio e adattamento alla UNO Q.
