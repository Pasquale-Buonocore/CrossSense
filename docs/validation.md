# Piano demo e validazione

Le prove seguenti sono da eseguire dopo l'implementazione. La diagnostica dello scaffold non costituisce una validazione delle funzioni AI o semaforiche.

| Scenario | Risposta attesa | Misure |
| --- | --- | --- |
| Attraversamento normale A → B e B → A | Segnalazione continua e un conteggio per transito completo | Errori conteggio/direzione, latenza di attivazione |
| Pedone fermo sulle strisce | Occupazione mantenuta; rosso veicoli durante lo sgombero | Spegnimenti anticipati, durata protezione |
| Gruppo e direzioni opposte | Segnalazione fino all'ultima uscita | Conteggio per persona, cambi di ID |
| Persona che torna indietro | Nessun attraversamento completo inventato | Conteggi errati e eventi di ritorno |
| Attraversamento lento / immobilità / possibile caduta | Protezione e avviso secondo regole validate | Falsi positivi/negativi, ritardo allerta |
| Traffico variabile e pedoni in attesa | Adattamento entro limiti configurati | Attesa media/massima, rispetto delle fasi |
| Veicolo verso un possibile conflitto | Allerta separata dalla fase semaforica | Errore velocità calibrata, latenza, falsi allarmi |
| Video perso, tracking incerto o Bridge interrotto | Nessuna riapertura basata su osservazioni mancanti | Tempo di rilevamento guasto, stato delle uscite |
| Riavvio senza Internet | Risorse disponibili localmente | Avvio riuscito e funzioni operative |

## Metodo

1. Usare riprese del plastico e video con permesso/licenza documentati. Etichettare ingressi, uscite, direzioni e occupazione delle strisce.
2. Confrontare eventi previsti e annotazioni. Separare i dati usati per tarare soglie da quelli usati per la valutazione finale.
3. Misurare FPS e latenza end-to-end sulla UNO Q, inclusa la conferma MCU; riportare mediana e percentile 95, versione e condizioni di prova.
4. Valutare la continuità: tempo di occupazione coperto dalla segnalazione e numero/durata degli spegnimenti anticipati.
5. Per velocità e arresto, registrare calibrazione geometrica, distanze reali e ipotesi di reazione/frenata. Il tempo al conflitto richiede traiettorie compatibili, non la sola distanza dalla camera.
6. Registrare risultati aggregati in `data/runs/`; condividere nel repository solo report privi di dati personali. Ogni soglia va indicata come scelta sperimentale del prototipo.

La simulazione in Unity può fornire scenari ripetibili, ma non prova da sola la qualità del riconoscimento su immagini reali. Per il pitch mostrare separatamente prove simulate, video reali e prove fisiche.
