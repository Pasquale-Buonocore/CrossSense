# Validazione e stato della demo

> Questo documento conserva le prove host della prima implementazione. Il profilo corrente è 480/320 e il collaudo reale della scheda è in [unoq-validation.md](unoq-validation.md); i conteggi del profilo 960/640 sotto riportati non valgono automaticamente per quello attuale.

Sessione del 10 ottobre 2026. **Percorso completo verificato sul PC: replay MP4 → YOLO reale → adapter Python → stesso sketch C++ compilato nativamente → dashboard.** Il pacchetto UNO Q è preparato, ma il nuovo software non è stato caricato o collaudato sulla scheda durante questa sessione.

## Modifiche completate

- Statistiche derivate dalla visione: attraversamenti per direzione, attesa osservata, immobilità, eventi deduplicati ed export JSON.
- ROI adatte ai replay, associazione degli ID dopo brevi interruzioni e deduplicazione persona/bicicletta sullo stesso partecipante.
- Richiesta automatica dopo permanenza, riarmo, anticipo con approach libero, richiesta accessibile e priorità veicolare simulata.
- Richieste manuali tracciate fino al servizio oppure annullate al cambio sorgente/restart; retry ACK senza creare falsi fronti.
- Stati mancanti/scaduti/errori espliciti; cambio e riavvio replay, incluso il recupero dopo asset mancante.
- Una sola FSM C++ per MCU e prove PC. Il backend non contiene una copia del controller.
- SDK Bridge isolato in un processo terminabile in caso di blocco; protocollo `crosssense_update` conservato. Nessun GPIO nella demo.
- README e architettura aggiornati; pacchetto con modello, cinque video e manifest SHA256 degli asset.

## Verifiche eseguite

| Verifica | Esito e copertura |
|---|---|
| `scripts/check_all.py` | `ALL_CHECKS_OK`: 57 test Python individuati, 56 superati e 1 saltato; quattro suite JavaScript superate; sei configurazioni C++ compilate con `-Wall -Wextra -Werror -pedantic` ed eseguite |
| Test saltato | Creazione symlink del catalogo: Windows non concede il privilegio richiesto; gli altri controlli di catalogo e percorsi sono eseguiti |
| `scripts/check_standard_cycle.py` | `HTTP_SKETCH_OK`: HTTP, richieste, due cicli completi e perdita osservazioni; `STOP_OK fault=TIMEOUT`, entrambi rossi |
| `scripts/check_replays.py --assert-counts` | `REAL_REPLAYS_OK`: tutti i 1980 frame dei cinque MP4, inferenza reale, conteggi e direzioni attesi, osservazioni accettate, nessun campione con entrambi i verdi, EOF con FAULT |
| `scripts/check_browser.cjs` | `BROWSER_OK`: browser Edge headless, startup senza modello, richiesta simulatore, disconnessione, editor ROI, assenza di eccezioni JS |
| `scripts/check_browser.cjs … replay` | `REPLAY_BROWSER_OK`: JPEG reale, quattro completamenti, selezione del secondo video, utenti in attesa, richiesta accessibile servita ed export JSON verificato; assenza di eccezioni JS |
| Trasporto | Processo bloccato terminato e riavviato; worker Bridge reale provato con SDK fittizio per handshake e isolamento dei log. **Non** equivale a una prova RPC sul router UNO Q |
| Firmware | Frame malformati/vecchi/duplicati, wrap, buffer atomico, richieste, timeout, occupazione, recupero, tempi adattivi, priorità limitata; sketch in modalità protetta e ciclo, zero chiamate GPIO |
| Packaging e sintassi | AST Python valido; ZIP integro, file di avvio presenti, ciclo abilitato e configurazione 960/640 verificata; sei asset controllati per dimensione e SHA256; `git diff --check` senza errori |
| Accesso scheda | `python -B scripts/board.py devices` termina con `ADB non trovato`: nessuna connessione alla scheda o operazione hardware eseguita |

Ambiente delle prove: Windows, Python 3.12, G++, ArduinoJson 7.4.3, Node moderno ed Edge headless. Inferenza CPU con Ultralytics 8.4.175 e pesi ufficiali locali; versioni e hash in [replay-assets.md](replay-assets.md). Il runtime ARM del pacchetto ha dipendenze specifiche e non è stato provato qui.

### Risultati dei video

Profilo: frame massimo 960 px, `imgsz=640`, confidenza 0,30, ByteTrack, ROI predefinite `replay-zones.json`. L'asserzione usa `simulation/expected-events.json`, derivato dalle traiettorie dei generatori dei video. Sono conteggi finali, non un'annotazione di ogni box o misura di precision/recall.

| Video | Frame | Sinistra → destra | Destra → sinistra | Totale | Tempo host dell'esecuzione |
|---|---:|---:|---:|---:|---:|
| `output_1.mp4` | 360 | 2 | 2 | 4 | 36,22 s |
| `output_2.mp4` | 390 | 0 | 0 | 0 | 33,52 s |
| `output_3.mp4` | 300 | 1 | 0 | 1 | 26,47 s |
| `output_4.mp4` | 510 | 2 | 1 | 3 | 47,91 s |
| `output_5.mp4` | 420 | 0 | 0 | 0 | 40,84 s |

Il quinto video include ingressi con ritorno: non completarli è il risultato atteso. Il secondo mostra attese senza attraversamenti completati. Il quarto non deve contare separatamente persona e bicicletta sovrapposte. Le durate includono startup e controllo, dipendono dal PC e non costituiscono benchmark UNO Q. Il replay elabora ogni frame e rallenta rispetto ai 30 FPS del file.

