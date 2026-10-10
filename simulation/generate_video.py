#!/usr/bin/env python3
"""
CrossSense — Generatore Video Multi-Attore con Semaforo Dinamico Multi-Ciclo
Simula un flusso continuo di traffico e pedoni su un arco temporale di 2 minuti,
con gestione rigorosa della separazione spaziale dei pedoni (zero sovrapposizioni).

Caratteristiche:
  - Durata: 2 minuti (120 secondi).
  - Cicli semaforici multipli (~35s per ciclo).
  - Generazione casuale continua distribuita nel tempo.
  - Velocità auto incrementata con frenata decisa e ripartenza al verde.
  - Pedoni con separazione corsie e postazioni di attesa dedicate:
      * Nessuna sovrapposizione tra pedoni sia in attesa al marciapiede sia durante l'attraversamento.
      * Corsie Y separate per senso di marcia: _LR transita sulla fascia inferiore, _RL sulla fascia superiore.
      * Slot di attesa distanziati a griglia sul marciapiede.
      * Mantenimento distanza di sicurezza longitudinale (headway) tra pedoni consecutivi.
      * Uscita completa dalla scena una volta superata la carreggiata.
  - Esattamente 1 carrozzina (Carrozzina_LR o Carrozzina_RL) a tempo casuale.
  - Indicatore semaforico HUD ingrandito ed evidente.

Utilizzo:
  python simulation/generate_video.py --duration 120 --fps 30 --output simulation/output.mp4
"""

import os
import sys
import math
import random
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

# Percorsi di default
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(WORKSPACE_DIR, "assets")
DEFAULT_BG = os.path.join(ASSETS_DIR, "StartingImage.jpeg")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "output.mp4")

# Asset disponibili
SPRITES_LR = ["Donna_LR", "Uomo_LR"]
SPRITES_RL = ["Donna_RL", "Uomo_RL"]
ALL_SPRITE_NAMES = ["Ambulanza", "Macchina", "Carrozzina_LR", "Carrozzina_RL"] + SPRITES_LR + SPRITES_RL

# Coordinate geometriche su StartingImage.jpeg (2528 x 1696)
LANE_APP_X_TOP = 1220
LANE_APP_Y_TOP = 240
LANE_APP_X_BOT = 960
LANE_APP_Y_BOT = 1696

STOP_LINE_Y = 820          # Linea d'arresto per la prima auto
QUEUE_SPACING_Y = 260      # Spazio tra auto in coda

# Limiti fuori campo per uscita di scena
EXIT_LEFT_X = -150
EXIT_RIGHT_X = 2680

# Fasce di attraversamento separate per direzione per evitare collisioni frontali:
# - Pedoni _RL (da destra a sinistra): utilizzano la fascia superiore delle strisce
TRACKS_RL = [1190, 1225, 1260]
# - Pedoni _LR (da sinistra a destra): utilizzano la fascia inferiore delle strisce
TRACKS_LR = [1310, 1345, 1380]

# Griglia di slot di attesa sul marciapiede sinistro (nessuna sovrapposizione in attesa)
WAITING_SLOTS_LEFT = [
    (480, 1310), (480, 1360),
    (380, 1290), (380, 1340), (380, 1380),
    (280, 1300), (280, 1350),
    (180, 1320), (180, 1360)
]

# Griglia di slot di attesa sul marciapiede destro
WAITING_SLOTS_RIGHT = [
    (2100, 1200), (2100, 1250),
    (2200, 1180), (2200, 1230), (2200, 1270),
    (2300, 1190), (2300, 1240),
    (2400, 1200), (2400, 1250)
]


def load_all_assets(assets_dir):
    """Carica tutti gli sprite PNG presenti nella cartella assets."""
    sprites = {}
    for name in ALL_SPRITE_NAMES:
        filename = f"{name}.png"
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                sprites[name] = img
            except Exception as e:
                print(f"[ERRORE] Impossibile caricare {filename}: {e}")
        else:
            print(f"[AVVISO] File {filename} non trovato in {assets_dir}")
    return sprites


