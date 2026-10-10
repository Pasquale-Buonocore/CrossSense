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