Il profilo iniziale 480/320 perdeva attraversamenti: non è stato promosso a profilo della demo. Durante prove AI concorrenti sono stati osservati timeout temporanei, visualizzati in dashboard con arresto protetto; eseguire una sola inferenza durante la presentazione. L'ultima verifica seriale ha accettato tutti i campioni validi dei cinque video. I conflitti rilevati sono compatibili con attori preregistrati che non rispettano il controller: non sono automaticamente falsi allarmi.

Report grezzo locale: `.local/replay-final-validation.json`. Screenshot ed export del browser: `.local/dashboard-smoke.png`, `.local/dashboard-replay.png`, `.local/dashboard-export.json`. Questi artefatti e il virtualenv sono esclusi da Git.

Pacchetto prodotto: `dist/crosssense-replay-dashboard.zip`, 104661422 byte; SHA256 `ff773f999060080ba3869ea030f23b399b16091f36c909d787c2cfe48a9fd814`. Anche `dist/` è esclusa da Git: distribuire lo ZIP separatamente oppure rigenerarlo con il comando nel README scegliendo una destinazione nuova. Il pacchetto contiene pesi e video; non contiene il virtualenv Windows.

## Stato rispetto agli scenari originari

| Comportamento | Stato corrente | Evidenza / limite |
|---|---|---|
| Pedoni in attesa, richiesta automatica | Implementato e testato su host | `rt_protocol.h`, `adaptive_test.cpp`; 800 ms e riarmo dopo 1 s senza attese |
| Pedone lento, protezione durante sgombero | Implementato e testato su host | `standard_cycle.h`, test ciclo; nessun rilascio veicolare su occupazione |
| Pedone fermo | Implementato con euristica visiva | `events.py`, test eventi; immobilità in dashboard e protezione/allarme di sgombero MCU |
| Pedone con verde veicolare | Implementato e osservato nei replay | `CROSSING_CONFLICT`, `PROTECTED_STOP` |
| Priorità emergenza | Implementata come richiesta simulata | Nessun riconoscimento visivo di ambulanza; non interrompe la protezione |
| Accessibilità | Richiesta esplicita e verde di 8 s | Solo rappresentazione dashboard, nessun buzzer o classificazione visiva |
| Traffico veicolare intenso | Parziale | Presenza in approach modifica il verde minimo; mancano tracking della coda e ottimizzazione basata sulla sua lunghezza |
| Veicolo che non riesce a fermarsi | Non implementata la previsione metrica | Mancano scala/calibrazione e storico metrico validato; `estimates=[]`, nessun TTC o spazio di arresto dichiarato |
| Conteggi e direzioni utenti dell'attraversamento | Implementati e verificati sui cinque replay | ID logici e sequenza A → crossing → B, senza doppio conteggio |
| Statistiche veicolari avanzate | Non implementate | Conteggio transiti, velocità e attesa in coda restano sviluppi successivi; la presenza istantanea non equivale al flusso |
| Offline | Asset locali e runtime configurato | Cold start completamente senza rete su UNO Q ancora da provare dopo installazione/build |
| Camera e attuatori | Rimossi dal percorso finale su richiesta | Nessuna interazione con hardware fisico per la demo |

Le estensioni metriche e di coda della proposta iniziale restano dichiaratamente incomplete: la semplificazione non le rende implicitamente soddisfatte. Mancano dati geometrici attendibili per attribuire valori fisici ai video sintetici.

## Collaudo minimo rimanente su UNO Q

1. Importare `dist/crosssense-replay-dashboard.zip` e compilare lo sketch Zephyr con il profilo incluso. Verificare che non siano avviate altre app diagnostiche.
2. Avviare e verificare Bridge bidirezionale `crosssense_update`, tipi e payload reali, telemetria applicata e nessun errore di SDK/processo figlio. Un limite host di 250 ms non prova il tempo di consegna alla MCU.
3. Ripetere i cinque replay al profilo 960/640: contatori 4/0/1/3/0, direzioni, nessun verde conflittuale, richieste servite, cambio sorgente ed EOF/loop. Misurare RAM, FPS, età immagini e p95 RPC; nessun frame scaduto deve essere trattato come libero.
4. Fermare inferenza/collegamento, riavviare Linux e MCU separatamente: dashboard obsoleta esplicita, annullamento richieste precedenti e recupero solo dopo osservazioni libere valide. Chiudere il browser e verificare che il controller continui.
5. Dopo aver preparato dipendenze e cache, togliere Internet ed eseguire un cold start completo, inclusi modello e pagina dashboard.

Se il profilo qualità non rientra nei tempi sulla scheda, provare prima l'export NCNN a 640 già supportato; confrontare nuovamente i conteggi. Abbassare la risoluzione senza ripetere le asserzioni reintroduce il problema osservato. Non allungare il watchdog per mascherare un'inferenza lenta senza valutare la semantica temporale.

## Cinque prossime attività concrete

1. Collaudo App Lab/Zephyr e Bridge reale del pacchetto — priorità P0, sforzo medio.
2. Benchmark UNO Q del profilo qualità e, se necessario, NCNN 640 — P0, medio.
3. Prova offline, reboot e perdita del collegamento — P1, medio.
4. Prova generale dei cinque scenari con dashboard e salvataggio risultati — P1, piccolo.
5. Annotazioni più ricche e casi aggiuntivi per occlusioni, biciclette separate e cambi ID — P2, medio; prerequisito per affermare qualità oltre i replay correnti.
