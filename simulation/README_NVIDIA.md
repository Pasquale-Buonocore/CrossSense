# CrossSense — Guida Esecuzione su PC con GPU NVIDIA

Questa guida descrive i requisiti hardware, le dipendenze software e i comandi per eseguire lo script di generazione video ad alto realismo su schede grafiche **NVIDIA (CUDA)**.

---

## 1. Requisiti Hardware

- **Scheda Grafica (GPU):** NVIDIA con architettura Pascal, Turing, Ampere, Ada Lovelace o successive (es. GTX 1660, RTX 2060/3060/4060/3080/4090 o GPU Datacenter T4/A10G/V100/A100).
- **VRAM Dedicata Minima:** 4 GB di VRAM (consigliati 6 GB o più per risoluzione nativa 2528x1696).
- **Sistema Operativo:** Linux (Ubuntu 20.04/22.04/24.04), Windows 10/11 (con driver NVIDIA aggiornati) o macOS (solo CPU fallback).

---

## 2. Verifica dell'Hardware e Driver NVIDIA

Prima di procedere, apri un terminale (o Prompt dei comandi su Windows) e controlla che la GPU e i driver siano riconosciuti:

```bash
# 1. Verifica presenza GPU NVIDIA e versione Driver
nvidia-smi
```

Se il comando mostra la tabella con il nome della scheda e la versione di CUDA (es. `CUDA Version: 12.x`), l'hardware è pronto.

---

## 3. Installazione Dipendenze e Ambiente

È consigliato utilizzare un ambiente virtuale Python (versione 3.9, 3.10 o 3.11):

```bash
# Crea e attiva un ambiente virtuale (opzionale ma consigliato)
python3 -m venv venv_crosssense
source venv_crosssense/bin/activate  # Su Linux
# venv_crosssense\Scripts\activate    # Su Windows
```

### A. Installazione di PyTorch con supporto CUDA
Vai sul sito ufficiale PyTorch o installa la versione adatta ai tuoi driver CUDA:

```bash
# Per CUDA 12.1 (standard recente)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Oppure per CUDA 11.8:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### B. Installazione delle librerie grafiche e scientifiche
```bash
pip install opencv-python pillow numpy
```

---

## 4. Test di Verifica del Supporto CUDA in Python

Esegui questo breve comando per verificare che PyTorch rilevi correttamente la scheda:

```bash
python -c "import torch; print('CUDA Disponibile:', torch.cuda.is_available()); print('Nome GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Nessuna')"
```

Se restituisce `CUDA Disponibile: True`, l'accelerazione hardware è pienamente operativa.

---

## 5. Come Eseguire lo Script di Simulazione CUDA

Posizionati nella root del progetto `CrossSense`:

```bash
cd CrossSense
```

### Esempi di comandi:

1. **Generare lo Scenario 1 in modalità Neural CCTV (15 FPS):**
   ```bash
   python simulation/generate_scenarios_cuda.py --scenario 1 --mode neural_cctv --fps 15
   ```

2. **Generare tutti i 5 scenari su GPU:**
   ```bash
   python simulation/generate_scenarios_cuda.py --all --mode neural_cctv --fps 15
   ```

3. **Salvare su un file video personalizzato:**
   ```bash
   python simulation/generate_scenarios_cuda.py --scenario 1 --output simulation/output/mio_video_gpu.mp4 --fps 15
   ```

### Modalità di rendering disponibili (`--mode`):
- `neural_cctv` (Predefinita su GPU): pipeline tensoriale su VRAM, aberrazione cromatica, rumore poissoniano sensore CMOS e ombre volumetriche.
- `fotoreal`: rifinitura ottica grandangolare avanzata e vignettatura.
- `standard`: rendering sprite classico.

Tutti i video generati vengono salvati automaticamente nella cartella `simulation/output/`.
