# Architettura CrossSense

## Divisione del lavoro su Arduino UNO Q

| Componente | Responsabilità prevista |
| --- | --- |
| Linux / Python | Camera, inferenza locale, tracking, ROI, calibrazione, conteggi e dashboard |
| MCU / sketch Arduino | Stima cinematica da posizioni valide, rischio, macchina a stati, priorità, luci, watchdog e protezione |
| Bridge RPC | Snapshot delle osservazioni da Python, richieste e telemetria dello stato MCU |

```text
Camera → detection → tracking → ROI / coordinate calibrate
                                      ↓ Bridge: osservazioni
                             MCU: rischio e macchina a stati
                                      ↓
                                luci del plastico
                                      ↓ Bridge: telemetria
                              Linux: dashboard e statistiche
```

La base attuale implementa solo la diagnostica: Python chiama `crosssense_status`, registrato nello sketch, e riceve `scaffold_ready`. Non esegue AI e non pilota GPIO. Riferimento: [Arduino RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge).

## Regole da implementare

- Distinguere zone di attesa, strisce e strada di avvicinamento; contare i transiti completi per direzione e gestire i ritorni.
- Prevedere fasi veicoli, transizione, attraversamento pedoni e sgombero. Durante lo sgombero, mantenere il rosso ai veicoli finché le strisce risultano occupate.
- Tenere l'allerta lampeggiante separata dalle fasi semaforiche.
- La perdita di video, tracking o Bridge non equivale a strisce libere. Definire avvio, timeout di comunicazione e stato di guasto prima di attivare le uscite.
- Eseguire inferenza e controllo localmente; conservare per default eventi e statistiche, senza archiviazione continua del video.

## Decisioni ancora aperte

Camera confermata: IMX219 su CAM0 di UNO Media Carrier, acquisizione e Bridge verificati con `apps/crosssense-env`. Restano aperti campo visivo, modello e classi effettive; pin, driver e alimentazione delle luci; limiti delle fasi e soglie di allerta. Calibrare la geometria prima di mostrare velocità in m/s o distanze in metri. Annotare le versioni App Lab/core e le prestazioni misurate sulla variante UNO Q disponibile.

Aggiungere moduli, dipendenze e nuovi documenti quando servono all'implementazione. Per le prove confrontare video annotati e comportamento del plastico, includendo pedoni fermi, gruppi, traffico variabile e perdita della comunicazione.

Vedi [revisione tecnica](technical-review.md), [contratto delle osservazioni](../protocol/README.md) e [piano del team](team-plan.md). La diagnostica in radice e l’app di prova hardware sono scaffold; la macchina a stati deve ancora essere implementata.
