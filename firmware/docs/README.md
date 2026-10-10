# Percorso di sviluppo STM32

Aggiornato il 10 ottobre 2026. Responsabile: Pasquale.

Questo documento conserva il piano e il punto di ripresa; lo [storico](history.md) registra le decisioni e le verifiche. Il riferimento per i messaggi resta il [contratto Bridge v1](../../protocol/bridge-v1.md).

## Punto di ripresa

- **Step 1 completato:** strutture dati e configurazione C++11 implementate e verificate con test nativi su PC.
- **Step 2 in discussione:** definire il comportamento di ricezione, validazione e risposta prima di implementarlo.
- Compilazione con il core UNO Q, caricamento e scambio Bridge reale ancora da verificare.
- Lo sketch attuale esegue la prova LED comandata da Linux. Non espone ancora `crosssense_update` e non contiene il controller semaforico.
- È presente un [adapter Linux/dashboard](../../dashboard/rt.py) che attende la RPC del contratto v1. La sua presenza non dimostra l'integrazione sulla scheda.

## Piano concordato

| Step | Obiettivo | Criterio di completamento | Stato |
| --- | --- | --- | --- |
| 1 | Definire strutture, capacità e configurazione | Rappresentare gli esempi del protocollo, i valori null e lo stato iniziale; superare i test nativi | Completato su PC; verifica MCU pendente |
| 2 | Implementare lo scambio Bridge | Ricevere JSON, validarlo, depositare un frame completo e restituire telemetria compatibile con Linux; verificare errori e scambio sulla scheda | In discussione, codice non iniziato |
| 3 | Implementare la macchina a stati di base | Avvio protetto, ciclo veicoli/pedoni, richieste manuali e watchdog; loop autonomo anche se Linux si ferma, senza verdi incompatibili | Da iniziare |
| 4 | Adattare il ciclo alle osservazioni | Richieste automatiche dalle zone di attesa, conferme temporali, limiti di attesa, clearance e recupero; un pedone lento o fermo mantiene la protezione | Da iniziare |
| 5 | Calcolare movimento e rischio | Storico per ID, velocità, direzione, TTC, distanza di arresto e allarmi; verificare traiettorie note, dati null e cambi di ID/stream | Da iniziare |
| 6 | Integrare e tarare la demo | Visione, dashboard e attuatori reali insieme; misurare tempi, tarare parametri e ripetere scenari, riavvii e perdita collegamento | Da iniziare |

Il primo traguardo funzionale è alla fine dello step 3: una richiesta sintetica Linux produce un ciclo autonomo STM32 e la dashboard riceve lo stato effettivo.

## Step 1: ciò che abbiamo

- [crosssense_types.h](../sketch/crosssense_types.h): osservazioni, tracce, richieste, stato, errori, allarmi, stime e risposta.
- [crosssense_config.h](../sketch/crosssense_config.h): limiti e configurazione temporale, con controlli di coerenza numerica.
- [step1_test.cpp](../tests/step1_test.cpp): esempi del protocollo, valori assenti e zero, capacità, configurazione e stato logico iniziale.
- [sketch.ino](../sketch/sketch.ino): include gli header; il comportamento operativo resta la prova LED descritta nel [README firmware](../README.md).

Decisioni fissate: C++11, capacità fisse, nessuna allocazione dinamica nelle strutture; massimo 8 tracce/stime e 4 allarmi. `Nullable<T>` distingue un dato assente da uno zero valido. L'ID ricevuto nella risposta è distinto dal frame applicato dal loop.

Lo stato logico iniziale è `FAULT`/`NO_DATA`, con rossi comandati nello stato. Questo non configura le uscite fisiche: nella prova LED esistente, i LED all'avvio sono spenti.

Le durate semaforiche restano **0 = da configurare**. I valori dei test sono esempi, non parametri della demo. Tick 10 ms, invii 5 Hz, timeout osservazioni 1000 ms e budget trasporto 250 ms sono obiettivi iniziali da misurare.

