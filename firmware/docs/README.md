> Documento storico. Il perimetro corrente è replay dichiarato e segnali soltanto nella dashboard. Riferimenti aggiornati: README principale e docs/architecture.md. Le affermazioni di verifica sotto riportate appartengono alle prove precedenti.

# Percorso di sviluppo STM32

Aggiornato il 10 ottobre 2026. Responsabile: Pasquale.

Questo documento conserva il piano e il punto di ripresa; lo [storico](history.md) registra le decisioni e le verifiche. Il riferimento per i messaggi resta il [contratto Bridge v1](../../protocol/bridge-v1.md).

## Punto di ripresa

- **Step 1 completato:** strutture dati e configurazione C++11 implementate e verificate con test nativi su PC.
- **Step 2 implementato su PC:** ricezione/validazione JSON, buffer atomico, telemetria e watchdog in `rt_protocol.h`, con test nativi.
- Compilazione con il core UNO Q, caricamento e scambio Bridge reale ancora da verificare.
- Lo sketch espone `crosssense_update`; per default mantiene entrambi i rossi. Il [ciclo standard di prova](standard-cycle.md) si abilita nel pacchetto con `--standard-cycle`.
- È presente un [adapter Linux/dashboard](../../dashboard/rt.py) usato dallo script di prova HTTP. Due cicli con server e sketch effettivi sono stati verificati sul PC con GPIO/Bridge simulati. La verifica sulla scheda resta pendente.

## Piano concordato

| Step | Obiettivo | Criterio di completamento | Stato |
| --- | --- | --- | --- |
| 1 | Definire strutture, capacità e configurazione | Rappresentare gli esempi del protocollo, i valori null e lo stato iniziale; superare i test nativi | Completato su PC; verifica MCU pendente |
| 2 | Implementare lo scambio Bridge | Ricevere JSON, validarlo, depositare un frame completo e restituire telemetria compatibile con Linux; verificare errori e scambio sulla scheda | Implementato e verificato su PC; verifica MCU pendente |
| 3 | Implementare la macchina a stati di base | Avvio protetto, ciclo veicoli/pedoni, richieste manuali e watchdog; loop autonomo anche se Linux si ferma, senza verdi incompatibili | Ciclo dashboard di prova implementato e verificato su PC; verifica MCU pendente |
| 4 | Adattare il ciclo alle osservazioni | Richieste automatiche dalle zone di attesa, conferme temporali, limiti di attesa, clearance e recupero; un pedone lento o fermo mantiene la protezione | Da iniziare |
| 5 | Calcolare movimento e rischio | Storico per ID, velocità, direzione, TTC, distanza di arresto e allarmi; verificare traiettorie note, dati null e cambi di ID/stream | Da iniziare |
| 6 | Integrare e tarare la demo | Visione, dashboard e attuatori reali insieme; misurare tempi, tarare parametri e ripetere scenari, riavvii e perdita collegamento | Da iniziare |

Il primo traguardo funzionale è alla fine dello step 3: una richiesta sintetica Linux produce un ciclo autonomo STM32 e la dashboard riceve lo stato effettivo.

## Step 1: ciò che abbiamo

- [crosssense_types.h](../sketch/crosssense_types.h): osservazioni, tracce, richieste, stato, errori, allarmi, stime e risposta.
- [crosssense_config.h](../sketch/crosssense_config.h): limiti e configurazione temporale, con controlli di coerenza numerica.
- [step1_test.cpp](../tests/step1_test.cpp): esempi del protocollo, valori assenti e zero, capacità, configurazione e stato logico iniziale.
- [sketch.ino](../sketch/sketch.ino): RPC e telemetria semaforica, senza GPIO, con ciclo opzionale in [standard_cycle.h](../sketch/standard_cycle.h).

Decisioni fissate: C++11, capacità fisse, nessuna allocazione dinamica nelle strutture; massimo 8 tracce/stime e 4 allarmi. `Nullable<T>` distingue un dato assente da uno zero valido. L'ID ricevuto nella risposta è distinto dal frame applicato dal loop.

Lo stato logico iniziale è `FAULT`/`NO_DATA`; lo sketch restituisce entrambi i campi luce rossi a boot e non configura GPIO.

