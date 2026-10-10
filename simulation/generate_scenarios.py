#!/usr/bin/env python3
"""
CrossSense — Generatore Scenari di Simulazione
Produce i 5 scenari specifici richiesti senza alcun overlay semaforico (vista telecamera pulita):

  output_1.mp4: Macchine ferme e pedoni che attraversano regolarmente
  output_2.mp4: Macchine in transito e pedoni fermi sul marciapiede
  output_3.mp4: Macchina in lontananza e pedone che passa illegalmente
  output_4.mp4: Macchine ferme, pedoni normali che passano e vanno via,
                mentre un pedone più lento (carrozzina) rimane da solo a finire l'attraversamento
  output_5.mp4: 1 macchina ferma e 2 pedoni sulle strisce; arriva un'ambulanza,
                i pedoni sgomberano rapidamente e i veicoli ripartono immediatamente

Utilizzo:
  python simulation/generate_scenarios.py --all
  python simulation/generate_scenarios.py --scenario 1
"""

import os
import sys
import math
import argparse
import numpy as np
from PIL import Image
import cv2

# Percorsi di base
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(WORKSPACE_DIR, "assets")
DEFAULT_BG = os.path.join(ASSETS_DIR, "StartingImage.jpeg")
SIM_DIR = os.path.dirname(os.path.abspath(__file__))

# Asset disponibili
ALL_SPRITE_NAMES = [
    "Ambulanza", "Macchina", "Carrozzina_LR", "Carrozzina_RL",
    "Donna_LR", "Donna_RL", "Uomo_LR", "Uomo_RL"
]

# Coordinate corsia avvicinamento (senza drift)
LANE_APP_X_TOP = 1220
LANE_APP_Y_TOP = 240
LANE_APP_X_BOT = 960
LANE_APP_Y_BOT = 1696
STOP_LINE_Y = 820
QUEUE_SPACING_Y = 260

# ==============================================================================
# MODELLO PROSPETTICO DELLA STRADA E CINEMATICA (40 km/h)
# ==============================================================================
# 40 km/h = 11.11 m/s.
# Nella prospettiva della camera:
# - In primo piano (Y = 1350 px, altezza attraversamento pedonale): 1 metro ≈ 30-32 px.
#   Velocità corrispondente a 40 km/h a Y=1350: ~340 px/s.
# - A Y=820 px (linea di arresto semaforo): 1 metro ≈ 18-20 px.
#   Velocità corrispondente a 40 km/h a Y=820: ~210 px/s.
# - A Y=240 px (orizzonte / inizio corsia): 1 metro ≈ 6-7 px.
#   Velocità corrispondente a 40 km/h a Y=240: ~75 px/s.
# Definiamo la velocità in px/s in funzione della coordinata Y per un moto a velocità reale costante (~40 km/h).

def get_speed_40kmh(y):
    """Restituisce la velocità apparente in pixel/secondo per un veicolo a circa 40 km/h."""
    ratio = (y - LANE_APP_Y_TOP) / float(LANE_APP_Y_BOT - LANE_APP_Y_TOP)
    ratio = max(0.0, min(1.2, ratio))
    # Da ~75 px/s all'orizzonte fino a ~360 px/s in primo piano
    return 75.0 + 285.0 * (ratio ** 1.15)


# Limiti laterali per uscita completa di scena
EXIT_LEFT_X = -150
EXIT_RIGHT_X = 2680

# Coordinate marciapiede / inizio strisce pedonali:
# Sinistra: marciapiede a X = 560-600.
# Destra: marciapiede a X = 2020-2060.
CROSSING_START_LEFT_X = 580
CROSSING_START_RIGHT_X = 2040

# Fasce di attraversamento
TRACKS_RL = [1190, 1225, 1260]
TRACKS_LR = [1310, 1345, 1380]


def load_all_assets(assets_dir):
    """Carica tutti gli sprite PNG presenti nella cartella assets."""
    sprites = {}
    for name in ALL_SPRITE_NAMES:
        filename = f"{name}.png"
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            sprites[name] = img
        else:
            print(f"[AVVISO] File {filename} non trovato in {assets_dir}")
    return sprites


