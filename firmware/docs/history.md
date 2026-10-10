# Storico di sviluppo STM32

Il [piano corrente](README.md) contiene lo stato aggiornato. Le voci seguenti conservano le decisioni della sessione del 10 ottobre 2026, nell'ordine della discussione; non assegnano orari non registrati.

## 1. Piano e responsabilità

Il piano descritto nel PDF del repository è stato trasferito nel README principale come base per architettura, scenari e presentazione. Pasquale segue la parte STM32: controller autonomo, tempi, priorità, watchdog, protezione, stime e allarmi. Linux produce le osservazioni e riceve la telemetria necessaria alla dashboard.

Decisione: l'arrivo dei dati alimenta il controller; il suo loop deve continuare anche quando Linux non comunica. Il materiale di riferimento è il [README principale](../../README.md).

## 2. Semplificazione del Bridge

Su richiesta di Pasquale, la prima proposta con più chiamate è stata sostituita da una sola RPC `crosssense_update(frame_json) -> state_json`, con stringhe JSON e frame completi. La versione vigente è in [bridge-v1.md](../../protocol/bridge-v1.md).

Concordati: un servizio Linux proprietario del Bridge, una chiamata in corso, ultimo frame disponibile, invii circa 5 Hz, massimo 8 tracce e 900 byte per JSON. Stream e frame identificano flusso e ordine; valori non disponibili restano null. Il buffer MCU contiene un solo frame in attesa e distingue accettazione da applicazione.

Chiarito `requests`: livelli `[pedestrian, accessible, vehicle_priority]`, memorizzati sul fronte false -> true. La richiesta accessibile include quella pedonale; nessuna richiesta forza direttamente le uscite.

Timeout osservazioni 1000 ms e budget trasporto 250 ms restano parametri iniziali, con verifica del trasporto ancora necessaria. Non sono prestazioni hardware dimostrate.

## 3. Piano in sei step e scelta del linguaggio

Concordato l'ordine: strutture/configurazione, scambio Bridge, FSM di base, comportamento adattivo, stime/allarmi, integrazione e taratura. Il dettaglio è nel [piano](README.md).

Pasquale ha chiesto inizialmente il motivo di C++, poi ha confermato la preferenza per la soluzione più semplice con C++. Si mantiene C++11, coerente con lo sketch Arduino e RouterBridge; nessuna riscrittura in C richiesta.

## 4. Implementazione e verifica dello step 1

Creati [crosssense_types.h](../sketch/crosssense_types.h), [crosssense_config.h](../sketch/crosssense_config.h) e [step1_test.cpp](../tests/step1_test.cpp). Le strutture non dipendono da Arduino e usano capacità fisse. I dati assenti sono espliciti, distinti dallo zero; i tempi semaforici non concordati restano a zero e rendono la configurazione incompleta.

Verifica eseguita con GCC MinGW 9.2 e `-std=c++11 -Wall -Wextra -Werror -pedantic`: superati esempi del protocollo, null/zero, limiti di rappresentazione, configurazione e stato logico iniziale.

Risultato registrato:

```text
STEP1_OK: protocol examples, unavailable values, capacity, configuration and initial logical state
Native sizes: frame=200 state=336 response=348 bytes
```

Limiti: test su PC, nessuna conferma di compilazione MCU o di GPIO/Bridge reale. Parser JSON, RPC v1, FSM, watchdog operativo e stime ancora assenti.

## 5. Preparazione per Arduino App Lab

[sketch.ino](../sketch/sketch.ino) include ora gli header dello step 1 per farli compilare anche con l'app Arduino. Il runtime resta **CrossSense Linux LED Counter**, con `crosssense_set_led` e `crosssense_get_led_change_count`; Python sceglie la sequenza LED. Gli header non introducono un ciclo semaforico.

Preparato e controllato un archivio `dist/crosssense-step1.zip` con manifest, Python, sketch, header e sorgenti dei test. Il pacchetto non esegue i test nativi. Compilazione UNO Q, caricamento e osservazione dei LED sulla scheda non sono stati verificati durante questa preparazione.

Al checkpoint di documentazione lo ZIP non risulta più presente: per importare nuovamente l'app occorre rigenerarlo dai sorgenti. La cartella firmware rimane il riferimento di sviluppo.

## 6. Stato Linux osservato al checkpoint

Nel repository è presente l'adapter Linux/dashboard in [dashboard/rt.py](../../dashboard/rt.py), introdotto dal commit `e920f47`. Espone lo scambio verso la RPC v1 e la gestione delle richieste per la dashboard; il [README dashboard](../../dashboard/README.md) documenta l'avvio.

Questa voce registra la presenza del codice e della documentazione. Non è una verifica di integrazione sul Bridge reale. Lo sketch LED attuale non espone ancora la RPC che l'adapter attende.

## 7. Documentazione persistente e avvio della discussione sullo step 2

Pasquale ha richiesto di conservare gli step e lo storico in `firmware/docs`, poi ha confermato lo step 1 completato e chiesto di discutere l'obiettivo dello step 2 prima del codice.

Creati il [piano con punto di ripresa](README.md) e questo storico. Lo step 2 è registrato come **in discussione**, con obiettivo proposto: ricezione/validazione JSON, deposito atomico, gestione ordine/duplicati/richieste e risposta compatibile con Linux. Le transizioni semaforiche restano allo step 3.

Prossimo passo: concordare il perimetro dello step 2 e poi implementare il confine Bridge. In questa sessione di documentazione non è stato aggiunto codice operativo né ripetuta la verifica nativa dello step 1.

## Modello per la prossima voce

```text
Data e step:
Richiesta/obiettivo:
Decisioni e motivazione:
File modificati:
Verifiche eseguite ed esito (PC o scheda):
Limiti e decisioni ancora aperte:
Prossimo punto di ripresa:
```
