#!/usr/bin/env python3
"""
Genera la presentazione PowerPoint 'Presentation.pptx' per il progetto CrossSense.
Sviluppato dal team Galileo Makers.
"""
import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 Widescreen layout: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Color Palette: Smart Application / Tech / Professional
    BG_DARK = RGBColor(15, 23, 42)       # Slate 900
    BG_LIGHT = RGBColor(248, 250, 252)   # Slate 50
    TEXT_MAIN = RGBColor(15, 23, 42)     # Dark Slate
    TEXT_MUTED = RGBColor(100, 116, 139) # Slate 500
    TEXT_LIGHT = RGBColor(241, 245, 249) # Slate 100
    TEXT_LIGHT_MUTED = RGBColor(148, 163, 184) # Slate 400
    ACCENT_CYAN = RGBColor(14, 165, 233) # Sky 500
    ACCENT_GREEN = RGBColor(16, 185, 129)# Emerald 500
    ACCENT_AMBER = RGBColor(245, 158, 11)# Amber 500
    CARD_BG = RGBColor(255, 255, 255)    # White
    CARD_BORDER = RGBColor(226, 232, 240)# Slate 200
    CARD_DARK = RGBColor(30, 41, 59)     # Slate 800

    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide, color):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def add_header(slide, tag_text, title_text, dark_mode=False):
        # Tag/Category
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.5), Inches(0.35))
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = tag_text.upper()
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = ACCENT_CYAN if dark_mode else RGBColor(2, 132, 199)

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.5), Inches(0.65))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_LIGHT if dark_mode else TEXT_MAIN

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        if border_color:
            shape.line.color.rgb = border_color
            shape.line.width = Pt(1.5)
        else:
            shape.line.fill.background()
        return shape

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Theme)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1, BG_DARK)

    # Accent decorative top bar
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.5), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT_CYAN
    bar.line.fill.background()

    # Project Title & Subtitle
    title_box = slide1.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(3.2))
    tf1 = title_box.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "SMART URBAN MOBILITY & IOT SAFETY"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(14)

    p1 = tf1.add_paragraph()
    p1.text = "Cross Sense"
    p1.font.size = Pt(50)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT
    p1.space_after = Pt(10)

    p2 = tf1.add_paragraph()
    p2.text = "A smart and safe solutions for crosswalks"
    p2.font.size = Pt(22)
    p2.font.color.rgb = TEXT_LIGHT_MUTED
    p2.space_after = Pt(20)

    # Bottom Metadata Card
    meta_card = add_card(slide1, Inches(0.8), Inches(5.2), Inches(11.733), Inches(1.5), CARD_DARK, RGBColor(51, 65, 85))
    meta_box = slide1.shapes.add_textbox(Inches(1.1), Inches(5.4), Inches(11.1), Inches(1.1))
    tf_meta = meta_box.text_frame
    tf_meta.word_wrap = True
    
    pm1 = tf_meta.paragraphs[0]
    pm1.text = "Team di Sviluppo: "
    pm1.font.size = Pt(14)
    pm1.font.bold = True
    pm1.font.color.rgb = ACCENT_CYAN
    run_team = pm1.add_run()
    run_team.text = "Galileo Makers"
    run_team.font.bold = True
    run_team.font.color.rgb = TEXT_LIGHT

    pm2 = tf_meta.add_paragraph()
    pm2.text = "Target Hardware: Arduino UNO Q (Dual-Core Linux MPU + STM32 MCU Zephyr RTOS) · HackTurin 2026"
    pm2.font.size = Pt(12)
    pm2.font.color.rgb = TEXT_LIGHT_MUTED
    pm2.space_before = Pt(6)

    # =========================================================================
    # SLIDE 2: Il Problema (Tempi non adattivi e Sicurezza)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2, BG_LIGHT)
    add_header(slide2, "Scenario e Problematiche", "I Limiti della Segnaletica Tradizionale")

    # Card 1: Tempi di attesa rigidi
    add_card(slide2, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    c1_box = slide2.shapes.add_textbox(Inches(1.1), Inches(1.85), Inches(5.0), Inches(4.7))
    tf_c1 = c1_box.text_frame
    tf_c1.word_wrap = True

    p = tf_c1.paragraphs[0]
    p.text = "TEMPI DI ATTESA RIGIDI E NON ADATTIVI"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(225, 29, 72)
    p.space_after = Pt(12)

    bullets_c1 = [
        ("Cicli a tempo fisso inefficienti: ", "I semafori convenzionali operano con temporizzazioni statiche che non riflettono l'effettiva presenza di pedoni o veicoli."),
        ("Attese inutili per il traffico: ", "Automobilisti bloccati con luce rossa anche in totale assenza di pedoni in attesa o in attraversamento."),
        ("Frustrazione dei pedoni: ", "L'obbligo di premere pulsanti fisici (spesso ignorati o poco igienici) genera attese ingiustificate, spingendo gli utenti ad attraversare con il rosso."),
        ("Mancanza di flessibilità: ", "Nessun supporto dinamico per persone a mobilità ridotta o carrozzine che necessitano di tempi di verde estesi.")
    ]
    for b_title, b_desc in bullets_c1:
        pb = tf_c1.add_paragraph()
        pb.space_after = Pt(10)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(11)
        r2.font.color.rgb = TEXT_MUTED

    # Card 2: Rischio Sicurezza e Conflitti
    add_card(slide2, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    c2_box = slide2.shapes.add_textbox(Inches(7.1), Inches(1.85), Inches(5.1), Inches(4.7))
    tf_c2 = c2_box.text_frame
    tf_c2.word_wrap = True

    p = tf_c2.paragraphs[0]
    p.text = "SICUREZZA E MANCATO RISPETTO DEL SEGNALE"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p.space_after = Pt(12)

    bullets_c2 = [
        ("Attraversamento con il Rosso: ", "Pedoni o ciclisti che impegnano le strisce improvvisamente mentre il semaforo veicolare è verde."),
        ("Veicoli che non rispettano il segnale: ", "Mancata precedenza o infrazione delle luci con rischio elevatissimo di collisione (crossing conflict)."),
        ("Utenti vulnerabili bloccati sulle strisce: ", "Pedoni lenti, anziani o persone in sedia a rotelle che rimangono intrappolati a metà carreggiata allo scadere del verde."),
        ("Totale 'cecità' degli impianti tradizionali: ", "I controllori semaforici standard non hanno alcuna percezione visiva dell'ingombro reale della carreggiata.")
    ]
    for b_title, b_desc in bullets_c2:
        pb = tf_c2.add_paragraph()
        pb.space_after = Pt(10)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(11)
        r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 3: La Visione di Cross Sense (Approccio Smart e Safe)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3, BG_LIGHT)
    add_header(slide3, "La Soluzione Cross Sense", "Un Attraversamento Smart, Consapevole e Protetto")

    pillars = [
        ("PERCEZIONE EDGE", "Computer Vision Locale",
         "Elaborazione video completamente on-device con reti neurali YOLO. Monitoraggio continuo e multi-classe delle zone di attesa, della corsia veicoli e dell'attraversamento pedonale senza dipendere dal cloud."),
        ("LOGICA ADATTIVA", "Controllo Real-Time MCU",
         "Chiamata pedonale automatica al rilevamento della presenza (800 ms di permanenza). Adattamento dinamico dei tempi: verde veicolare ridotto a 1s se la strada è vuota, esteso a 8s per mobilità ridotta."),
        ("SAFETY-FIRST", "Protezione da Conflitto & Fail-Safe",
         "Stato protetto (All-Red / Protected Stop) immediato se l'attraversamento è occupato durante il transito auto o in caso di anomalie di tracking. Watchdog hardware rigoroso a 1000 ms.")
    ]

    card_w = Inches(3.7)
    gap = Inches(0.3)
    start_x = Inches(0.8)

    for i, (tag, title, desc) in enumerate(pillars):
        cx = start_x + i * (card_w + gap)
        add_card(slide3, cx, Inches(1.6), card_w, Inches(4.3))
        
        # Color badge on top of card
        badge = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, cx, Inches(1.6), card_w, Inches(0.08))
        badge.fill.solid()
        badge.fill.fore_color.rgb = ACCENT_CYAN if i==0 else (ACCENT_GREEN if i==1 else RGBColor(225, 29, 72))
        badge.line.fill.background()

        tb = slide3.shapes.add_textbox(cx + Inches(0.25), Inches(1.85), card_w - Inches(0.5), Inches(3.9))
        tf = tb.text_frame
        tf.word_wrap = True

        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = ACCENT_CYAN if i==0 else (ACCENT_GREEN if i==1 else RGBColor(225, 29, 72))
        p_tag.space_after = Pt(6)

        p_t = tf.add_paragraph()
        p_t.text = title
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_MAIN
        p_t.space_after = Pt(14)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_MUTED

    # Bottom summary banner
    add_card(slide3, Inches(0.8), Inches(6.1), Inches(11.733), Inches(0.9), CARD_DARK, None)
    bb = slide3.shapes.add_textbox(Inches(1.1), Inches(6.25), Inches(11.1), Inches(0.6))
    tf_bb = bb.text_frame
    tf_bb.word_wrap = True
    p_bb = tf_bb.paragraphs[0]
    p_bb.text = "Risultato: "
    p_bb.font.size = Pt(12)
    p_bb.font.bold = True
    p_bb.font.color.rgb = ACCENT_GREEN
    r_bb = p_bb.add_run()
    r_bb.text = "Azzeramento delle attese a vuoto per i veicoli, tutela attiva degli utenti deboli ed eliminazione del rischio di collisione in caso di mancato rispetto del semaforo."
    r_bb.font.bold = False
    r_bb.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 4: Risoluzione Parte 1 - Architettura Hardware (Arduino UNO Q)
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4, BG_LIGHT)
    add_header(slide4, "Risoluzione Parte 1", "Hardware Imbarcato: La Piattaforma Eterogenea Arduino UNO Q")

    # Left: Specs and Architecture
    add_card(slide4, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    hw_tb1 = slide4.shapes.add_textbox(Inches(1.1), Inches(1.85), Inches(5.0), Inches(4.7))
    tf_hw1 = hw_tb1.text_frame
    tf_hw1.word_wrap = True

    p = tf_hw1.paragraphs[0]
    p.text = "COMPOSIZIONE HARDWARE BOARD"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(2, 132, 199)
    p.space_after = Pt(12)

    hw_items = [
        ("Architettura Dual-Core Eterogenea: ", "Combina un processore applicativo ad alte prestazioni Linux con un microcontrollore real-time dedicato alla sicurezza."),
        ("Linux Application Processor (MPU): ", "Core ARM aarch64 (Linux Kernel 6.16, 3.6 GiB RAM). Esegue il runtime di Computer Vision, le reti neurali e il Web Server HTTP."),
        ("Microcontrollore STM32 (MCU): ", "Core real-time governato da Zephyr RTOS. Esegue la macchina a stati finiti (FSM) del semaforo deterministica, isolata e immune da crash dell'OS."),
        ("Bus di Comunicazione Inter-Core: ", "RouterBridge IPC ultra-affidabile su canale seriale virtuale / RPC bidirezionale per lo scambio dati a bassa latenza.")
    ]
    for b_title, b_desc in hw_items:
        pb = tf_hw1.add_paragraph()
        pb.space_after = Pt(10)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(11)
        r2.font.color.rgb = TEXT_MUTED

    # Right: Hardware Features & Isolation
    add_card(slide4, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    hw_tb2 = slide4.shapes.add_textbox(Inches(7.1), Inches(1.85), Inches(5.1), Inches(4.7))
    tf_hw2 = hw_tb2.text_frame
    tf_hw2.word_wrap = True

    p = tf_hw2.paragraphs[0]
    p.text = "FUNZIONALITÀ FORNITE DALL'HARDWARE"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN
    p.space_after = Pt(12)

    hw_feats = [
        ("Separazione dei Domini di Sicurezza: ", "L'elaborazione pesante dell'IA su Linux non interferisce mai con la cadenza real-time (loop nominale 10 ms) del controllore semaforico su STM32."),
        ("Isolamento Fail-Safe Deterministico: ", "Se l'ambiente Linux o la pipeline video subiscono rallentamenti o crash, il controller STM32 rileva l'anomalia entro 1000 ms e impone il rosso di sicurezza."),
        ("Esecuzione 100% Offline & Standalone: ", "Nessuna dipendenza da connettività Internet o cloud runtime. Modello NCNN e logica residenti interamente on-board."),
        ("Efficienza Termica ed Energetica: ", "Consumo contenuto con profilo 2-thread NCNN su ARM: temperature operative stabili tra 48.2°C e 54.5°C senza throttling.")
    ]
    for b_title, b_desc in hw_feats:
        pb = tf_hw2.add_paragraph()
        pb.space_after = Pt(10)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(11)
        r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 5: Risoluzione Parte 2 - Ripartizione Carichi MPU vs MCU
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5, BG_LIGHT)
    add_header(slide5, "Risoluzione Parte 2", "Architettura Software: Ripartizione Computazionale MPU vs MCU")

    # Column Left: Linux MPU
    add_card(slide5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(4.3))
    add_card(slide5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(0.08), ACCENT_CYAN, None)
    mpu_tb = slide5.shapes.add_textbox(Inches(1.1), Inches(1.85), Inches(5.0), Inches(3.9))
    tf_mpu = mpu_tb.text_frame
    tf_mpu.word_wrap = True

    p = tf_mpu.paragraphs[0]
    p.text = "LINUX MPU (Core Applicativo & Visione)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(2, 132, 199)
    p.space_after = Pt(10)

    mpu_tasks = [
        ("Video Capture & Replay Decoder: ", "Decodifica flussi MP4/frame video con OpenCV headless."),
        ("YOLO26n Object Detection: ", "Inferenza neurale ottimizzata NCNN (FP32) su bounding box a 320x320."),
        ("ByteTrack & Identity Stitching: ", "Tracking multi-oggetto continuo con persistenza ID e filtro duplicati."),
        ("Analisi Spaziale ROI Poligonali: ", "Classificazione coordinate nelle 4 zone (attese, attraversamento, corsia)."),
        ("Crossing Events & Web Server: ", "Calcolo statistiche flussi, compressione JPEG e API HTTP REST (:8080).")
    ]
    for b_title, b_desc in mpu_tasks:
        pb = tf_mpu.add_paragraph()
        pb.space_after = Pt(6)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = TEXT_MUTED

    # Column Right: STM32 MCU
    add_card(slide5, Inches(6.8), Inches(1.6), Inches(5.7), Inches(4.3))
    add_card(slide5, Inches(6.8), Inches(1.6), Inches(5.7), Inches(0.08), ACCENT_GREEN, None)
    mcu_tb = slide5.shapes.add_textbox(Inches(7.1), Inches(1.85), Inches(5.1), Inches(3.9))
    tf_mcu = mcu_tb.text_frame
    tf_mcu.word_wrap = True

    p = tf_mcu.paragraphs[0]
    p.text = "STM32 MCU (Zephyr RTOS & Safety Engine)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(5, 150, 105)
    p.space_after = Pt(10)

    mcu_tasks = [
        ("Loop Deterministico Real-Time: ", "Cadenza di esecuzione costante a 10 ms (113 KB program flash, 47 KB RAM)."),
        ("Macchina a Stati Finiti (FSM): ", "Gestione rigorosa 8 fasi: Vehicle Green/Yellow, All-Red, Ped Green, Clearance, Fault."),
        ("Chiamata Automatica e Tempi Dinamici: ", "Trigger dopo 800 ms di attesa; 5s verde pedonale base, 8s tempo accessibile."),
        ("Arbitraggio Priorità & Conflitti: ", "Priorità veicolare limitata (5s hold); blocco immediato (Protected Stop) se occupato."),
        ("Hardware Watchdog & Sgombero: ", "Sorveglianza deadline trasporto (1000 ms) e timeout massimo sgombero (10 s).")
    ]
    for b_title, b_desc in mcu_tasks:
        pb = tf_mcu.add_paragraph()
        pb.space_after = Pt(6)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = TEXT_MUTED

    # Center Bridge Interface Banner
    add_card(slide5, Inches(0.8), Inches(6.1), Inches(11.733), Inches(0.9), CARD_DARK, None)
    br_tb = slide5.shapes.add_textbox(Inches(1.1), Inches(6.25), Inches(11.1), Inches(0.6))
    tf_br = br_tb.text_frame
    tf_br.word_wrap = True
    p_br = tf_br.paragraphs[0]
    p_br.text = "Contratto RouterBridge v1 (RPC crosssense_update): "
    p_br.font.size = Pt(11)
    p_br.font.bold = True
    p_br.font.color.rgb = ACCENT_CYAN
    r_br = p_br.add_run()
    r_br.text = "Payload compatto JSON <= 900 bytes per lato, massimo 8 tracce attive. Trasferisce stati logici 'crossing occupied/clear' e richieste senza inviare immagini pesanti alla MCU, garantendo latenza minima."
    r_br.font.bold = False
    r_br.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: Prestazioni Computazionali e Metriche di Calcolo
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6, BG_LIGHT)
    add_header(slide6, "Metriche e Prestazioni", "Benchmark di Calcolo e Prestazioni Reali su Arduino UNO Q")

    metrics_cards = [
        ("INFERENZA YOLO26n", "163 - 179 ms", "Mediana su CPU ARM (p95: ~190 ms)",
         "Modello esportato NCNN a 320x320 con 2 thread dedicati. Nessun drop di memoria o surriscaldamento."),
        ("LATENZA RPC BRIDGE", "178 - 196 ms", "p95 Round-Trip Time (max < 208 ms)",
         "Budget di trasporto ampiamente rispettato (Watchdog configurato a 1000 ms, deadline RPC 250 ms)."),
        ("THROUGHPUT PIPELINE", "5.2 - 5.6 FPS", "Frame rate elaborazione continuo",
         "I video nativi a 30 FPS sono campionati e processati frame-by-frame preservando tutti i transiti e le traiettorie."),
        ("IMPRONTA DI SISTEMA", "~300 MiB RAM", "CPU Load: ~182% su doppio core",
         "Impronta footprint ultra-leggera in container Docker; firmware STM32 occupa solo 113 KB di Flash e 47 KB di SRAM.")
    ]

    cw = Inches(2.7)
    c_gap = Inches(0.31)
    for i, (m_tag, m_val, m_sub, m_detail) in enumerate(metrics_cards):
        cx = Inches(0.8) + i * (cw + c_gap)
        add_card(slide6, cx, Inches(1.6), cw, Inches(4.3))
        
        # Top accent line
        add_card(slide6, cx, Inches(1.6), cw, Inches(0.08), ACCENT_CYAN if i%2==0 else ACCENT_GREEN, None)

        tb = slide6.shapes.add_textbox(cx + Inches(0.2), Inches(1.85), cw - Inches(0.4), Inches(3.9))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = m_tag
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_MUTED
        p1.space_after = Pt(12)

        p2 = tf.add_paragraph()
        p2.text = m_val
        p2.font.size = Pt(22)
        p2.font.bold = True
        p2.font.color.rgb = RGBColor(2, 132, 199) if i%2==0 else RGBColor(5, 150, 105)
        p2.space_after = Pt(4)

        p3 = tf.add_paragraph()
        p3.text = m_sub
        p3.font.size = Pt(10)
        p3.font.bold = True
        p3.font.color.rgb = TEXT_MAIN
        p3.space_after = Pt(12)

        p4 = tf.add_paragraph()
        p4.text = m_detail
        p4.font.size = Pt(10)
        p4.font.color.rgb = TEXT_MUTED

    # Bottom summary note
    add_card(slide6, Inches(0.8), Inches(6.1), Inches(11.733), Inches(0.9), CARD_DARK, None)
    nt_tb = slide6.shapes.add_textbox(Inches(1.1), Inches(6.25), Inches(11.1), Inches(0.6))
    tf_nt = nt_tb.text_frame
    tf_nt.word_wrap = True
    p_nt = tf_nt.paragraphs[0]
    p_nt.text = "Evidenza del Collaudo: "
    p_nt.font.size = Pt(11)
    p_nt.font.bold = True
    p_nt.font.color.rgb = ACCENT_AMBER
    r_nt = p_nt.add_run()
    r_nt.text = "Zero disconnessioni di trasporto nei test di stress. Watchdog e FSM STM32 garantiscono un fail-safe immediato con transizione protetta a rosso integrale in caso di ritardo oltre i margini di sicurezza."
    r_nt.font.bold = False
    r_nt.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 7: Risoluzione Parte 3 - La Dashboard di Controllo
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7, BG_LIGHT)
    add_header(slide7, "Risoluzione Parte 3", "Control Room Dashboard: Monitoraggio e Controllo Web in Tempo Reale")

    # Left: Placeholder for user screenshot
    screen_w = Inches(6.8)
    screen_h = Inches(5.2)
    add_card(slide7, Inches(0.8), Inches(1.6), screen_w, screen_h, RGBColor(241, 245, 249), RGBColor(148, 163, 184))
    
    # Inner decorative dashed-like placeholder box
    inner_box = slide7.shapes.add_textbox(Inches(1.2), Inches(2.6), Inches(6.0), Inches(3.2))
    tf_in = inner_box.text_frame
    tf_in.word_wrap = True
    pin1 = tf_in.paragraphs[0]
    pin1.alignment = PP_ALIGN.CENTER
    pin1.text = "📷 [ SCREENSHOT DELLA DASHBOARD ]"
    pin1.font.size = Pt(16)
    pin1.font.bold = True
    pin1.font.color.rgb = RGBColor(2, 132, 199)
    pin1.space_after = Pt(10)

    pin2 = tf_in.add_paragraph()
    pin2.alignment = PP_ALIGN.CENTER
    pin2.text = "(Sostituisci questo box inserendo lo screen dell'interfaccia attiva su http://<IP>:8080)"
    pin2.font.size = Pt(11)
    pin2.font.italic = True
    pin2.font.color.rgb = TEXT_MUTED
    pin2.space_after = Pt(14)

    pin3 = tf_in.add_paragraph()
    pin3.alignment = PP_ALIGN.CENTER
    pin3.text = "Elementi visibili nella UI:\n• Video annotato con ROI poligonali dinamiche\n• Semaforo virtuale e stato FSM in tempo reale\n• Pulsanti di richiesta manuale / accessibile\n• Contatori di flusso direzionale e allarmi"
    pin3.font.size = Pt(10)
    pin3.font.color.rgb = TEXT_MAIN

    # Right: Dashboard Features
    add_card(slide7, Inches(7.9), Inches(1.6), Inches(4.6), Inches(5.2))
    dash_tb = slide7.shapes.add_textbox(Inches(8.15), Inches(1.85), Inches(4.1), Inches(4.7))
    tf_dash = dash_tb.text_frame
    tf_dash.word_wrap = True

    p = tf_dash.paragraphs[0]
    p.text = "FUNZIONALITÀ DELLA CONTROL ROOM"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(2, 132, 199)
    p.space_after = Pt(12)

    dash_features = [
        ("Web Interface Integrata (:8080): ", "Nessun software client richiesto; fruibile da qualsiasi browser su PC o tablet via LAN."),
        ("Feed Video Annotato & Bounding Box: ", "Streaming JPEG con sovrimpressione in tempo reale di ID univoci, classi e coordinate."),
        ("Editor Interattivo delle Zone ROI: ", "Configurazione live dei 4 poligoni geometrici: attesa sx, attesa dx, crossing e approach."),
        ("Interazione & Chiamate Manuali: ", "Possibilità di simulare richieste pedonali, estensione tempo accessibile (+8s) e priorità veicoli."),
        ("Log Eventi ed Esportazione Dati: ", "Tracciamento in formato JSON di tutte le transizioni semaforiche, allarmi ed eventi per audit.")
    ]
    for b_title, b_desc in dash_features:
        pb = tf_dash.add_paragraph()
        pb.space_after = Pt(8)
        r1 = pb.add_run()
        r1.text = "• " + b_title
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_MAIN
        r2 = pb.add_run()
        r2.text = b_desc
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 8: Monitoraggio e Tracking Multi-Classe (Pedoni, Auto, Carrozzine)
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8, BG_LIGHT)
    add_header(slide8, "Rilevamento e Analisi", "Monitoraggio Intelligente: Tracking Multi-Classe & Occupancy")

    classes_info = [
        ("CONTEGGIO PEDONI", "Persone e Flussi", ACCENT_CYAN,
         "Rilevamento e tracking di pedoni che transitano sulle strisce con conteggio direzionale certificato (Sx -> Dx e Dx -> Sx) basato sulla sequenza temporale delle ROI.",
         "Metriche: Totale attraversamenti, pedoni attualmente in attesa (sx/dx), tempo medio di attesa prima dell'ingresso."),
        
        ("STATO ATTRAVERSAMENTO", "Occupancy & Safety", RGBColor(225, 29, 72),
         "Rilevamento istantaneo dell'occupazione fisica dell'area strisce pedonali. Segnale 'crossing occupied' inviato prioritariamente alla macchina a stati MCU.",
         "Protezione: Previene il verde veicolare fino al completo sgombero stabile (500 ms clear confirm). Allarme in caso di pedone fermo."),
        
        ("APPROCCIO VEICOLI", "Macchine e Priorità", ACCENT_AMBER,
         "Monitoraggio della corsia di avvicinamento veicolare (classe auto/bus/camion). Riconosce la presenza di veicoli in arrivo per adattare il verde semaforico.",
         "Efficienza: Consente lo skip immediato del verde veicoli se non ci sono auto in arrivo, accelerando la chiamata pedonale."),
        
        ("ACCESSIBILITÀ", "Carrozzine & Fragilità", ACCENT_GREEN,
         "Riconoscimento e gestione dedicata per utenti a mobilità ridotta, carrozzine e passeggini, integrato con tracking del tempo di permanenza e immobilità.",
         "Inclusività: Supporto estensione semaforica a 8 secondi di verde pedonale ('Tempo Accessibile') per garantire attraversamenti protetti e sereni.")
    ]

    card_w2 = Inches(5.6)
    card_h2 = Inches(2.4)
    positions = [
        (Inches(0.8), Inches(1.6)),
        (Inches(6.8), Inches(1.6)),
        (Inches(0.8), Inches(4.3)),
        (Inches(6.8), Inches(4.3))
    ]

    for idx, (head_tag, head_title, col_acc, main_desc, sub_desc) in enumerate(classes_info):
        pos_x, pos_y = positions[idx]
        add_card(slide8, pos_x, pos_y, card_w2, card_h2)
        add_card(slide8, pos_x, pos_y, card_w2, Inches(0.06), col_acc, None)

        tb = slide8.shapes.add_textbox(pos_x + Inches(0.25), pos_y + Inches(0.15), card_w2 - Inches(0.5), card_h2 - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = head_tag.upper()
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = col_acc
        p1.space_after = Pt(2)

        p2 = tf.add_paragraph()
        p2.text = head_title
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_MAIN
        p2.space_after = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = main_desc
        p3.font.size = Pt(10)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_after = Pt(4)

        p4 = tf.add_paragraph()
        p4.text = sub_desc
        p4.font.size = Pt(9.5)
        p4.font.bold = True
        p4.font.color.rgb = TEXT_MAIN

    # =========================================================================
    # SLIDE 9: Next Steps (Sviluppi Futuri)
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9, BG_LIGHT)
    add_header(slide9, "Evoluzione del Progetto", "Next Steps: Dalla Dimostrazione al Deployment Stradale")

    next_steps = [
        ("01", "CALIBRAZIONE METRICA DELLA CAMERA",
         "Implementazione della matrice di omografia prospettica (bird's-eye view) per mappare i pixel in coordinate metriche reali (millimetri/metri).",
         "Beneficio: Permette il calcolo esatto della velocità istantanea dei veicoli in avvicinamento e stima del Time-To-Collision (TTC) per frenate di emergenza."),
        
        ("02", "TEST IN AMBIENTE REALISTICO & LIVE CAMERA",
         "Transizione dai flussi video preregistrati a sensori camera live (MIPI-CSI / USB HD) installati su palo semaforico reale.",
         "Beneficio: Validazione su strada esposta a condizioni meteorologiche avverse (pioggia, nebbia), illuminazione notturna e riflessi stradali."),
        
        ("03", "FINE-TUNING DEL MODELLO SUI TARGET PICCOLI",
         "Addestramento custom del detector neurale (YOLOv8/v11/YOLO26 nano) su dataset urbano annotato ad alta risoluzione con modelli quantizzati ottimizzati.",
         "Beneficio: Incremento della precisione di tracking su soggetti piccoli o parzialmente occlusi a 320x320 pixel, perfezionando la recall sui transiti."),
        
        ("04", "INTEGRAZIONE ATTUATORI FISICI & C-ITS (V2X)",
         "Pilotaggio di relè/GPIO di potenza per lanterne semaforiche reali e modulo radio C-ITS (Cellular-V2X) per allerta diretta all'abitacolo delle auto connesse.",
         "Beneficio: Creazione di un ecosistema cooperativo completo tra infrastruttura intelligente urbana e veicoli a guida autonoma/connessi.")
    ]

    step_w = Inches(5.6)
    step_h = Inches(2.4)
    step_positions = [
        (Inches(0.8), Inches(1.6)),
        (Inches(6.8), Inches(1.6)),
        (Inches(0.8), Inches(4.3)),
        (Inches(6.8), Inches(4.3))
    ]

    for idx, (num, title, desc, benefit) in enumerate(next_steps):
        px, py = step_positions[idx]
        add_card(slide9, px, py, step_w, step_h)

        tb = slide9.shapes.add_textbox(px + Inches(0.25), py + Inches(0.18), step_w - Inches(0.5), step_h - Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = f"{num}  ·  {title}"
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(2, 132, 199)
        p1.space_after = Pt(6)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10)
        p2.font.color.rgb = TEXT_MAIN
        p2.space_after = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = benefit
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 10: Conclusioni e Ringraziamenti (Dark Theme)
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide10, BG_DARK)

    # Accent top bar
    bar10 = slide10.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.5), Inches(0.08))
    bar10.fill.solid()
    bar10.fill.fore_color.rgb = ACCENT_GREEN
    bar10.line.fill.background()

    # Content Box
    c10_box = slide10.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.733), Inches(4.8))
    tf10 = c10_box.text_frame
    tf10.word_wrap = True

    p = tf10.paragraphs[0]
    p.text = "SMART CITIES · CONNECTED SAFETY"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN
    p.space_after = Pt(12)

    p_t = tf10.add_paragraph()
    p_t.text = "Cross Sense: Il Futuro degli Attraversamenti Pedonali"
    p_t.font.size = Pt(36)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_LIGHT
    p_t.space_after = Pt(14)

    p_s = tf10.add_paragraph()
    p_s.text = "Un'architettura embedded completa, riproducibile e resiliente:\ndall'edge AI al determinismo real-time per salvare vite sulle strade di oggi e di domani."
    p_s.font.size = Pt(16)
    p_s.font.color.rgb = TEXT_LIGHT_MUTED
    p_s.space_after = Pt(30)

    # Team & Links Card
    add_card(slide10, Inches(0.8), Inches(4.8), Inches(11.733), Inches(1.9), CARD_DARK, RGBColor(51, 65, 85))
    team_tb = slide10.shapes.add_textbox(Inches(1.1), Inches(5.0), Inches(11.1), Inches(1.5))
    tf_team = team_tb.text_frame
    tf_team.word_wrap = True

    pt1 = tf_team.paragraphs[0]
    pt1.text = "TEAM DI SVILUPPO: "
    pt1.font.size = Pt(14)
    pt1.font.bold = True
    pt1.font.color.rgb = ACCENT_CYAN
    r_t = pt1.add_run()
    r_t.text = "GALILEO MAKERS"
    r_t.font.bold = True
    r_t.font.color.rgb = TEXT_LIGHT

    pt2 = tf_team.add_paragraph()
    pt2.text = "Progetto: Cross Sense  ·  Sviluppato per HackTurin 2026 su piattaforma Arduino UNO Q"
    pt2.font.size = Pt(12)
    pt2.font.color.rgb = TEXT_LIGHT_MUTED
    pt2.space_before = Pt(6)

    pt3 = tf_team.add_paragraph()
    pt3.text = "Grazie per l'attenzione! Siamo pronti per le vostre domande e per la demo dal vivo."
    pt3.font.size = Pt(13)
    pt3.font.bold = True
    pt3.font.color.rgb = ACCENT_GREEN
    pt3.space_before = Pt(8)

    # Save presentation
    output_path = "/home/guccilinda/Workspace/CrossSense/Presentation.pptx"
    prs.save(output_path)
    print(f"Presentazione creata con successo in: {output_path}")

if __name__ == "__main__":
    create_presentation()