def get_vehicle_scale(y):
    """Scala prospettica per i veicoli lungo la carreggiata."""
    ratio = (y - LANE_APP_Y_TOP) / float(LANE_APP_Y_BOT - LANE_APP_Y_TOP)
    ratio = max(0.0, min(1.3, ratio))
    return 0.35 + 1.15 * (ratio ** 1.25)


def get_app_vehicle_x(y):
    """Coordinata X della corsia in base a Y."""
    ratio = (y - LANE_APP_Y_TOP) / float(LANE_APP_Y_BOT - LANE_APP_Y_TOP)
    return int(LANE_APP_X_TOP + (LANE_APP_X_BOT - LANE_APP_X_TOP) * ratio)


def overlay_rgba(background_img, sprite, center_x, center_y, scale=1.0):
    """Sovrapposizione standard diretta (modalità classica)."""
    if scale <= 0.05:
        return
    orig_w, orig_h = sprite.size
    new_w = max(4, int(orig_w * scale))
    new_h = max(4, int(orig_h * scale))
    resized = sprite.resize((new_w, new_h), Image.Resampling.LANCZOS)
    top_left_x = int(center_x - new_w // 2)
    top_left_y = int(center_y - new_h // 2)
    background_img.alpha_composite(resized, (top_left_x, top_left_y))


# ==============================================================================
# PIPELINE DI RENDERING AVANZATO: POST-PROCESSING & FOTOREALISMO
# ==============================================================================

def draw_contact_shadow(draw, center_x, center_y, sprite_w, sprite_h, is_vehicle=False, opacity=120):
    """
    Disegna l'ombra di contatto reale proiettata a terra sul manto stradale.
    La luce del sole proviene dall'alto-sinistra; l'ombra si allunga verso il basso-destra.
    """
    if is_vehicle:
        # Ombra di un veicolo: sagoma ampia sotto il telaio e le 4 ruote
        shadow_w = int(sprite_w * 0.95)
        shadow_h = int(sprite_h * 0.28)
        # Offset verso il basso e leggermente a destra (coerente con l'illuminazione della scena)
        s_cx = int(center_x + sprite_w * 0.04)
        s_cy = int(center_y + sprite_h * 0.42)
    else:
        # Ombra di un pedone / carrozzina: ellisse concentrata sotto la base dei piedi
        shadow_w = int(sprite_w * 0.70)
        shadow_h = int(sprite_h * 0.16)
        s_cx = int(center_x + sprite_w * 0.05)
        s_cy = int(center_y + sprite_h * 0.45)

    bbox = [s_cx - shadow_w // 2, s_cy - shadow_h // 2,
            s_cx + shadow_w // 2, s_cy + shadow_h // 2]
    # Tonalità scura dell'asfalto (ombra morbida)
    draw.ellipse(bbox, fill=(15, 18, 20, opacity))


def harmonize_sprite(sprite, mode="post"):
    """
    Armonizzazione cromatica e tonale dello sprite per integrarlo nel background reale:
    - Adatta il contrasto e la luminosità per eliminare l'effetto 'ritaglio'
    - Se mode=='fotoreal', sfuma leggermente i contorni per fusione perfetta col sensore
    """
    # Converti in RGBA numpy
    arr = np.array(sprite, dtype=np.float32)
    alpha = arr[:, :, 3] / 255.0
    rgb = arr[:, :, :3]

    if mode == "post":
        # Leggera calibrazione dell'esposizione e del punto di nero (asfalto riflesso)
        rgb = rgb * 0.94 + 5.0
        # Aumenta coerenza con la luce diffusa
        rgb[:, :, 0] *= 0.98  # R
        rgb[:, :, 2] *= 1.02  # B leggermente freddo
    elif mode == "fotoreal":
        # Fusione tonale più profonda, micro-abbassamento saturazione da telecamera stradale
        gray = np.mean(rgb, axis=2, keepdims=True)
        rgb = rgb * 0.88 + gray * 0.12  # desaturazione parziale 12%
        rgb = rgb * 0.92 + 8.0

    np.clip(rgb, 0, 255, out=rgb)
    arr[:, :, :3] = rgb

    if mode == "fotoreal":
        # Ammorbidimento bordi alpha (anti-aliasing subpixel ottico)
        alpha_blurred = cv2.GaussianBlur(alpha, (3, 3), 0.5)
        arr[:, :, 3] = alpha_blurred * 255.0

    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")


def apply_cctv_sensor_effects(frame_bgr, mode="post", frame_idx=0):
    """
    Emulazione ottica ed elettronica di una vera telecamera di videosorveglianza semaforica:
    - Grana del sensore CMOS (Sensor Noise variabile)
    - Compressione video broadcast/RTSP realistica
    - Leggera aberrazione cromatica periferica
    - Vignettatura ottica della lente
    """
    h, w = frame_bgr.shape[:2]
    out = frame_bgr.copy().astype(np.float32)

    if mode == "post":
        # 1. Micro-grana sensore CCTV (rumore gaussiano lieve)
        np.random.seed((frame_idx * 17) % 100000)
        noise = np.random.normal(0, 3.2, (h, w, 3)).astype(np.float32)
        out = np.clip(out + noise, 0, 255)

        # 2. Leggero contrasto s-curve tipico dei DSP di telecamere da palo
        out = (out / 255.0)
        out = (out ** 1.04) * 255.0
        out = np.clip(out, 0, 255).astype(np.uint8)

    elif mode == "fotoreal":
        # 1. Grana ad alta frequenza tipica dei sensori 2K/4K CCTV da incrocio
        np.random.seed((frame_idx * 23) % 100000)
        noise = np.random.normal(0, 4.0, (h, w, 3)).astype(np.float32)
        out = np.clip(out + noise, 0, 255)

        # 2. Aberrazione cromatica sottile ai margini della lente
        b, g, r = cv2.split(out)
        # Shift orizzontale di 1 pixel del canale blu e rosso (dispersione ottica tipica)
        r_shifted = np.roll(r, 1, axis=1)
        b_shifted = np.roll(b, -1, axis=1)
        out = cv2.merge([b_shifted, g, r_shifted])

        # 3. Leggera vignettatura della lente fissa grandangolare
        y, x = np.ogrid[:h, :w]
        cx, cy = w / 2.0, h / 2.0
        max_dist = np.hypot(cx, cy)
        dist_map = np.hypot(x - cx, y - cy) / max_dist
        vignette = 1.0 - 0.12 * (dist_map ** 2)
        out = out * vignette[:, :, np.newaxis]
        out = np.clip(out, 0, 255).astype(np.uint8)

        # 4. Compressione dinamica tipica stream RTSP/H.264
        # Simula la leggera perdita di micro-contrasto delle codifiche IP
        out = cv2.bilateralFilter(out, d=3, sigmaColor=15, sigmaSpace=15)

    return out


# ==============================================================================
# DEFINIZIONE CLASSI ATTORI SCENARIO
# ==============================================================================

class ScenarioPedestrian:
    """Pedone con waypoint o traiettorie flessibili e orientamento."""
    def __init__(self, sprite_name, start_x, start_y, target_x, target_y,
                 start_time, speed, scale=0.95):
        self.sprite_name = sprite_name
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.start_time = start_time
        self.speed = speed
        self.scale = scale
        self.is_wheelchair = "Carrozzina" in sprite_name

        self.cur_x = start_x
        self.cur_y = start_y
        self.is_active = False
        self.has_exited = False

        # Supporto per inversione / cambio destinazione (es. Scenario 5 emergenza)
        self.escape_time = None
        self.escape_target_x = None
        self.escape_speed = None
        self.escape_sprite_name = None

    def trigger_escape_shortest(self, escape_time, left_exit=EXIT_LEFT_X, right_exit=EXIT_RIGHT_X, speed_mult=1.5):
        """
        Calcola la via di fuga più breve (distanza minore dal marciapiede/bordo più vicino).
        Se inverte direzione, aggiorna lo sprite (da _LR a _RL o viceversa).
        """
        self.escape_time = escape_time
        dist_to_left = abs(self.cur_x - left_exit)
        dist_to_right = abs(self.cur_x - right_exit)

        if dist_to_left < dist_to_right:
            self.escape_target_x = left_exit
            # Se andava a destra (_LR), tornando a sinistra deve guardare verso sinistra (_RL)
            if "_LR" in self.sprite_name:
                self.escape_sprite_name = self.sprite_name.replace("_LR", "_RL")
            else:
                self.escape_sprite_name = self.sprite_name
        else:
            self.escape_target_x = right_exit
            # Se andava a sinistra (_RL), tornando a destra deve guardare verso destra (_LR)
            if "_RL" in self.sprite_name:
                self.escape_sprite_name = self.sprite_name.replace("_RL", "_LR")
            else:
                self.escape_sprite_name = self.sprite_name

        self.escape_speed = self.speed * speed_mult

    def update(self, dt, current_time):
        if current_time < self.start_time:
            self.is_active = False
            return
        if self.has_exited:
            self.is_active = False
            return

        self.is_active = True

        # Verifica se è scattata la fuga/inversione più breve
        active_target_x = self.target_x
        active_target_y = self.target_y
        active_speed = self.speed

        if self.escape_time is not None and current_time >= self.escape_time:
            active_target_x = self.escape_target_x
            active_speed = self.escape_speed
            if self.escape_sprite_name:
                self.sprite_name = self.escape_sprite_name

        dx = active_target_x - self.cur_x
        dy = active_target_y - self.cur_y
        dist = math.hypot(dx, dy)

        if dist > 5.0 and active_speed > 0:
            step = min(dist, active_speed * dt)
            self.cur_x += (dx / dist) * step
            self.cur_y += (dy / dist) * step
        elif active_speed == 0:
            # Pedone fermo in attesa
            pass
        else:
            self.has_exited = True
            self.is_active = False

    def get_pose(self, current_time):
        if not self.is_active or self.has_exited:
            return None, None, 0.0, False
        step_bob = math.sin((current_time - self.start_time) * 8.0) * 3.0 if (not self.is_wheelchair and self.speed > 0) else 0.0
        return int(self.cur_x), int(self.cur_y + step_bob), self.scale, True


class ScenarioVehicle:
    """Veicolo con cinematica a ~40 km/h (fermo, in transito, frenata o ripartenza)."""
    def __init__(self, sprite_name, spawn_time, mode="stop",
                 stop_y=STOP_LINE_Y, speed_nominal=40.0, restart_time=None):
        self.sprite_name = sprite_name
        self.spawn_time = spawn_time
        self.mode = mode  # "transit", "stop", "brake_emergency", "restart"
        self.stop_y = stop_y
        self.restart_time = restart_time
        self.speed_nominal = speed_nominal  # km/h di riferimento

        self.cur_y = LANE_APP_Y_TOP
        self.cur_speed = get_speed_40kmh(self.cur_y)
        self.is_active = False
        self.has_exited = False

    def update(self, dt, current_time):
        if current_time < self.spawn_time:
            self.is_active = False
            return
        if self.has_exited:
            self.is_active = False
            return

        self.is_active = True
        base_speed = get_speed_40kmh(self.cur_y)

        if self.mode == "transit":
            # Transito fluido a velocità di circa 40 km/h calibrata in prospettiva
            self.cur_speed = base_speed
            self.cur_y += self.cur_speed * dt

        elif self.mode == "stop":
            # Rallenta dolcemente e si arresta alla posizione stop_y
            dist_to_stop = self.stop_y - self.cur_y
            if dist_to_stop > 10:
                target_v = min(base_speed, math.sqrt(2.0 * 130.0 * max(0.0, dist_to_stop)))
                self.cur_speed = max(25.0, target_v)
                self.cur_y += self.cur_speed * dt
            else:
                self.cur_y = self.stop_y
                self.cur_speed = 0.0

        elif self.mode == "brake_emergency":
            # Macchina che viaggia a 40 km/h e frena prima della linea
            dist_to_stop = self.stop_y - self.cur_y
            if dist_to_stop > 10:
                target_v = min(base_speed, math.sqrt(2.0 * 180.0 * max(0.0, dist_to_stop)))
                self.cur_speed = max(25.0, target_v)
                self.cur_y += self.cur_speed * dt
            else:
                self.cur_y = self.stop_y
                self.cur_speed = 0.0

        elif self.mode == "restart":
            # Fermo prima di restart_time, poi riparte accelerando fino a 40 km/h
            if self.restart_time is None or current_time < self.restart_time:
                dist_to_stop = self.stop_y - self.cur_y
                if dist_to_stop > 10:
                    target_v = min(base_speed, math.sqrt(2.0 * 130.0 * max(0.0, dist_to_stop)))
                    self.cur_speed = max(25.0, target_v)
                    self.cur_y += self.cur_speed * dt
                else:
                    self.cur_y = self.stop_y
                    self.cur_speed = 0.0
            else:
                # Riparte con accelerazione realistica
                self.cur_speed = min(base_speed, self.cur_speed + 160.0 * dt)
                self.cur_y += self.cur_speed * dt

        if self.cur_y > LANE_APP_Y_BOT + 150:
            self.has_exited = True
            self.is_active = False

    def get_pose(self):
        if not self.is_active or self.has_exited:
            return None, None, 0.0, False
        cur_x = get_app_vehicle_x(self.cur_y)
        scale = get_vehicle_scale(self.cur_y)
        return int(cur_x), int(self.cur_y), scale, True


# ==============================================================================
# COSTRUZIONE DEI 5 SCENARI SPECIFICI (MASSIMO 8 ATTORI TOTALI PER VIDEO)
# ==============================================================================

def build_scenario_1():
    """
    Scenario 1: Macchine ferme e pedoni che attraversano regolarmente.
    Totale attori: 2 veicoli + 4 pedoni = 6 attori (<= 8).
    La seconda macchina entra con un distanziamento temporale e spaziale netto (spazio di sicurezza ampio).
    """
    duration = 12.0
    vehicles = [
        ScenarioVehicle("Macchina", spawn_time=0.0, mode="stop", stop_y=STOP_LINE_Y),
        ScenarioVehicle("Macchina", spawn_time=1.8, mode="stop", stop_y=STOP_LINE_Y - (QUEUE_SPACING_Y + 40))
    ]
    pedestrians = [
        ScenarioPedestrian("Donna_LR", start_x=450, start_y=1340, target_x=EXIT_RIGHT_X, target_y=1340,
                           start_time=0.5, speed=200.0),
        ScenarioPedestrian("Uomo_RL", start_x=2120, start_y=1210, target_x=EXIT_LEFT_X, target_y=1210,
                           start_time=0.2, speed=190.0),
        ScenarioPedestrian("Uomo_LR", start_x=360, start_y=1380, target_x=EXIT_RIGHT_X, target_y=1380,
                           start_time=1.2, speed=195.0),
        ScenarioPedestrian("Donna_RL", start_x=2220, start_y=1255, target_x=EXIT_LEFT_X, target_y=1255,
                           start_time=1.5, speed=200.0)
    ]
    return vehicles, pedestrians, duration


def build_scenario_2():
    """
    Scenario 2: Macchine in transito (40 km/h) e pedoni fermi all'inizio delle strisce ad aspettare.
    Totale attori: 3 veicoli + 4 pedoni = 7 attori (<= 8).
    I pedoni sono posizionati esattamente all'imbocco delle strisce (bordo marciapiede).
    """
    duration = 13.0
    vehicles = [
        ScenarioVehicle("Macchina", spawn_time=0.0, mode="transit"),
        ScenarioVehicle("Macchina", spawn_time=3.8, mode="transit"),
        ScenarioVehicle("Ambulanza", spawn_time=7.5, mode="transit")
    ]
    # Pedoni posizionati all'inizio delle strisce:
    # A sinistra a X ≈ 580 (corsie LR), a destra a X ≈ 2040 (corsie RL)
    pedestrians = [
        ScenarioPedestrian("Donna_LR", start_x=CROSSING_START_LEFT_X, start_y=1330,
                           target_x=CROSSING_START_LEFT_X, target_y=1330,
                           start_time=0.0, speed=0.0),
        ScenarioPedestrian("Uomo_LR", start_x=CROSSING_START_LEFT_X - 60, start_y=1370,
                           target_x=CROSSING_START_LEFT_X - 60, target_y=1370,
                           start_time=0.0, speed=0.0),
        ScenarioPedestrian("Donna_RL", start_x=CROSSING_START_RIGHT_X, start_y=1210,
                           target_x=CROSSING_START_RIGHT_X, target_y=1210,
                           start_time=0.0, speed=0.0),
        ScenarioPedestrian("Uomo_RL", start_x=CROSSING_START_RIGHT_X + 60, start_y=1255,
                           target_x=CROSSING_START_RIGHT_X + 60, target_y=1255,
                           start_time=0.0, speed=0.0)
    ]
    return vehicles, pedestrians, duration


def build_scenario_3():
    """
    Scenario 3: Macchina in lontananza a 40 km/h e pedone che passa illegalmente.
    Totale attori: 1 veicolo + 1 pedone = 2 attori (<= 8).
    """
    duration = 10.0
    vehicles = [
        ScenarioVehicle("Macchina", spawn_time=0.0, mode="brake_emergency", stop_y=STOP_LINE_Y)
    ]
    pedestrians = [
        ScenarioPedestrian("Uomo_LR", start_x=CROSSING_START_LEFT_X, start_y=1340, target_x=EXIT_RIGHT_X, target_y=1340,
                           start_time=0.5, speed=250.0)
    ]
    return vehicles, pedestrians, duration


def build_scenario_4():
    """
    Scenario 4: Macchine ferme, pedoni normali via, carrozzina lenta rimane da sola ad attraversare.
    Totale attori: 2 veicoli + 3 pedoni = 5 attori (<= 8).
    """
    duration = 17.0
    vehicles = [
        ScenarioVehicle("Macchina", spawn_time=0.0, mode="stop", stop_y=STOP_LINE_Y),
        ScenarioVehicle("Ambulanza", spawn_time=0.4, mode="stop", stop_y=STOP_LINE_Y - QUEUE_SPACING_Y)
    ]
    pedestrians = [
        ScenarioPedestrian("Donna_LR", start_x=CROSSING_START_LEFT_X, start_y=1360, target_x=EXIT_RIGHT_X, target_y=1360,
                           start_time=0.2, speed=230.0),
        ScenarioPedestrian("Uomo_RL", start_x=CROSSING_START_RIGHT_X, start_y=1210, target_x=EXIT_LEFT_X, target_y=1210,
                           start_time=0.4, speed=220.0),
        # Carrozzina lenta che inizia e prosegue da sola
        ScenarioPedestrian("Carrozzina_LR", start_x=CROSSING_START_LEFT_X - 50, start_y=1310, target_x=EXIT_RIGHT_X, target_y=1310,
                           start_time=0.8, speed=95.0)
    ]
    return vehicles, pedestrians, duration


def build_scenario_5():
    """
    Scenario 5: 1 macchina ferma e 2 pedoni ad attraversare; arriva un'ambulanza,
                i pedoni sgomberano percorrendo la distanza più breve (anche tornando sui propri passi),
                e i veicoli ripartono immediatamente.
    Totale attori: 2 veicoli + 2 pedoni = 4 attori (<= 8).
    """
    duration = 14.0
    # Al secondo t=3.8 l'ambulanza arriva in emergenza.
    # Pedone 1 (Donna_LR) è partita da sinistra (580) e a t=3.8 si trova circa a X=1080 (ancora più vicina al lato sinistro < 1300):
    # torna indietro sui propri passi verso sinistra (distanza minore)!
    # Pedone 2 (Uomo_RL) è partito da destra (2040) e a t=3.8 si trova a X=1540 (ancora più vicino al lato destro > 1300):
    # torna indietro sui propri passi verso destra (distanza minore)!
    # Una volta liberata la strada (circa t=6.2), i veicoli ripartono a 40 km/h.
    veh_car = ScenarioVehicle("Macchina", spawn_time=0.0, mode="restart",
                              stop_y=STOP_LINE_Y, restart_time=6.4)
    veh_amb = ScenarioVehicle("Ambulanza", spawn_time=1.0, mode="restart",
                              stop_y=STOP_LINE_Y - QUEUE_SPACING_Y, restart_time=7.1)
    vehicles = [veh_car, veh_amb]

    ped_1 = ScenarioPedestrian("Donna_LR", start_x=CROSSING_START_LEFT_X, start_y=1340,
                               target_x=EXIT_RIGHT_X, target_y=1340,
                               start_time=0.2, speed=135.0)
    ped_2 = ScenarioPedestrian("Uomo_RL", start_x=CROSSING_START_RIGHT_X, start_y=1220,
                               target_x=EXIT_LEFT_X, target_y=1220,
                               start_time=0.2, speed=135.0)

    # All'arrivo dell'ambulanza a t=3.8, i pedoni percepiscono l'emergenza, invertono la marcia
    # e corrono verso il marciapiede più vicino (fuga sulla distanza più breve)
    ped_1.trigger_escape_shortest(escape_time=3.8, left_exit=EXIT_LEFT_X, right_exit=EXIT_RIGHT_X, speed_mult=1.8)
    ped_2.trigger_escape_shortest(escape_time=3.8, left_exit=EXIT_LEFT_X, right_exit=EXIT_RIGHT_X, speed_mult=1.8)

    pedestrians = [ped_1, ped_2]
    return vehicles, pedestrians, duration


# ==============================================================================
# ENGINE DI RENDERING (SENZA HUD SEMAFORO)
# ==============================================================================

def render_scenario(bg_path, assets_dir, vehicles, pedestrians, duration, output_path, fps=30, mode="standard"):
    """
    Renderizza il video per lo scenario specificato.
    Modalità supportate:
      - 'standard': Rendering originale sprite diretto (stile attuale).
      - 'post': Post-Processing avanzato con contact shadows, armonizzazione colori ed emulazione sensore CCTV.
      - 'fotoreal': Fusione fotorealistica con subpixel anti-aliasing, aberrazione cromatica ottica, vignettatura e filtro lenti stradali.
    """
    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Sfondo non trovato: {bg_path}")

    from PIL import ImageDraw

    base_bg = Image.open(bg_path).convert("RGBA")
    orig_w, orig_h = base_bg.size
    sprites = load_all_assets(assets_dir)

    total_frames = int(duration * fps)
    dt = 1.0 / float(fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (orig_w, orig_h))
    if not video_writer.isOpened():
        raise RuntimeError(f"Impossibile aprire VideoWriter su {output_path}")

    print(f"  [Rendering ({mode.upper()})] {output_path} ({duration}s @ {fps}fps = {total_frames} frame)...")

    for f_idx in range(total_frames):
        current_time = f_idx * dt

        # Update fisica
        for v in vehicles:
            v.update(dt, current_time)
        for p in pedestrians:
            p.update(dt, current_time)

        frame_canvas = base_bg.copy()

        # Raccolta pose
        poses = []
        for v in vehicles:
            vx, vy, vscale, vvis = v.get_pose()
            if vvis and vx is not None and vy is not None:
                poses.append((v.sprite_name, vx, vy, vscale, True))

        for p in pedestrians:
            px, py, pscale, pvis = p.get_pose(current_time)
            if pvis and px is not None and py is not None:
                poses.append((p.sprite_name, px, py, pscale, False))

        # Ordinamento prospettico Y (lontani disegnati prima)
        poses.sort(key=lambda item: item[2])

        if mode in ("post", "fotoreal"):
            # 1. PASSAGGIO OMBRE: Proiezione a terra delle ombre di contatto su layer trasparente
            shadow_layer = Image.new("RGBA", (orig_w, orig_h), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)

            for s_name, x, y, scale, is_veh in poses:
                if s_name in sprites:
                    sp = sprites[s_name]
                    sw = int(sp.size[0] * scale)
                    sh = int(sp.size[1] * scale)
                    shadow_opacity = 110 if mode == "post" else 135
                    draw_contact_shadow(shadow_draw, x, y, sw, sh, is_vehicle=is_veh, opacity=shadow_opacity)

            # Sfocatura morbida delle ombre (penombra naturale)
            shadow_arr = np.array(shadow_layer)
            ksize = 11 if mode == "fotoreal" else 7
            shadow_arr = cv2.GaussianBlur(shadow_arr, (ksize, ksize), 0)
            shadow_layer = Image.fromarray(shadow_arr, mode="RGBA")
            frame_canvas.alpha_composite(shadow_layer)

            # 2. PASSAGGIO SPRITE ARMONIZZATI
            for s_name, x, y, scale, is_veh in poses:
                if s_name in sprites:
                    raw_sp = sprites[s_name]
                    harmonized_sp = harmonize_sprite(raw_sp, mode=mode)
                    overlay_rgba(frame_canvas, harmonized_sp, x, y, scale=scale)

        else:
            # MODALITÀ STANDARD (attuale, sprite diretti)
            for s_name, x, y, scale, is_veh in poses:
                if s_name in sprites:
                    overlay_rgba(frame_canvas, sprites[s_name], x, y, scale=scale)

        # Scrittura frame video (senza alcun HUD)
        frame_rgb = frame_canvas.convert("RGB")
        frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)

        # 3. PASSAGGIO EFFETTI SENSORE CCTV / TELECAMERA STRADALE
        if mode in ("post", "fotoreal"):
            frame_bgr = apply_cctv_sensor_effects(frame_bgr, mode=mode, frame_idx=f_idx)

        video_writer.write(frame_bgr)

        if (f_idx + 1) % 45 == 0 or (f_idx + 1) == total_frames:
            pct = ((f_idx + 1) / total_frames) * 100
            print(f"      Frame: {f_idx + 1}/{total_frames} ({pct:.0f}%)", end="\r")

    video_writer.release()
    print(f"\n  [OK] Salvato: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="CrossSense - Generatore 5 Scenari Dimostrativi")
    parser.add_argument("--scenario", type=int, choices=[1, 2, 3, 4, 5], help="Numero scenario (1-5)")
    parser.add_argument("--all", action="store_true", help="Genera tutti i 5 scenari")
    parser.add_argument("--fps", type=int, default=15, help="Framerate (default: 15)")
    parser.add_argument("--mode", type=str, choices=["standard", "post", "fotoreal"], default="standard",
                        help="Modalità rendering: standard (attuale), post (post-processing CCTV), fotoreal (fotorealistico ottico)")
    parser.add_argument("--output", type=str, default=None, help="Percorso file output personalizzato")

    args = parser.parse_args()

    scenarios_to_run = []
    if args.scenario:
        scenarios_to_run = [args.scenario]
    elif args.all:
        scenarios_to_run = [1, 2, 3, 4, 5]
    else:
        # Default: genera tutti i 5 scenari
        scenarios_to_run = [1, 2, 3, 4, 5]

    scenario_builders = {
        1: (build_scenario_1, "1) Macchine ferme e pedoni che attraversano regolarmente"),
        2: (build_scenario_2, "2) Macchine in transito e pedoni fermi al marciapiede"),
        3: (build_scenario_3, "3) Macchina in lontananza e pedone che passa illegalmente"),
        4: (build_scenario_4, "4) Macchine ferme, pedoni normali via, pedone lento (carrozzina) da solo"),
        5: (build_scenario_5, "5) Macchina ferma + pedoni, arriva ambulanza, pedoni via e ripartenza")
    }

    print("\n" + "="*70)
    print(f"🎬 CROSSSENSE — GENERATORE SCENARI (MODALITÀ: {args.mode.upper()})")
    print("="*70)

    for sc_num in scenarios_to_run:
        builder, title = scenario_builders[sc_num]
        if args.output:
            out_path = args.output
        else:
            output_dir = os.path.join(SIM_DIR, "output")
            os.makedirs(output_dir, exist_ok=True)
            out_filename = f"output_{sc_num}.mp4"
            out_path = os.path.join(output_dir, out_filename)

        print(f"\n▶ SCENARIO {sc_num}: {title}")
        vehicles, pedestrians, duration = builder()
        render_scenario(
            bg_path=DEFAULT_BG,
            assets_dir=ASSETS_DIR,
            vehicles=vehicles,
            pedestrians=pedestrians,
            duration=duration,
            output_path=out_path,
            fps=args.fps,
            mode=args.mode
        )

    print("\n" + "="*70)
    print("✅ TUTTI GLI SCENARI RICHIESTI SONO STATI GENERATI CON SUCCESSO!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