Ultima verifica nativa registrata il 10 ottobre 2026: GCC MinGW 9.2, C++11, esito `STEP1_OK`; dimensioni sul PC: frame 200, stato 336, risposta 348 byte. Non sono misure di memoria sul toolchain MCU.

Per ripeterla dalla radice del repository in PowerShell:

```powershell
New-Item -ItemType Directory -Force firmware/build | Out-Null
g++ -std=c++11 -Wall -Wextra -Werror -pedantic firmware/tests/step1_test.cpp -o firmware/build/step1_test.exe
./firmware/build/step1_test.exe
```

## Step 2: obiettivo proposto

Realizzare il confine tra Linux e il futuro controller, mantenendo una sola RPC:

```text
crosssense_update(frame_json) -> state_json
```

Il percorso previsto è: JSON -> validazione -> buffer di un frame -> consumo nel loop -> risposta con stato corrente. La ricezione non deve cambiare direttamente una fase o un GPIO.

1. **Decodifica e validazione:** rispettare campi, tipi, range, capacità, ID univoci, coordinate entrambe null o entrambe valide e coerenza tra tracce e zone. Un messaggio camera assente (`valid=false`) è ammesso dal protocollo; non equivale a JSON malformato.
2. **Ordine e freschezza:** gestire stream, frame, wrap, timestamp e dati troppo vecchi; distinguere `BAD_DATA`, `OLD_FRAME` e `STALE_FRAME`. Un duplicato può aggiornare solo l'età, non applicare nuovamente richieste né rinnovare la validità.
3. **Deposito atomico:** un solo frame in attesa; rispondere `BUSY` se non è stato consumato. `ok=true` significa accettato, mentre `applied_stream/applied_frame` indicano ciò che il loop ha realmente consumato.
4. **Richieste:** conservare i tre livelli e riconoscere i passaggi false -> true una sola volta. Accessibile implica richiesta pedonale; l'esecuzione e le priorità saranno responsabilità del controller.
5. **Risposta:** serializzare tutti i campi previsti, preservando null e nomi del contratto, entro 900 byte. Preparare lo stato iniziale e i metadati di ricezione senza inventare countdown, stime o un ciclo semaforico già funzionante.
6. **Prova:** test locali del protocollo, compilazione UNO Q e scambio sintetico a 5 Hz con Linux. Controllare anche payload massimo, camera/calibrazione assenti, duplicati, dati incoerenti, buffer occupato, riavvio stream e ritardi.

Il watchdog che modifica fasi e uscite appartiene allo step 3; lo step 2 prepara la gestione dell'età e le informazioni necessarie. La risposta deve descrivere il comportamento realmente presente durante l'integrazione, anche per le uscite della prova LED.

Prima del codice, concordare questa ripartizione e scegliere un parser JSON compatibile con C++ e con le versioni delle librerie nel [profilo Arduino](../sketch/sketch.yaml). La validazione deve essere compatibile anche con quella del servizio Linux già presente.

## Decisioni ancora aperte

- Assegnazione dei segnali a LED3/LED4 oppure ad attuatori esterni; buzzer e beacon, pin e polarità.
- Durate delle fasi e finestre di conferma/recupero. Nessun tempo del test va copiato come scelta definitiva.
- Garanzia di consegna Bridge entro 250 ms: un timeout Python da solo non impedisce l'esecuzione tardiva di una vecchia RPC. Verificare questo punto prima di autorizzare il rilascio veicolare con dati `clear`.
- Geometria/calibrazione e soglie per le stime e gli allarmi dello step 5.
- Pacchetto App Lab: lo ZIP preparato durante la sessione non è presente al checkpoint attuale. Rigenerarlo dai sorgenti prima di una nuova importazione; le modifiche sulla scheda non si sincronizzano automaticamente con il repository.

## Come continuare lo storico

A ogni sessione aggiornare il punto di ripresa e aggiungere una voce in [history.md](history.md): decisione, file interessati, verifiche realmente eseguite, limiti e prossimo passo. Distinguere sempre codice implementato, test su PC e verifica sulla scheda. Registrare cambi al contratto in `protocol/`, evitando copie divergenti dei messaggi qui.