def get_vehicle_scale(y):
    """Scala prospettica per i veicoli lungo la carreggiata."""
    ratio = (y - LANE_APP_Y_TOP) / float(LANE_APP_Y_BOT - LANE_APP_Y_TOP)
    ratio = max(0.0, min(1.3, ratio))
    return 0.35 + 1.15 * (ratio ** 1.25)


def get_app_vehicle_x(y):
    """Coordinata X della corsia di avvicinamento in base a Y (senza drift)."""
    ratio = (y - LANE_APP_Y_TOP) / float(LANE_APP_Y_BOT - LANE_APP_Y_TOP)
    return int(LANE_APP_X_TOP + (LANE_APP_X_BOT - LANE_APP_X_TOP) * ratio)


def overlay_rgba(background_img, sprite, center_x, center_y, scale=1.0):
    """Sovrappone uno sprite RGBA sullo sfondo RGBA."""
    if scale <= 0.05:
        return

    orig_w, orig_h = sprite.size
    new_w = max(4, int(orig_w * scale))
    new_h = max(4, int(orig_h * scale))

    resized = sprite.resize((new_w, new_h), Image.Resampling.LANCZOS)
    top_left_x = int(center_x - new_w // 2)
    top_left_y = int(center_y - new_h // 2)

    background_img.alpha_composite(resized, (top_left_x, top_left_y))


class RepeatingTrafficLightFSM:
    """
    Macchina a stati semaforica ciclica su periodi da 35 secondi:
      - 0.0s -> 18.0s: VERDE Auto / ROSSO Pedoni
      - 18.0s -> 22.0s: GIALLO Auto / ROSSO Pedoni
      - 22.0s -> 32.0s: ROSSO Auto / VERDE Pedoni
      - 32.0s -> 35.0s: ROSSO Auto / ROSSO Pedoni (Sgombero)
    """
    def __init__(self, cycle_len=35.0, t_yellow=18.0, t_ped_green=22.0, t_clearance=32.0):
        self.cycle_len = cycle_len
        self.t_yellow = t_yellow
        self.t_ped_green = t_ped_green
        self.t_clearance = t_clearance

    def get_state(self, current_time):
        t_cycle = current_time % self.cycle_len
        if t_cycle < self.t_yellow:
            return "VEHICLE_GREEN", "PED_RED"
        elif t_cycle < self.t_ped_green:
            return "VEHICLE_YELLOW", "PED_RED"
        elif t_cycle < self.t_clearance:
            return "VEHICLE_RED", "PED_GREEN"
        else:
            return "VEHICLE_RED", "PED_RED"

    def is_ped_green(self, current_time):
        _, ped_s = self.get_state(current_time)
        return ped_s == "PED_GREEN"

    def is_vehicle_green(self, current_time):
        veh_s, _ = self.get_state(current_time)
        return veh_s == "VEHICLE_GREEN"


class AntiOverlapPedestrian:
    """
    Pedone con separazione geometrica delle corsie, slot di attesa esclusivo
    e controllo della distanza di sicurezza per garantire zero sovrapposizioni.
    """
    def __init__(self, sprite_name, spawn_time, is_lr, target_crossing_y, waiting_slot):
        self.sprite_name = sprite_name
        self.spawn_time = spawn_time
        self.is_lr = is_lr  # True: SX -> DX, False: DX -> SX
        self.target_crossing_y = target_crossing_y
        self.wait_x, self.wait_y = waiting_slot

        self.is_wheelchair = "Carrozzina" in sprite_name
        self.scale = 0.95 if self.is_wheelchair else random.uniform(0.90, 0.98)
        self.base_speed = 125.0 if self.is_wheelchair else random.uniform(185.0, 215.0)
        self.current_speed = self.base_speed

        # Coordinate correnti
        if self.is_lr:
            self.cur_x = self.wait_x - 180.0
            self.cur_y = self.wait_y
            self.exit_x = EXIT_RIGHT_X
        else:
            self.cur_x = self.wait_x + 180.0
            self.cur_y = self.wait_y
            self.exit_x = EXIT_LEFT_X

        self.state = "approaching_wait"  # "approaching_wait", "waiting", "crossing", "exited"
        self.is_active = False

    def update(self, dt, current_time, fsm, active_pedestrians):
        if current_time < self.spawn_time:
            self.is_active = False
            return

        if self.state == "exited":
            self.is_active = False
            return

        self.is_active = True
        ped_green = fsm.is_ped_green(current_time)

        # 1. Fase Avvicinamento alla postazione di attesa sul marciapiede
        if self.state == "approaching_wait":
            if self.is_lr:
                self.cur_x += self.base_speed * dt
                if self.cur_x >= self.wait_x:
                    self.cur_x = self.wait_x
                    self.cur_y = self.wait_y
                    self.state = "crossing" if ped_green else "waiting"
            else:
                self.cur_x -= self.base_speed * dt
                if self.cur_x <= self.wait_x:
                    self.cur_x = self.wait_x
                    self.cur_y = self.wait_y
                    self.state = "crossing" if ped_green else "waiting"

        # 2. Fase di Attesa al Rosso sul proprio slot riservato
        elif self.state == "waiting":
            self.cur_x = self.wait_x
            self.cur_y = self.wait_y
            if ped_green:
                self.state = "crossing"

        # 3. Fase di Attraversamento al Verde (con transizione dolce verso la corsia Y assegnata)
        elif self.state == "crossing":
            # Allinea gradualmente Y alla corsia di attraversamento assegnata
            y_diff = self.target_crossing_y - self.cur_y
            self.cur_y += np.clip(y_diff * 4.0 * dt, -70.0 * dt, 70.0 * dt)

            # Controllo distanza di sicurezza con pedoni che precedono nella stessa direzione
            desired_speed = self.base_speed
            for other in active_pedestrians:
                if other is self or not other.is_active or other.state != "crossing":
                    continue
                # Se viaggiano nella stessa direzione e su corsie Y simili
                if other.is_lr == self.is_lr and abs(other.cur_y - self.cur_y) < 55:
                    if self.is_lr and other.cur_x > self.cur_x:
                        dist = other.cur_x - self.cur_x
                        if dist < 170:
                            # Rallenta per mantenere la distanza di sicurezza
                            desired_speed = min(desired_speed, max(40.0, other.current_speed * (dist / 170.0)))
                    elif not self.is_lr and other.cur_x < self.cur_x:
                        dist = self.cur_x - other.cur_x
                        if dist < 170:
                            desired_speed = min(desired_speed, max(40.0, other.current_speed * (dist / 170.0)))

            self.current_speed = desired_speed

            # Movimento orizzontale
            if self.is_lr:
                self.cur_x += self.current_speed * dt
                if self.cur_x >= self.exit_x:
                    self.state = "exited"
                    self.is_active = False
            else:
                self.cur_x -= self.current_speed * dt
                if self.cur_x <= self.exit_x:
                    self.state = "exited"
                    self.is_active = False

    def get_pose(self, current_time):
        if not self.is_active or self.state == "exited":
            return None, None, 0.0, False

        # Oscillazione passo solo durante il cammino
        if self.state in ["approaching_wait", "crossing"] and not self.is_wheelchair:
            step_bob = math.sin((current_time - self.spawn_time) * 8.0) * 3.0
        else:
            step_bob = 0.0

        return int(self.cur_x), int(self.cur_y + step_bob), self.scale, True


class DynamicVehicle:
    """Veicolo che scende veloce lungo la corsia, frena in coda se rosso/giallo, riparte al verde."""
    def __init__(self, sprite_name, spawn_time, base_speed=490.0):
        self.sprite_name = sprite_name
        self.spawn_time = spawn_time
        self.base_speed = base_speed
        self.current_speed = base_speed

        self.cur_y = LANE_APP_Y_TOP
        self.is_active = False
        self.has_exited = False

    def update(self, dt, current_time, fsm, leader_vehicle):
        if current_time < self.spawn_time:
            self.is_active = False
            return

        if self.has_exited:
            self.is_active = False
            return

        self.is_active = True
        veh_state, _ = fsm.get_state(current_time)

        # Quota d'arresto target (in coda al leader o alla linea STOP)
        if leader_vehicle is not None and leader_vehicle.is_active and leader_vehicle.cur_y > self.cur_y:
            effective_stop_y = leader_vehicle.cur_y - QUEUE_SPACING_Y
        else:
            effective_stop_y = STOP_LINE_Y

        # Gestione cinematica
        if veh_state == "VEHICLE_GREEN":
            # Verde: via libera ad alta velocità
            self.current_speed = min(self.base_speed, self.current_speed + 380.0 * dt)
            self.cur_y += self.current_speed * dt
        else:
            # Giallo / Rosso: frenata decisa e arresto in coda
            dist_to_stop = effective_stop_y - self.cur_y
            if dist_to_stop > 15:
                braking_speed = max(60.0, math.sqrt(2.0 * 320.0 * max(0.0, dist_to_stop)))
                self.current_speed = min(self.current_speed, braking_speed)
                self.cur_y += self.current_speed * dt
            else:
                self.current_speed = 0.0
                self.cur_y = min(self.cur_y, effective_stop_y)

        # Uscita dalla scena in basso
        if self.cur_y > LANE_APP_Y_BOT + 120:
            self.has_exited = True
            self.is_active = False

    def get_pose(self):
        if not self.is_active or self.has_exited:
            return None, None, 0.0, False

        cur_x = get_app_vehicle_x(self.cur_y)
        scale = get_vehicle_scale(self.cur_y)
        return int(cur_x), int(self.cur_y), scale, True


def draw_prominent_hud(frame_canvas, current_time, veh_state, ped_state):
    """Disegna l'indicatore semaforico HUD ingrandito con lanterne grafiche e testo chiaro."""
    draw = ImageDraw.Draw(frame_canvas, "RGBA")

    bx0, by0, bx1, by1 = 50, 45, 590, 275
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=(15, 18, 24, 235), outline=(220, 220, 225, 220), width=3)

    mins = int(current_time) // 60
    secs = int(current_time) % 60
    draw.text((bx0 + 25, by0 + 15), "CROSSSENSE SMART CROSSING", fill=(255, 255, 255, 255))
    draw.text((bx1 - 130, by0 + 15), f"{mins:02d}:{secs:02d}.{int((current_time%1)*10)}s", fill=(0, 230, 255, 255))
    draw.line([(bx0 + 20, by0 + 44), (bx1 - 20, by0 + 44)], fill=(120, 130, 145, 180), width=2)

    # --- SEZIONE AUTO ---
    draw.text((bx0 + 25, by0 + 60), "SEMAFORO AUTO:", fill=(200, 210, 225, 240))
    red_active = (veh_state == "VEHICLE_RED")
    yel_active = (veh_state == "VEHICLE_YELLOW")
    grn_active = (veh_state == "VEHICLE_GREEN")

    col_r = (255, 40, 40, 255) if red_active else (60, 20, 20, 140)
    col_y = (255, 210, 0, 255) if yel_active else (70, 60, 15, 140)
    col_g = (40, 255, 60, 255) if grn_active else (15, 65, 25, 140)

    draw.ellipse([bx0 + 200, by0 + 55, bx0 + 232, by0 + 87], fill=col_r, outline=(255, 255, 255, 200) if red_active else (80, 80, 80, 100), width=2)
    draw.ellipse([bx0 + 242, by0 + 55, bx0 + 274, by0 + 87], fill=col_y, outline=(255, 255, 255, 200) if yel_active else (80, 80, 80, 100), width=2)
    draw.ellipse([bx0 + 284, by0 + 55, bx0 + 316, by0 + 87], fill=col_g, outline=(255, 255, 255, 200) if grn_active else (80, 80, 80, 100), width=2)

    auto_status_label = {
        "VEHICLE_GREEN": ("VERDE - AVANTI", (40, 255, 60, 255)),
        "VEHICLE_YELLOW": ("GIALLO - RALLENTA", (255, 210, 0, 255)),
        "VEHICLE_RED": ("ROSSO - ALT (STOP)", (255, 50, 50, 255))
    }
    lbl_text, lbl_color = auto_status_label[veh_state]
    draw.text((bx0 + 335, by0 + 62), lbl_text, fill=lbl_color)

    draw.line([(bx0 + 20, by0 + 105), (bx1 - 20, by0 + 105)], fill=(60, 70, 85, 140), width=1)

    # --- SEZIONE PEDONI ---
    draw.text((bx0 + 25, by0 + 120), "SEMAFORO PEDONI:", fill=(200, 210, 225, 240))
    ped_red_active = (ped_state == "PED_RED")
    ped_grn_active = (ped_state == "PED_GREEN")

    p_col_r = (255, 40, 40, 255) if ped_red_active else (60, 20, 20, 140)
    p_col_g = (40, 255, 60, 255) if ped_grn_active else (15, 65, 25, 140)

    draw.ellipse([bx0 + 200, by0 + 115, bx0 + 232, by0 + 147], fill=p_col_r, outline=(255, 255, 255, 200) if ped_red_active else (80, 80, 80, 100), width=2)
    draw.ellipse([bx0 + 242, by0 + 115, bx0 + 274, by0 + 147], fill=p_col_g, outline=(255, 255, 255, 200) if ped_grn_active else (80, 80, 80, 100), width=2)

    ped_status_label = {
        "PED_RED": ("ROSSO - ATTESA AL MARCIAPIEDE", (255, 60, 60, 255)),
        "PED_GREEN": ("VERDE - ATTRAVERSAMENTO STRISCE", (40, 255, 60, 255))
    }
    p_lbl_text, p_lbl_color = ped_status_label[ped_state]
    draw.text((bx0 + 290, by0 + 122), p_lbl_text, fill=p_lbl_color)

    draw.rounded_rectangle([bx0 + 20, by0 + 165, bx1 - 20, by1 - 20], radius=8, fill=(35, 42, 55, 200))
    if ped_state == "PED_GREEN":
        info_desc = "Auto ferme al rosso in coda | Pedoni transitano sulle strisce"
        info_col = (140, 240, 180, 255)
    elif veh_state == "VEHICLE_YELLOW":
        info_desc = "Auto in decelerazione prima delle strisce | Pedoni in attesa"
        info_col = (255, 220, 100, 255)
    else:
        info_desc = "Auto a velocita sostenuta | Pedoni fermi al limite del marciapiede"
        info_col = (180, 215, 255, 255)
    draw.text((bx0 + 35, by0 + 175), info_desc, fill=info_col)


def apply_soft_lateral_repulsion(active_pedestrians):
    """
    Rileva eventuali vicinanze residue tra pedoni attivi e applica una separazione
    laterale morbida lungo l'asse Y per garantire l'assoluta assenza di sovrapposizioni.
    """
    n = len(active_pedestrians)
    for i in range(n):
        p1 = active_pedestrians[i]
        if not p1.is_active or p1.state == "exited":
            continue
        for j in range(i + 1, n):
            p2 = active_pedestrians[j]
            if not p2.is_active or p2.state == "exited":
                continue

            dx = abs(p1.cur_x - p2.cur_x)
            dy = abs(p1.cur_y - p2.cur_y)

            # Se si trovano troppo vicini in entrambe le dimensioni
            if dx < 140.0 and dy < 60.0:
                push_y = (60.0 - dy) * 0.5
                if p1.cur_y <= p2.cur_y:
                    p1.cur_y -= push_y
                    p2.cur_y += push_y
                else:
                    p1.cur_y += push_y
                    p2.cur_y -= push_y


def generate_extended_simulation(bg_path, assets_dir, output_path,
                                 duration_sec=120.0, fps=30, scale_output=1.0, seed=None):
    """Genera la simulazione da 2 minuti con anti-sovrapposizione pedoni e FSM multi-ciclo."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Immagine di sfondo non trovata: {bg_path}")

    print("\n" + "="*70)
    print("🚦 CROSSSENSE — SIMULAZIONE STRADALE CONTINUA (2 MINUTI)")
    print("="*70)
    print(f"  • Durata totale: {duration_sec} secondi ({fps} fps = {int(duration_sec*fps)} frame)")
    print("  • Gestione anti-sovrapposizione attiva: corsie separate e slot dedicati")
    print("  • Cicli semaforici multipli (~35s per ciclo con alternanza completa)")
    print("  • Uscita di scena dei pedoni e velocità elevata per le auto")
    print("  • Esattamente 1 carrozzina generata a tempo casuale")

    sprites = load_all_assets(assets_dir)
    base_bg = Image.open(bg_path).convert("RGBA")
    orig_w, orig_h = base_bg.size

    fsm = RepeatingTrafficLightFSM(cycle_len=35.0, t_yellow=18.0, t_ped_green=22.0, t_clearance=32.0)

    # 1. GENERAZIONE VEICOLI DISTRIBUITI NEL TEMPO
    vehicles = []
    t_spawn = 1.0
    v_idx = 0
    while t_spawn < duration_sec - 10:
        v_type = "Ambulanza" if random.random() < 0.20 else "Macchina"
        spd = random.uniform(480.0, 540.0) if v_type == "Macchina" else random.uniform(530.0, 590.0)
        vehicles.append(DynamicVehicle(v_type, spawn_time=t_spawn, base_speed=spd))
        print(f"  🚗 Veicolo #{v_idx+1:02d}: {v_type:10s} (Spawn t={t_spawn:05.1f}s, Vel={spd:.0f} px/s)")
        t_spawn += random.uniform(3.0, 7.5)
        v_idx += 1

    # 2. GENERAZIONE PEDONI DISTRIBUITI NEL TEMPO CON ALLOCAZIONE SLOT NON-OVERLAPPING
    pedestrians = []
    # Posizionamento della SINGOLA carrozzina a un tempo casuale
    wheelchair_time = random.uniform(15.0, 95.0)
    wheelchair_is_lr = (random.random() < 0.5)
    wheelchair_sprite = "Carrozzina_LR" if wheelchair_is_lr else "Carrozzina_RL"

    # Corsia e slot dedicati per la carrozzina
    wheelchair_track_y = 1345 if wheelchair_is_lr else 1225
    wheelchair_slot = WAITING_SLOTS_LEFT[0] if wheelchair_is_lr else WAITING_SLOTS_RIGHT[0]
    pedestrians.append(AntiOverlapPedestrian(wheelchair_sprite, spawn_time=wheelchair_time,
                                            is_lr=wheelchair_is_lr, target_crossing_y=wheelchair_track_y,
                                            waiting_slot=wheelchair_slot))
    print(f"\n  ♿ CARROZZINA UNICA: {wheelchair_sprite} (Spawn t={wheelchair_time:05.1f}s, Dir={'SX ➜ DX' if wheelchair_is_lr else 'DX ➜ SX'})")

    # Generazione degli altri pedoni con rotazione ordinata di corsie e slot d'attesa
    p_time = 0.5
    p_idx = 0
    lr_count = 1 if wheelchair_is_lr else 0
    rl_count = 1 if not wheelchair_is_lr else 0

    while p_time < duration_sec - 15:
        if abs(p_time - wheelchair_time) < 2.5:
            p_time += 3.5
            continue

        is_lr = (random.random() < 0.5)
        if is_lr:
            sprite_name = random.choice(SPRITES_LR)
            # Assegna una corsia Y e uno slot d'attesa distinti
            track_y = TRACKS_LR[lr_count % len(TRACKS_LR)]
            slot = WAITING_SLOTS_LEFT[(lr_count + 1) % len(WAITING_SLOTS_LEFT)]
            lr_count += 1
        else:
            sprite_name = random.choice(SPRITES_RL)
            track_y = TRACKS_RL[rl_count % len(TRACKS_RL)]
            slot = WAITING_SLOTS_RIGHT[(rl_count + 1) % len(WAITING_SLOTS_RIGHT)]
            rl_count += 1

        ped = AntiOverlapPedestrian(sprite_name, spawn_time=p_time, is_lr=is_lr,
                                    target_crossing_y=track_y, waiting_slot=slot)
        pedestrians.append(ped)
        p_time += random.uniform(4.0, 7.5)
        p_idx += 1

    print(f"  🚶 Pedoni totali generati: {len(pedestrians)} distribuiti su corsie e slot distanziati")
    print("-"*70)

    # 3. Video Writer
    out_w = int(orig_w * scale_output)
    out_h = int(orig_h * scale_output)
    total_frames = int(duration_sec * fps)
    dt = 1.0 / float(fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))
    if not video_writer.isOpened():
        raise RuntimeError(f"Impossibile aprire VideoWriter su {output_path}")

    print(f"[Rendering] Generazione {total_frames} frame a {out_w}x{out_h} ({duration_sec}s a {fps} fps)...")

    # 4. Rendering Loop
    for f_idx in range(total_frames):
        current_time = f_idx * dt
        veh_state, ped_state = fsm.get_state(current_time)

        # Aggiornamento fisica veicoli
        for i, veh in enumerate(vehicles):
            leader = None
            for j in range(i):
                if vehicles[j].is_active and not vehicles[j].has_exited and vehicles[j].cur_y > veh.cur_y:
                    if leader is None or vehicles[j].cur_y < leader.cur_y:
                        leader = vehicles[j]
            veh.update(dt, current_time, fsm, leader_vehicle=leader)

        # Aggiornamento fisica pedoni con verifica mutua delle distanze
        active_ped_list = [p for p in pedestrians if p.is_active and p.state != "exited"]
        for ped in pedestrians:
            ped.update(dt, current_time, fsm, active_pedestrians=active_ped_list)

        # Repulsione laterale morbida anticollisione per zero sovrapposizioni
        apply_soft_lateral_repulsion([p for p in pedestrians if p.is_active and p.state != "exited"])

        # Composizione grafica del frame
        frame_canvas = base_bg.copy()

        poses = []
        for veh in vehicles:
            vx, vy, vscale, vvis = veh.get_pose()
            if vvis and vx is not None and vy is not None:
                poses.append((veh.sprite_name, vx, vy, vscale))

        for ped in pedestrians:
            px, py, pscale, pvis = ped.get_pose(current_time)
            if pvis and px is not None and py is not None:
                poses.append((ped.sprite_name, px, py, pscale))

        # Ordinamento prospettico Y (oggetti in alto disegnati prima)
        poses.sort(key=lambda item: item[2])

        for s_name, x, y, scale in poses:
            if s_name in sprites:
                overlay_rgba(frame_canvas, sprites[s_name], x, y, scale=scale)

        # HUD Semaforico evidente
        draw_prominent_hud(frame_canvas, current_time, veh_state, ped_state)

        # Scrittura video
        if scale_output != 1.0:
            frame_to_save = frame_canvas.resize((out_w, out_h), Image.Resampling.BILINEAR)
        else:
            frame_to_save = frame_canvas

        frame_rgb = frame_to_save.convert("RGB")
        frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)

        if (f_idx + 1) % 60 == 0 or (f_idx + 1) == total_frames:
            pct = ((f_idx + 1) / total_frames) * 100
            print(f"      Frame renderizzati: {f_idx + 1}/{total_frames} ({pct:.0f}%)", end="\r")

    video_writer.release()
    print(f"\n[SUCCESSO] Video da 2 minuti salvato con successo in: {output_path}\n")


def main():
    parser = argparse.ArgumentParser(description="CrossSense - Simulazione Stradale Continua 2 Minuti (Anti-Overlap)")
    parser.add_argument("--background", type=str, default=DEFAULT_BG, help="Path immagine sfondo")
    parser.add_argument("--assets-dir", type=str, default=ASSETS_DIR, help="Path cartella assets")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Path video MP4 di output")
    parser.add_argument("--duration", type=float, default=120.0, help="Durata video in secondi (default: 120s = 2 min)")
    parser.add_argument("--fps", type=int, default=30, help="Framerate (fps)")
    parser.add_argument("--scale-output", type=float, default=1.0, help="Scala risoluzione (1.0 = 2528x1696 nativa)")
    parser.add_argument("--seed", type=int, default=None, help="Seed casuale opzionale")

    args = parser.parse_args()

    generate_extended_simulation(
        bg_path=args.background,
        assets_dir=args.assets_dir,
        output_path=args.output,
        duration_sec=args.duration,
        fps=args.fps,
        scale_output=args.scale_output,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