Le durate in `ControllerConfig` restano **0 = da configurare** per il controller completo. Il ciclo dashboard usa tempi demo separati in `DemoTimings`, descritti nella [guida](standard-cycle.md). Tick 10 ms, invii 5 Hz, timeout osservazioni 1000 ms e budget trasporto 250 ms sono obiettivi iniziali da misurare sulla scheda.

Ultima verifica nativa registrata il 10 ottobre 2026: GCC MinGW 9.2, C++11, esito `STEP1_OK`; dimensioni sul PC: frame 200, stato 336, risposta 348 byte. Non sono misure di memoria sul toolchain MCU.

Per ripeterla dalla radice del repository in PowerShell:

```powershell
New-Item -ItemType Directory -Force firmware/build | Out-Null
g++ -std=c++11 -Wall -Wextra -Werror -pedantic firmware/tests/step1_test.cpp -o firmware/build/step1_test.exe
./firmware/build/step1_test.exe
```

## Step 2: specifica di riferimento

Realizzare il confine tra Linux e il futuro controller, mantenendo una sola RPC:

```text
crosssense_update(frame_json) -> state_json
```

Il percorso è: JSON -> validazione -> buffer di un frame -> consumo nel loop -> risposta con stato corrente. Le nuove osservazioni non avanzano le fasi nella callback; il watchdog può impostare il rosso logico già durante la RPC se i dati applicati sono scaduti. Il firmware non configura GPIO.

1. **Decodifica e validazione:** rispettare campi, tipi, range, capacità, ID univoci, coordinate entrambe null o entrambe valide e coerenza tra tracce e zone. Un messaggio camera assente (`valid=false`) è ammesso dal protocollo; non equivale a JSON malformato.
2. **Ordine e freschezza:** gestire stream, frame, wrap, timestamp e dati troppo vecchi; distinguere `BAD_DATA`, `OLD_FRAME` e `STALE_FRAME`. Un duplicato può aggiornare solo l'età, non applicare nuovamente richieste né rinnovare la validità.
3. **Deposito atomico:** un solo frame in attesa; rispondere `BUSY` se non è stato consumato. `ok=true` significa accettato, mentre `applied_stream/applied_frame` indicano ciò che il loop ha realmente consumato.
4. **Richieste:** conservare i tre livelli e riconoscere i passaggi false -> true una sola volta. Accessibile implica richiesta pedonale; l'esecuzione e le priorità saranno responsabilità del controller.
5. **Risposta:** serializzare tutti i campi previsti, preservando null e nomi del contratto, entro 900 byte. Preparare lo stato iniziale e i metadati di ricezione senza inventare countdown, stime o un ciclo semaforico già funzionante.
6. **Prova:** test locali del protocollo, compilazione UNO Q e scambio sintetico a 5 Hz con Linux. Controllare anche payload massimo, camera/calibrazione assenti, duplicati, dati incoerenti, buffer occupato, riavvio stream e ritardi.

Il watchdog che modifica fasi e uscite è ora operativo nel ciclo di prova dello step 3. La risposta descrive il comportamento presente durante l'integrazione.

Il parser scelto è ArduinoJson 7.4.3, presente nel [profilo Arduino](../sketch/sketch.yaml). La validazione è compatibile con quella del servizio Linux già presente; il contratto JSON resta invariato.

## Decisioni ancora aperte

- Attuatori esterni, buzzer e beacon, pin e polarità. La prova attuale usa esclusivamente i tre indicatori della dashboard.
- Durate delle fasi e finestre di conferma/recupero del controller completo. I tempi demo non sono scelte definitive.
- Garanzia di consegna Bridge entro 250 ms: un timeout Python da solo non impedisce l'esecuzione tardiva di una vecchia RPC. Verificare questo punto prima di autorizzare il rilascio veicolare con dati `clear`.
- Geometria/calibrazione e soglie per le stime e gli allarmi dello step 5.
- Pacchetto App Lab: si genera dai sorgenti con `scripts/package_rt.py --standard-cycle --zip`; gli artefatti in `dist/` sono ignorati da Git. Le modifiche sulla scheda non si sincronizzano automaticamente con il repository.

## Come continuare lo storico

A ogni sessione aggiornare il punto di ripresa e aggiungere una voce in [history.md](history.md): decisione, file interessati, verifiche realmente eseguite, limiti e prossimo passo. Distinguere sempre codice implementato, test su PC e verifica sulla scheda. Registrare cambi al contratto in `protocol/`, evitando copie divergenti dei messaggi qui.
