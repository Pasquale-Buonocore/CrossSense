# Visione replay

Percorso: MP4 locale → YOLO26n → ByteTrack → ROI → osservazioni Bridge e metriche. Avvio, dipendenze e packaging: [README](../README.md); contratti e regole: [architettura](../docs/architecture.md).

Il catalogo è esplicito (`--video-dir`), la sorgente singola usa `--video`. Senza queste opzioni la visione non parte. Profilo corrente UNO Q: video entro 480×480, inferenza 320×320, NCNN a due thread. Il modello deve essere esportato a 320 e locale. Nessun download/installazione automatica nel worker. Risultati e limiti in [collaudo UNO Q](../docs/unoq-validation.md).

ROI normalizzate modificabili nella dashboard: attesa sinistra, attraversamento, attesa destra, avvicinamento. Salvataggio con revisione, cambio stream e scarto dei risultati già in elaborazione. Riavviare o cambiare video resetta tracker e traiettorie parziali; i contatori di sessione restano.

Confidence 0.15 nel pacchetto UNO Q (default CLI 0.30 se omessa), IoU 0.50, classi COCO 0/2/7 (pedone, auto, camion). La classe camion mostra l’etichetta `AMBULANZA`; resta un veicolo nel protocollo e non attiva automaticamente una priorità. Più di 8 tracce o tracking incompleto invalidano lo snapshot RT. Le coordinate metriche sono null. Le metriche di attraversamento e immobilità sono implementate in `events.py`, con tempo del video distinto dal tempo reale del watchdog. Un veicolo senza ID invalida la decisione RT, senza cancellare le traiettorie pedonali osservate; gli ID sconosciuti vengono ignorati e le singole traiettorie perse scadono dopo 1,5 s video.

Fine video, errore e stop pubblicano indisponibilità. Il server resta raggiungibile; “Riprova / Riavvia replay” riparte dalla sorgente selezionata dopo aver risolto un errore. Il modello viene ricaricato al riavvio del worker.

Test: `python -B -m unittest discover -s vision/tests`; prova reale completa: `scripts/check_replays.py`. I test con mock non misurano accuratezza. I cinque video sono sintetici e non costituiscono un dataset annotato di validazione.

La confidenza effettiva è esposta in `/api/vision` nel campo `confidence`. Il catalogo sostituito in questa chat contiene `fotoRealVideo.mp4` e `postProcessingVideo.mp4`, preparati a 480×322, con inferenza 320×320 e soglia 0.15. I video precedenti sono conservati nel backup dell’app.
