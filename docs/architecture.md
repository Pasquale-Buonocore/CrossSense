# Architettura CrossSense

## Divisione del lavoro su Arduino UNO Q

| Componente | Responsabilità prevista |
| --- | --- |
| Linux / Python | Camera, inferenza locale, tracking, conteggi, tempi adattivi e stime del rischio |
| MCU / sketch Arduino | Luci del plastico, controllo delle combinazioni consentite e gestione della perdita di comunicazione |
| Bridge RPC | Comandi da Python e conferma dello stato applicato dal MCU |

```text
Camera → rilevamento → tracking → stato dell'attraversamento
                                        ↓
                          decisione su fasi e allerte
                                        ↓ Bridge
                              MCU → luci del plastico
```

La base attuale implementa solo la diagnostica: Python chiama `crosssense_status`, registrato nello sketch, e riceve `scaffold_ready`. Non esegue AI e non pilota GPIO. Riferimento: [Arduino RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge).

## Regole da implementare

- Distinguere zone di attesa, strisce e strada di avvicinamento; contare i transiti completi per direzione e gestire i ritorni.
- Prevedere fasi veicoli, transizione, attraversamento pedoni e sgombero. Durante lo sgombero, mantenere il rosso ai veicoli finché le strisce risultano occupate.
- Tenere l'allerta lampeggiante separata dalle fasi semaforiche.
- La perdita di video, tracking o Bridge non equivale a strisce libere. Definire avvio, timeout di comunicazione e stato di guasto prima di attivare le uscite.
- Eseguire inferenza e controllo localmente; conservare per default eventi e statistiche, senza archiviazione continua del video.

## Decisioni ancora aperte

Camera e campo visivo; modello e classi effettive; pin, driver e alimentazione delle luci; limiti delle fasi e soglie di allerta. Calibrare la geometria prima di mostrare velocità in m/s o distanze in metri. Annotare le versioni App Lab/core e le prestazioni misurate sulla variante UNO Q disponibile.

Aggiungere moduli, dipendenze e nuovi documenti quando servono all'implementazione. Per le prove confrontare video annotati e comportamento del plastico, includendo pedoni fermi, gruppi, traffico variabile e perdita della comunicazione.
