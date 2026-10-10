> Documento storico. Il perimetro corrente è replay dichiarato e segnali soltanto nella dashboard. Riferimenti aggiornati: README principale e docs/architecture.md. Le affermazioni di verifica sotto riportate appartengono alle prove precedenti.

# Revisione tecnica CrossSense

10 ottobre 2026 — valutazione del prototipo per un hackathon di 30 ore.

## Giudizio

La separazione Linux/STM32 è appropriata e l'MVP è plausibile, ma la fattibilità della visione live è ancora da dimostrare. Camera, modello e latenza end-to-end sono i primi vincoli. La protezione MCU resta deterministica, ma dipende dalla qualità delle osservazioni: un watchdog non risolve una falsa dichiarazione di attraversamento libero.

Arduino documenta Linux QRB2210, STM32U585 con Zephyr, Bridge RPC e connettori ad alta velocità per carrier MIPI. La presenza dei connettori non garantisce compatibilità con qualsiasi sensore. Fonti: [UNO Q](https://docs.arduino.cc/hardware/uno-q/), [manuale](https://docs.arduino.cc/tutorials/uno-q/user-manual/), [UNO Media Carrier](https://docs.arduino.cc/resources/datasheets/ASX00083-datasheet.pdf).

## 1. Camera e campo visivo

Acquisizione validata su IMX219 collegata a CAM0 di UNO Media Carrier. Abilitato il DTB installato per Camera v2/IMX219 e riavviata la UNO Q. CAMSS espone il media graph; libcamera ha acquisito tre frame a 632×480 ABGR8888, anche come utente arduino dopo una regola udev limitata al DMA heap system. Dettagli riproducibili in [environment.md](environment.md).

La prova conferma il collegamento e l’acquisizione; non dimostra ancora stabilità prolungata, prestazioni AI o accesso dalla futura app containerizzata. Libcamera usa software ISP e configurazione uncalibrated; esposizione e colore richiedono verifica.

Una singola camera deve vedere entrambe le attese, tutte le strisce e un tratto sufficiente di avvicinamento per ogni direzione. Ostacoli e veicoli grandi possono occultare pedoni. Provare l'inquadratura sul plastico/scena reale prima di definire le ROI. Se una ROI critica è coperta o il frame è troppo scuro, lo stato deve essere unknown.

Percorso di riserva: video locale preregistrato, stesso detector/tracker e contratto MCU. I risultati della demo vanno etichettati live, replay o simulati. Nel percorso offline finale nessun telefono/cloud è una dipendenza necessaria.

## 2. AI locale e memoria

La scheda verificata dispone di 3,6 GiB RAM utilizzabili dal sistema e circa 2,1 GiB di disco liberi prima della prova di compilazione. Non installare indiscriminatamente PyTorch e più runtime: prima scegliere tra runtime già presente App Lab e modello YOLO piccolo con runtime leggero compatibile con ARM64. Nessuna accelerazione hardware va data per acquisita.

Benchmark: frame 320/416/640, inferenza batch 1, numero tracce, RSS, temperatura, FPS, p50/p95 acquisizione→decisione MCU, frame scartati e intervalli senza osservazioni valide. Un singolo worker acquisisce la camera e conserva solo il frame più recente; la dashboard legge copie ridotte. Evitare che encoding video o log rallentino inferenza e invio.

Il requisito YOLO va mantenuto se il benchmark lo consente. Un modello preinstallato diverso è una proposta di ripiego da concordare, non una sostituzione già decisa. Prima della demo offline: pesi, immagini container e dipendenze già scaricati, poi verifica del funzionamento senza Internet.

## 3. Semaforo: separare ammissione e sgombero

Stati proposti: VEHICLE_GREEN → VEHICLE_YELLOW → ALL_RED_TO_PED → PED_GREEN → PED_CLEARANCE → ALL_RED_TO_VEH → VEHICLE_GREEN. Aggiungere PROTECTED_STOP e FAULT.

- PED_GREEN consente nuovi ingressi; durata ordinaria min/max adattabile.
- PED_CLEARANCE chiude i nuovi ingressi (rosso pedoni) e mantiene rosso veicoli finché le strisce non risultano libere in modo stabile. Se si visualizza un giallo pedonale nella demo, definirne esplicitamente il significato; non usarlo come permesso ambiguo di ingresso.
- Occupazione persistente oltre il massimo di sgombero → PROTECTED_STOP + allarme, senza timeout che liberi le auto.
- UNKNOWN o osservazioni scadute → fase di arresto prudente; se i veicoli hanno il verde e non c'è conflitto immediato, usare giallo di chiusura e poi tutto rosso. Un conflitto occupato attiva subito l'allarme; la politica di arresto viene verificata sul prototipo.
- Nessuna coppia di verdi conflittuali, anche durante boot, reset e variazione parametri. Definire uscite di boot e protezione elettrica per il reset MCU.
- Il ritorno da guasto richiede osservazioni valide e libere per una finestra continua e una transizione tutto rosso; decidere quali guasti richiedono riarmo manuale.

La MCU decide le fasi; Linux propone osservazioni e richieste. Nessun `delay()` lungo nel controller finale. Loop temporizzato, buffer limitati, nessuna allocazione senza limiti. I callback RPC devono depositare snapshot e terminare rapidamente; verificare il modello di concorrenza Bridge prima di condividere dati con il loop.

## 4. Priorità e tempi

Filtrare le attese con permanenza nella ROI per evitare richieste da passanti. Il timer di attesa sopravvive a brevi perdite di ID. Con veicoli presenti, rispettare verde minimo veicolare; con avvicinamento validamente libero, avviare prima la sequenza giallo/tutto rosso, senza saltare le transizioni.

Il massimo di attesa pedonale limita la durata del verde veicolare quando esiste una richiesta persistente. Il verde pedonale ordinario limitato protegge la disponibilità al traffico, ma non può limitare la protezione di una persona ancora sulle strisce. Le richieste manuali vengono memorizzate; il pulsante accessibile aggiunge il segnale acustico. Debounce e antiripetizione degli allarmi.

Un veicolo di emergenza diventa una richiesta prioritaria, mai un comando diretto di verde. Identificarlo solo visivamente è fragile: nel MVP usare un ingresso/scenario esplicito, mantenendo il riconoscimento automatico opzionale.

## 5. Rischio di collisione

La formula proposta è utilizzabile nella demo con v in m/s, reazione in s e decelerazione positiva in m/s². Confrontare la distanza lungo la traiettoria verso le strisce, non una semplice distanza euclidea. TTC solo per veicoli in avvicinamento, con velocità valida e componente verso il conflitto positiva. Velocità in allontanamento o quasi zero non produce TTC attendibile.

Usare margine, età del frame, errore di calibrazione e isteresi. L'allarme scatta quando il percorso interseca l'attraversamento occupato e distanza/TTC indicano rischio. Non richiedere che più criteri indipendenti siano tutti veri se ciò ritarda un allarme conservativo. Senza calibrazione, mantenere protezione e segnalazione di conflitto per ROI, marcando il rischio metrico come non disponibile.

Una omografia sul piano stradale richiede camera fissa, correzione distorsione e punti di riferimento misurati. Estimare velocità su uno storico filtrato a timestamp di acquisizione, non di arrivo RPC. Reset storico dopo cambio ID/sessione/calibrazione; salto impossibile → stima invalida. Il lampeggiatore è una segnalazione sperimentale, non un dispositivo che arresta fisicamente i veicoli.

## 6. Statistiche e dashboard

Conteggi completati tramite traiettoria con ingresso/uscita e direzione, deduplicati per ID. Separare contatori di occupazione dai conteggi di completamento. L'attesa dei veicoli richiede una ROI e tracking della coda: con la sola zona di avvicinamento non è misurabile in modo affidabile.

Velocità media: segmenti calibrati e validi, con criterio esplicito per escludere l'accelerazione iniziale; non eliminare velocità basse reali. Registrare eventi e latenza; contare episodi di allarme, non ogni frame. Dashboard in sola lettura per MVP. Indicare stato obsoleto quando non arriva telemetria.

## 7. Test richiesti prima della demo

1. Richiesta automatica e manuale con/senza veicoli, verde minimo e attesa massima.
2. Pedone lento/fermo oltre la scadenza: auto sempre rosse.
3. Ingresso sulle strisce con verde auto: allarme e transizione prevista.
4. Frame vecchio, duplicato, fuori ordine, processo morto, camera scollegata, ROI occultata e overflow tracce.
5. Riavvio Linux/MCU, sessione nuova e recupero da FAULT senza apertura prematura.
6. Veicolo in allontanamento, ID che cambia, calibrazione assente e velocità non valida.
7. Stress dashboard/video senza degradare il ciclo MCU; nessun verde conflittuale in ogni scenario.

Confronto: stesso insieme di arrivi per ciclo fisso e CrossSense, medesimi vincoli di sicurezza e finestre di misura. Riportare attese, throughput e tempo di protezione; simulazione di conflitti non equivale a dimostrare una riduzione di incidenti reali.

## Decisioni raccomandate

Camera e Bridge sono verificati. Il prossimo passo è fissare l’inquadratura e misurare acquisizione e inferenza nella futura app prima di sviluppare in parallelo. Congelare protocollo v1, stati e criteri di clear/unknown. Prima integrazione con dati sintetici entro ora 8. Posticipare SUMO, emergenza visiva, classificazione accessibilità e video avanzato finché il ciclo completo funziona.
