# Setup Arduino UNO Q

## Prima prova

1. Verificare scheda UNO Q, cavo USB-C dati, alimentazione e versione App Lab.
2. Preparare la scheda con il [manuale ufficiale UNO Q](https://docs.arduino.cc/tutorials/uno-q/user-manual/) e la [guida App Lab](https://docs.arduino.cc/software/app-lab/).
3. Creare/importare l'app CrossSense preservando `app.yaml`, `python/`, `sketch/` e `config/`. Per importazione ZIP e percorsi, seguire l'interfaccia della versione installata.
4. Avviare l'app con il profilo `arduino:zephyr` in `sketch/sketch.yaml`. Lo scaffold usa RouterBridge dell'ambiente UNO Q: verificare disponibilità e registrare la versione che compila.
5. Verificare nel log `MCU: scaffold_ready`. L'app non ha bisogno di camera e non pilota uscite esterne.

Sul PC, `python python/main.py --check` verifica la configurazione senza runtime Arduino. Il percorso della configurazione è risolto rispetto all'app, non alla directory corrente; `--config` permette di indicare un file locale.

## Passaggio al prototipo

- Verificare la camera USB e il campo visivo prima di integrare acquisizione o brick AI.
- Scegliere il modello dopo aver misurato FPS, latenza e RAM sulla variante UNO Q disponibile. Annotare classi, licenza, versione e checksum in `models/`.
- Aggiungere soltanto brick/dependenze effettivamente necessari. La base ha `bricks: []` e non scarica modelli.
- Annotare pin e livelli elettrici in `hardware/`; le impostazioni di una UNO classica non sono automaticamente valide per UNO Q.
- Implementare politica, uscite e gestione guasti prima di collegare la demo completa.

## Prova offline

Predisporre inizialmente pacchetti, immagini container, brick e modelli usando la rete, quando necessario. Poi riavviare l'app senza Internet e verificare che acquisizione, inferenza, Bridge e luci funzionino con risorse locali. Ripetere la prova dopo un riavvio della scheda; annotare eventuali dipendenze da servizi esterni.

## Evidenze da registrare

Variante e RAM della UNO Q; versione OS, App Lab e core Zephyr; camera; modello e checksum; comando/versione di compilazione; risultato Bridge; data della prova e risultati offline. Compilazione e prove sulla scheda non sono ancora eseguite in questa base.
