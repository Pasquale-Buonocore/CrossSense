# Lavorare su CrossSense

1. Scegliere un obiettivo nella [roadmap](docs/roadmap.md), creando un branch `feature/...`, `fix/...` o `docs/...`.
2. Tenere il codice Linux in `python/crosssense/`, l'hardware in `sketch/`, la configurazione in `config/` e la documentazione in `docs/`.
3. Eseguire `python python/main.py --check` e `python -m compileall -q python` dalla root.
4. Per modifiche a sketch, Bridge, modelli o brick, provare sulla UNO Q e riportare versioni, risultato e limiti. Il controllo PC non compila il firmware.
5. Aprire una PR con obiettivo, modifiche, prove e stato della demo; aggiornare README e roadmap quando cambia ciò che è implementato.

Non aggiungere pesi, video, segreti o log con dati personali. Evitare nuove dipendenze finché non servono a una funzione verificabile sulla scheda. Prima di abilitare GPIO aggiornare cablaggio, gestione guasti e protocollo Bridge.
