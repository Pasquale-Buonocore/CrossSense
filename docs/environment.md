# Ambiente verificato — 10 ottobre 2026

## Mac

macOS 26.7 Intel; Python 3.11.7; `uv` 0.10.0; Arduino CLI 1.4.1; Arduino App Lab 1.0.0. Repository inizialmente vuoto, branch `main` senza commit. Creato venv `.venv`, verificato con `scripts/check_host.py`. SDK Arduino Python utilizzato nel container App Lab, non installato sul Mac.

La UNO Q è riconosciuta via USB: VID `2341`, PID `0078`, seriale `227988816`, porta osservata `/dev/cu.usbmodem2279888162`. ADB disponibile in `~/Library/Arduino15/packages/arduino/tools/adb/32.0.0/adb`; `scripts/board.py` lo trova automaticamente. Il core Zephyr non è installato sul Mac: per questa fase la compilazione avviene sulla scheda.

## UNO Q

- Hostname `CrossSense`, utente `arduino`, architettura aarch64.
- Debian 13.7 (trixie), kernel `6.16.7-g0dd6551ae96b`.
- RAM 3,6 GiB, circa 2,9 GiB disponibili al primo controllo; swap 1,8 GiB.
- Filesystem root 9,8 GiB, circa 2,1 GiB liberi prima di preparare il toolchain dell'app.
- Wi-Fi attivo, IP osservato `192.168.23.19/23` (DHCP: può cambiare).
- Arduino App CLI 0.13.0, core `arduino:zephyr` 1.0.0, Python host 3.13.5.
- Servizi `arduino-router` e Docker attivi; container base `python-apps-base:0.12.0` già presente. Import `from arduino.app_utils import Bridge, App` verificato nel container senza rete.
- ADB operativo. SSH non ancora validato: prima verifica fermata dalla chiave host sconosciuta; non sono state modificate le credenziali o le impostazioni SSH.

## Prova Bridge

App `crosssense-env` creata e sorgenti copiati in `/home/arduino/ArduinoApps/crosssense-env`. Espone `crosssense_ping` sulla MCU, interrogato ogni secondo da Linux, senza configurare GPIO. Non è il controller semaforico e non comprende il suo watchdog.

Il primo avvio è fallito prima della compilazione: la shell ADB imposta `TMPDIR=/data/local/tmp`, cartella assente sulla scheda. Il comando corretto è:

```sh
TMPDIR=/tmp arduino-app-cli app start /home/arduino/ArduinoApps/crosssense-env
```

App CLI prepara una cache di toolchain per il profilo anche se il core è già installato nell'ambiente globale. Perciò il primo avvio richiede download e spazio; questi asset vanno preparati prima delle prove offline.

Esito: compilazione, caricamento STM32, provisioning container e RPC riusciti. Il profilo elenca esplicitamente anche le dipendenze transitive: Arduino_RouterBridge 0.4.3, Arduino_RPClite 0.3.1, MsgPack 0.4.2, ArxContainer 0.7.0, ArxTypeTraits 0.3.2, DebugLog 0.8.4. Con il solo RouterBridge la compilazione non trovava `Arduino_RPClite.h`.

Sketch compilato: 84.060 byte di programma, 33.868 byte di variabili globali, secondo il report del toolchain. Nei primi otto campioni RPC, round-trip da 6,94 a 9,92 ms. Questi valori non includono acquisizione/inferenza e non sono un benchmark sotto carico.

```text
BRIDGE_OK mcu_uptime_ms=6119 roundtrip_ms=9.92
BRIDGE_OK mcu_uptime_ms=8134 roundtrip_ms=7.97
BRIDGE_OK mcu_uptime_ms=9141 roundtrip_ms=6.94
BRIDGE_OK mcu_uptime_ms=13171 roundtrip_ms=7.63
```

App Linux arrestata dopo la verifica; lo sketch di prova rimane sulla MCU. Nessuna uscita GPIO configurata. Spazio libero finale ancora circa 2,1 GiB. L’acquisizione camera è stata successivamente verificata come descritto sotto; visione AI, controller semaforico e dashboard non sono ancora implementati. Il funzionamento offline dell'intero MVP resta da verificare dopo aver scelto e preparato il modello.

## Camera CAM0

Hardware confermato: IMX219 su CAM0 di UNO Media Carrier. Prima della configurazione Linux esponeva soltanto i codec Qualcomm Venus su `/dev/video0` e `/dev/video1`; lo stato operativo aggiornato è riportato sotto.

Diagnosi: nodo `/sys/firmware/devicetree/base/soc@0/camss@5c11000/status` = `disabled`; nessun nodo sensore IMX/OV rilevato nella ricerca del device tree attivo. Il kernel dispone di moduli CAMSS, IMX219, IMX412, OV5640 e OV5645. Presente `/boot/efi/dtb/qcom/qrb2210-arduino-imola-camera-rpiv2.dtb`, ma questo non dimostra che la camera collegata sia IMX219 né che il carrier usi lo stesso cablaggio.

Aggiornamento: confermato UNO Media Carrier e autorizzata esplicitamente la modifica al boot. Applicato il DTB IMX219 attraverso `scripts/enable-imx219.py`, poi riavviata la scheda dopo il completamento dell'aggiornamento APT dell'utente. Backup originale: `/boot/efi/crosssense-backups/a3cfdcbfa9ad463e89f8a1f9bd9a5dd4-6.16.7-g0dd6551ae96b.conf.1791637333080336311.bak`.

