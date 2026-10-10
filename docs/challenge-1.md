# Challenge 1 — GOMA: Smart Crossing

## Contesto condiviso

Questa pagina raccoglie la proposta CrossSense elaborata dal team nella conversazione «Riepiloga la traccia 1», aggiornata il 10 ottobre 2026. È una sintesi di progetto; il testo ufficiale del bando resta da allegare se necessario.

Requisiti condivisi: riconoscere categorie di utenti, attivare segnalazioni luminose, contare attraversamenti e direzioni, funzionare senza Internet.

## Speech di progetto

Proponiamo **CrossSense**, un sistema di attraversamento intelligente che utilizza l'AI offline per adattare il semaforo al traffico e contribuire alla sicurezza dei pedoni.

La camera osserva le strisce, le zone di attesa e la strada da cui arrivano i veicoli. Il sistema riconosce le categorie di utenti — pedoni, biciclette, veicoli e ausili visibili — conta gli attraversamenti e ne distingue la direzione.

La proposta combina tre funzioni. La prima è la **gestione adattiva del semaforo**: rileviamo i pedoni in attesa, contiamo i veicoli e regoliamo i tempi in base al traffico e all'attesa accumulata, entro limiti prestabiliti.

La seconda è la **protezione durante lo sgombero**. Se il pedonale torna rosso ma qualcuno è ancora sulle strisce, manteniamo il rosso per i veicoli che ne incrociano il percorso, considerando chi procede lentamente, si ferma o ha bisogno di più tempo.

La terza è l'**allerta anticipata sul rischio**. Con una camera calibrata stimiamo velocità e traiettorie dei veicoli, tempo al possibile conflitto con un pedone e spazio di arresto, considerando parametri di reazione e frenata. Se il rischio supera una soglia, nel prototipo attiviamo un segnale rosso lampeggiante orientato verso l'attraversamento. Punti luminosi distribuiti lungo la strada avvisano inoltre i conducenti in avvicinamento.

Realizzeremo il sistema su Arduino UNO Q, con elaborazione locale e funzionamento senza Internet. La demo mostrerà traffico variabile, pedoni ancora sulle strisce e un veicolo in avvicinamento a una situazione critica. Misureremo attese, conteggi, tempi di risposta, falsi allarmi e continuità della protezione.

**CrossSense collega percezione, gestione del traffico e segnalazione anticipata in un unico prototipo misurabile.**

## Confini della proposta

- La camera deve inquadrare tutte le zone utili: posizione e campo visivo vanno provati prima di scegliere il modello.
- Le classi per carrozzine o altri ausili richiedono modello e dati dedicati; non sono garantite da un rilevatore generico.
- Immobilità e possibile caduta sono segnali da validare, non diagnosi.
- Velocità, tempo al conflitto e spazio di arresto richiedono geometria calibrata e ipotesi esplicite. Senza calibrazione, non mostrare valori in m/s o metri.
- Le funzioni di questo speech descrivono il risultato previsto, non capacità già implementate nello scaffold.
