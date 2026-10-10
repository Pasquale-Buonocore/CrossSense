# Hardware del prototipo

Target: **Arduino UNO Q**, camera e plastico dell'attraversamento.

| Componente | Stato / decisione |
| --- | --- |
| UNO Q e alimentazione | Registrare variante/RAM e alimentatore effettivi |
| Camera | Scegliere modello e verificare compatibilità, campo visivo e latenza |
| Semafori veicoli/pedoni | Definire numero di LED, pilotaggio e corrente |
| Luci lungo la strada | Definire posizione, tipo e alimentazione |
| Allerta rossa verso l'attraversamento | Uscita distinta dalle fasi semaforiche |
| Plastico e supporto camera | CAD e distanze misurabili da aggiungere |

## Cablaggio da compilare prima di abilitare GPIO

| Segnale | Pin UNO Q | Driver/resistenza | Alimentazione | Livello attivo |
| --- | --- | --- | --- | --- |
| Rosso/giallo/verde veicoli | Da definire | Da definire | Da definire | Da definire |
| Rosso/verde pedoni | Da definire | Da definire | Da definire | Da definire |
| Luci di avvicinamento | Da definire | Da definire | Da definire | Da definire |
| Allerta rossa | Da definire | Da definire | Da definire | Da definire |

Consultare [pinout e documentazione UNO Q](https://docs.arduino.cc/hardware/uno-q/) per livelli e limiti elettrici. Non riutilizzare automaticamente assegnazioni pin o cablaggi della UNO classica. Lo sketch iniziale non configura GPIO.

Destinazioni suggerite: `hardware/cad/` per FreeCAD/STL, `hardware/wiring/` per schemi, `hardware/photos/` per immagini del montaggio. Il materiale locale `mini-semaforo` va revisionato prima di integrarlo: non è stato copiato automaticamente in questo repository.