CAMSS ora attivo: `/dev/video0`–`/dev/video7`, `/dev/media0`; codec Venus spostato su `/dev/video8`–`/dev/video9`. `cam --list` rileva IMX219 su CCI bus 0. Acquisiti tre frame come root con `cam -c 1 --stream role=viewfinder,width=640,height=480 --capture=3 --file=/tmp/crosssense-frame-#.bin`; formato effettivo 632×480 ABGR8888, 1.213.440 byte/frame. Un frame convertito in PNG è disponibile localmente in `.local/camera/frame.png`. La brevissima prova non misura prestazioni sostenute né latenza AI.

Dopo autorizzazione esplicita dell’utente, applicato `scripts/configure-camera-access.sh`: regola permanente `/etc/udev/rules.d/99-crosssense-camera-dma.rules`, limitata a `/dev/dma_heap/system`, gruppo video e modalità 0660. Ricaricate le regole e verificata l’acquisizione di tre frame con utente arduino (uid 1000), senza sudo: 632×480 ABGR8888, 1.213.440 byte/frame. Non serve un ulteriore riavvio. Libcamera usa software ISP con configurazione `uncalibrated.yaml`; calibrazione colore ed esposizione da verificare. L’accesso camera da container App Lab va ancora verificato separatamente.

Fonti di riferimento: [accesso Debian/ADB](https://docs.arduino.cc/tutorials/uno-q/debian-guide/), [formato Arduino App](https://github.com/arduino/arduino-app-cli/blob/main/docs/app-specification.md). I dati sopra provengono dai comandi eseguiti sulla scheda, non da specifiche nominali.

## Deployment video YOLO — 10 ottobre 2026

App attiva: `/home/arduino/ArduinoApps/crosssense-yolo-360`, dashboard su
`http://192.168.23.19:8080`. Sorgenti aggiornati da Git con i cinque MP4 di
`simulation/output` (2528×1696, 30 FPS). Tutti sono copiati nell'app e
selezionabili dalla dashboard; l'ultima scelta persiste sulla scheda. Le
zone di Gaetano restano configurabili e condivise.

Frame elaborati 360×242, ingresso al modello 352×352: nessun lato supera
360 pixel. YOLO26n della consegna è esportato in NCNN FP32, con ByteTrack e
preview JPEG annotata con classe, ID e confidenza. Ultralytics 8.4.175,
NCNN 1.0.20260526, PyTorch 2.8.0 CPU, torchvision 0.23.0 e lap 0.5.13 sono
installati nel venv persistente dell'app. OpenCV headless 4.13.0 è fornito
dall'immagine App Lab 0.12.0. Il modello è locale.

Corretto il limite effettivo RouterBridge: la libreria 0.4.3 negoziava
256 byte, insufficienti per Bridge v1. Il profilo usa la copia locale
MPL-2.0, con buffer RPC 1024 e stack worker 4096 byte. Compilazione e flash
STM32 riusciti: 113140 byte di programma, 47188 byte di globali. Ciclo
logico attivo e telemetria reale sulla dashboard; nessun GPIO configurato.

Verificati sulla UNO Q caricamento e cambio di tutti e cinque i video,
nuove osservazioni fresche, limite dimensioni, risposta Bridge accettata
e assenza di verdi conflittuali nei campioni. Inferenza nei campioni di
avvio: 108–136 ms. Sono misure di quei campioni, non un benchmark completo
dei cinque scenari. Ogni frame viene elaborato; il replay rallenta rispetto
ai 30 FPS originali quando la catena non ne sostiene la frequenza.

I server e i worker CrossSense sul Mac sono stati arrestati. Elaborazione,
dashboard e scambio RT continuano sulla UNO Q anche senza browser.


## Riavvio e ottimizzazione video — 10 ottobre 2026, sera

Wi-Fi aggiornato; dashboard verificata su `http://192.168.1.196:8080`.
L’app `crosssense-yolo-360` usa ora preview 480×322 e detection NCNN 320×320.
Esportato lo stesso YOLO26n a 320, mantenendo l’export 352. NCNN usa due
thread al caricamento dei pesi; BLAS, PyTorch e OpenCV limitati a un thread.
Cinque MP4 ricodificati a 480×322 H.264 CRF 18, preservando numero di frame
e frame rate; originali conservati localmente e nel backup della app.
ROI revisione 3, posizioni semafori e selezione `output_2.mp4` conservate.

FPS reali della pipeline aggiunti accanto all’inferenza (finestra 30 frame).
Corretto l’adapter RT: tra immagini nuove interroga la telemetria usando
il duplicato esatto dell’ultimo messaggio, aggiornando solo l’età. STM32 non
lo riapplica e non rinnova il watchdog. Prima si generavano indisponibilità
artificiali quando l’inferenza oltrepassava il tick RPC di 200 ms. I ritardi
RPC oltre 250 ms continuano a invalidare la connessione, senza mascherarli.

Prova finale su `output_2.mp4`, con browser dashboard attivi: 150
campioni in 70.3 s, 5.11 FPS, inferenza mediana
178.3 ms (p95 195.6 ms), RPC
mediana 165.4 ms, massimo 204.1 ms.
Nessun campione disconnesso o con fault. Prima della conversione MP4 a 480,
la nuova configurazione sosteneva circa 4,38 FPS e aveva due campioni TIMEOUT
su 150. Il campione iniziale a 360/352 sosteneva 5,36 FPS, ma presentava due
errori di budget RPC e tre INVALID_DATA su 100 campioni. Le finestre non
sono un benchmark controllato né una garanzia di assenza di guasti futuri.

Passati 21 test dashboard, 8 test vision, controlli JavaScript, test nativo
STM32 del protocollo e prova integrata con acquisizione 2,5 Hz/RPC 5 Hz:
nessun guasto tra immagini, TIMEOUT preservato quando l’acquisizione cessa.
