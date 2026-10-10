# Contratto Linux-STM32: proposta semplice

Il riferimento da concordare è [Bridge v1: un solo scambio](bridge-v1.md). Questa revisione sostituisce la precedente specifica funzionale v0.2 e la proposta con più RPC. L’adapter Linux/dashboard è implementato in `dashboard/rt.py`; il ricevitore STM32 è implementato in `firmware/sketch/rt_protocol.h` in modalità protetta; la macchina semaforica resta da implementare.

```text
Linux -> crosssense_update(frame_json) -> STM32
Linux <- stato corrente in JSON       <- STM32
```

## Responsabilità

| Componente | Responsabilità |
| --- | --- |
| Gaetano / visione Linux | Camera, detection, tracking, ID persistenti, ROI, coordinate calibrate e validità della scena |
| Pasquale / STM32 | Storico, velocità, direzione, rischio, richieste, macchina a stati, attuatori e watchdog |
| Matteo / adapter e dashboard | Unico servizio Bridge, invio dell'ultimo frame, cache della telemetria, video, conteggi completati, statistiche e storico allarmi |

Il servizio Bridge e il loop STM32 funzionano anche con dashboard chiusa. Linux invia osservazioni e richieste; la MCU decide le fasi.

## Dati minimi

Linux invia identificatore del flusso, numero del frame, timestamp ed età dell'immagine, validità, stato attraversamento/avvicinamento, tracce e tre richieste booleane. Una traccia contiene solo ID, classe, zona e x/y in mm; coordinate null indicano posizione metrica indisponibile. Permanenza nelle ROI e stime cinematiche sono derivate dalla MCU.

STM32 restituisce esito dell'invio, frame effettivamente applicato, fase, residuo, luci, buzzer, lampeggiatore, validità delle osservazioni, guasto, allarmi attivi e stime veicolari. La dashboard ricava velocità/direzione dalle componenti restituite. Non sono previsti apertura separata, ticket, paginazione, storico eventi MCU o comandi diretti ai GPIO.

## Vincoli iniziali

- Una sola RPC in volo, un frame completo applicato atomicamente, nessuna coda di immagini vecchie.
- Massimo **8 tracce, 5 Hz, 900 byte JSON** per richiesta/risposta. Le 32 tracce sono un obiettivo futuro da verificare sul trasporto.
- Deadline osservazioni **1000 ms** comprendendo l'età dell'immagine; budget di consegna **250 ms** da garantire/verificare. Senza limite affidabile sul trasporto, una risposta tardiva non prova la freschezza.
- Unknown, frame invalidi, tracce troncate e timeout non significano strisce libere. L'occupazione prevale sul conteggio e sulle priorità.
- Un nuovo flusso azzera lo storico; un duplicato non rinnova il watchdog. Le richieste manuali sono livelli con rilevamento false -> true, senza ID di comando o RPC aggiuntive.

Formato completo, esempi, errori e criteri di prova sono nel [documento Bridge](bridge-v1.md). Mappa pin, tempi semaforici e soglie del rischio vengono definiti nei requisiti STM32.
