#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveBox Potential Lab (Qt) v0.30.0 — release pública
===================================================================================

Esta versión mantiene el motor numérico de la v2, pero mejora la experiencia de uso
para estudiantes que recién se familiarizan con fenómenos de propagación de ondas:

1) La interfaz ahora separa claramente:
   - fenómeno físico,
   - parámetros del modelo,
   - visualización,
   - guía teórica.

2) Los controles numéricos ya no dependen de las flechas nativas del spinbox.
   En su lugar usan botones explícitos "−" y "+", corrigiendo el problema de área
   clickeable pequeña reportado en la interfaz anterior.

3) Cada preset explica:
   - qué física representa,
   - qué deberías observar,
   - qué parámetros importan realmente.

Modelo que se integra:
    u_tt + gamma u_t = ∇·(c(x,y)^2 ∇u) - V(x,y) u

Interpretación:
    - u(x,y,t): amplitud de una onda escalar 2D.
    - c(x,y): velocidad local; si cambia en el espacio, aparece refracción.
    - V(x,y): potencial de dispersión.
    - obstáculos sólidos: se impone u = 0 dentro de la pared, generando reflexión.
    - gamma: amortiguamiento numérico/físico.

Dependencias:
    pip install numpy opencv-python PyQt6 pyqtgraph

Ejecutar:
    python wavebox.py
"""

from __future__ import annotations
import sys, time, math, shutil, subprocess, os, json
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Callable

try:
    import psutil  # type: ignore
except Exception:
    psutil = None

import numpy as np
import cv2

try:
    import pyqtgraph as pg  # type: ignore
    from pyqtgraph.Qt import QtCore, QtWidgets  # type: ignore
except Exception:
    print("\nFalta PyQt6 / pyqtgraph. Instala:\n  pip install PyQt6 pyqtgraph\n", file=sys.stderr)
    raise


# ----------------------------- Theme -----------------------------
#
# Dos niveles de apariencia:
# 1) tema de la interfaz (botones, paneles, pestañas)
# 2) tema visual de la simulación (paleta de colores del campo u)
#
# La idea es separar la física del aspecto visual para que el usuario pueda
# experimentar sin confundir un cambio de color con un cambio en el modelo.

APP_THEMES: Dict[str, Dict[str, object]] = {
    "Noche": {
        "window_bg": (12, 14, 20),
        "widget_bg": (19, 22, 31),
        "panel_bg": (18, 21, 29),
        "card_bg": (21, 25, 35),
        "tab_selected": (32, 40, 58),
        "button_bg": (28, 34, 48),
        "button_hover": (36, 45, 63),
        "button_pressed": (45, 57, 78),
        "border": "#4A5F87",
        "border_soft": "#2F3A50",
        "text": "#EFF4FF",
        "text_soft": "#AFC1E3",
        "accent": "#7EA7FF",
        "accent_soft": "#202C42",
        "accent_text": "#F2F7FF",
        "alert": "rgba(170, 30, 30, 220)",
        "alert_border": "rgba(255, 148, 148, 235)",
        "sim_default": "Original",
    },
    "Pizarra clara": {
        "window_bg": (235, 237, 242),
        "widget_bg": (248, 249, 252),
        "panel_bg": (242, 244, 248),
        "card_bg": (252, 253, 255),
        "tab_selected": (225, 232, 245),
        "button_bg": (236, 239, 245),
        "button_hover": (228, 233, 242),
        "button_pressed": (216, 224, 238),
        "border": "#B7C1D6",
        "border_soft": "#CAD2E3",
        "text": "#1C2330",
        "text_soft": "#55627C",
        "accent": "#5D7BB8",
        "accent_soft": "#DFE8FA",
        "accent_text": "#223455",
        "alert": "rgba(180, 36, 36, 225)",
        "alert_border": "rgba(255, 164, 164, 235)",
        "sim_default": "Hueso",
    },
    "Laboratorio verde": {
        "window_bg": (17, 23, 20),
        "widget_bg": (23, 31, 27),
        "panel_bg": (22, 29, 25),
        "card_bg": (26, 34, 29),
        "tab_selected": (34, 48, 39),
        "button_bg": (31, 40, 35),
        "button_hover": (38, 50, 43),
        "button_pressed": (44, 58, 48),
        "border": "#44624E",
        "border_soft": "#33483B",
        "text": "#E7F0EA",
        "text_soft": "#A7C1B0",
        "accent": "#6AA678",
        "accent_soft": "#24402D",
        "accent_text": "#E2F6E7",
        "alert": "rgba(162, 32, 32, 220)",
        "alert_border": "rgba(255, 135, 135, 230)",
        "sim_default": "Viridis",
    },
    "Atardecer cálido": {
        "window_bg": (27, 18, 16),
        "widget_bg": (36, 24, 21),
        "panel_bg": (32, 22, 19),
        "card_bg": (38, 26, 23),
        "tab_selected": (52, 34, 30),
        "button_bg": (44, 29, 25),
        "button_hover": (54, 35, 31),
        "button_pressed": (64, 41, 36),
        "border": "#7D5B4B",
        "border_soft": "#5B4036",
        "text": "#F6ECE7",
        "text_soft": "#D3B6A9",
        "accent": "#D18C5A",
        "accent_soft": "#4A2F24",
        "accent_text": "#FFF0E4",
        "alert": "rgba(170, 34, 34, 220)",
        "alert_border": "rgba(255, 145, 145, 230)",
        "sim_default": "Turbo",
    },
    "Aurora": {
        "window_bg": (13, 19, 28),
        "widget_bg": (19, 28, 39),
        "panel_bg": (18, 25, 35),
        "card_bg": (21, 31, 43),
        "tab_selected": (28, 42, 57),
        "button_bg": (28, 38, 53),
        "button_hover": (35, 48, 66),
        "button_pressed": (42, 57, 78),
        "border": "#4F6A8E",
        "border_soft": "#374A63",
        "text": "#E8F1FF",
        "text_soft": "#A8BEDD",
        "accent": "#67A9D6",
        "accent_soft": "#22384C",
        "accent_text": "#E6F7FF",
        "alert": "rgba(165, 30, 40, 220)",
        "alert_border": "rgba(255, 145, 160, 230)",
        "sim_default": "Océano",
    },
}


def app_theme_meta(theme_name: str) -> Dict[str, object]:
    return APP_THEMES.get(theme_name, APP_THEMES["Noche"])


def qss_app_theme(theme_name: str = "Noche") -> str:
    pal = app_theme_meta(theme_name)

    def rgb(key: str) -> str:
        vals = pal[key]
        return f"rgb({vals[0]},{vals[1]},{vals[2]})"

    return f"""
    QWidget {{
        background-color: {rgb('window_bg')};
        color: {pal['text']};
        font-size: 10pt;
    }}
    QMainWindow {{ background-color: {rgb('window_bg')}; }}
    QTabWidget::pane {{
        border: 1px solid {pal['border_soft']};
        top: -1px;
    }}
    QTabBar::tab {{
        background: {rgb('widget_bg')};
        padding: 8px 14px;
        border: 1px solid {pal['border_soft']};
        border-bottom: none;
        min-width: 140px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    QTabBar::tab:selected {{ background: {rgb('tab_selected')}; }}
    QGroupBox {{
        border: 1px solid {pal['border_soft']};
        margin-top: 12px;
        padding: 12px;
        border-radius: 10px;
        background: {rgb('panel_bg')};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: {pal['text']};
        font-weight: 600;
    }}
    QPushButton {{
        background: {rgb('button_bg')};
        border: 1px solid {pal['border']};
        padding: 8px 12px;
        border-radius: 8px;
        min-height: 18px;
    }}
    QPushButton:hover {{ background: {rgb('button_hover')}; }}
    QPushButton:pressed {{ background: {rgb('button_pressed')}; }}
    QPushButton:disabled {{
        color: #8E8E8E;
        background: {rgb('widget_bg')};
        border-color: {pal['border_soft']};
    }}
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextBrowser {{
        background: {rgb('widget_bg')};
        border: 1px solid {pal['border']};
        padding: 6px 8px;
        border-radius: 8px;
    }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QTextBrowser:focus {{
        border: 1px solid {pal['accent']};
        background: {rgb('card_bg')};
    }}
    QComboBox, QLineEdit, QTextBrowser {{
        selection-background-color: {pal['accent']};
    }}
    QTextBrowser {{
        line-height: 1.35;
    }}
    QLabel#hud {{
        background-color: rgba(0,0,0,145);
        color: white;
        padding: 10px;
        border-radius: 10px;
    }}
    QLabel#caption {{
        color: {pal['text_soft']};
        font-size: 9pt;
        line-height: 1.35;
    }}
    QLabel#titleMini {{
        color: {pal['text']};
        font-weight: 600;
    }}
    QLabel#badge {{
        background: {pal['accent_soft']};
        border: 1px solid {pal['accent']};
        border-radius: 12px;
        padding: 4px 10px;
        color: {pal['accent_text']};
        font-size: 9pt;
        font-weight: 600;
    }}
    QFrame#paramCard {{
        background: {rgb('card_bg')};
        border: 1px solid {pal['border']};
        border-radius: 10px;
    }}
    QFrame#panelCard {{
        background: {rgb('panel_bg')};
        border: 1px solid {pal['border_soft']};
        border-radius: 10px;
    }}
    QCheckBox {{ spacing: 8px; }}
    QProgressBar {{
        border: 1px solid {pal['border_soft']};
        border-radius: 6px;
        text-align: center;
        background: {rgb('widget_bg')};
    }}
    QProgressBar::chunk {{
        background: {pal['accent']};
        border-radius: 6px;
    }}
    QToolTip {{
        background: {rgb('button_bg')};
        color: {pal['text']};
        border: 1px solid {pal['accent']};
        padding: 6px;
    }}
    QLabel#alertOverlay {{
        background-color: {pal['alert']};
        color: white;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid {pal['alert_border']};
        font-weight: 700;
    }}
    QLabel#softBadge {{
        background: {rgb('button_bg')};
        border: 1px solid {pal['border']};
        border-radius: 8px;
        padding: 6px 10px;
        color: {pal['text']};
    }}
    QFrame#metricCard {{
        background: {rgb('card_bg')};
        border: 1px solid {pal['border']};
        border-radius: 8px;
    }}
    QLabel#metricTitle {{
        color: {pal['text_soft']};
        font-size: 8.4pt;
        font-weight: 600;
    }}
    QLabel#metricValue {{
        color: {pal['text']};
        font-size: 9pt;
        font-weight: 600;
    }}
    QLabel#sectionCaption {{
        color: {pal['text_soft']};
        font-size: 9pt;
        font-weight: 600;
    }}
    QScrollArea {{ border: none; }}
    QPushButton#accordionHeader {{
        text-align: left;
        background: {pal['accent_soft']};
        border: 1px solid {pal['accent']};
        border-radius: 12px;
        color: {pal['accent_text']};
        font-weight: 700;
        padding: 11px 14px;
        min-height: 26px;
    }}
    QPushButton#accordionHeader:hover {{
        background: {rgb('button_hover')};
        border-color: {pal['accent']};
    }}
    QPushButton#accordionHeader[expanded="true"] {{
        background: {rgb('tab_selected')};
        border: 1px solid {pal['accent']};
        color: {pal['accent_text']};
    }}
    QFrame#accordionBody {{
        background: transparent;
        border: none;
    }}
    """


def qss_dark() -> str:
    return qss_app_theme("Noche")


# ----------------------------- Metadata -----------------------------

PARAM_TEXT = {
    "quality_mode": (
        "Calidad visual rápida",
        "Es un atajo para mover la grilla entre Baja, Media y Alta. Si la subes: + ganas detalle y una imagen más limpia; − sube el costo en RAM y cae el rendimiento. Puedes dejarla en Personalizada y fijar la grilla a mano.",
    ),
    "grid": (
        "Resolución espacial de la grilla",
        "Sirve para discretizar mejor el espacio. Si la subes: + ves bordes y patrones más suaves; − consume bastante más RAM y suele bajar los FPS.",
    ),
    "fps": (
        "FPS de visualización",
        "Solo cambia la fluidez visual. Si lo subes: + movimiento más continuo; − exige más al render y puede reducir margen de rendimiento.",
    ),
    "V0": (
        "Intensidad del potencial V(x,y)",
        "Controla qué tan fuerte empuja o deforma el medio a la onda. Si la subes: + la dispersión se nota más; − aparecen patrones más abruptos y más sensibles al valor elegido.",
    ),
    "Vsig": (
        "Ancho sigma del potencial",
        "Ajusta qué tan extendida es cada región de potencial. Si la subes: + el efecto se vuelve más suave y amplio; − se pierden detalles finos y pueden mezclarse estructuras cercanas.",
    ),
    "n_strength": (
        "Fuerza del índice de refracción",
        "Mide cuánto cambia la velocidad local. Si la subes: + la refracción se vuelve más evidente; − el frente puede deformarse mucho y costar más interpretar qué fenómeno domina. Solo produce cambios visibles en presets donde el medio usa índice de refracción variable.",
    ),
    "c": (
        "Velocidad base de propagación c",
        "Escala la rapidez de avance de la perturbación. Si la subes: + la evolución recorre el medio más rápido; − necesitas más subpasos internos y puede subir el costo computacional.",
    ),
    "gamma": (
        "Amortiguamiento gamma",
        "Hace que la onda pierda amplitud con el tiempo. Si lo subes: + se limpia el ruido visual y se controlan rebotes tardíos; − desaparecen antes detalles útiles de la dinámica.",
    ),
    "boundary_mode": (
        "Condición de borde física",
        "Decide qué pasa en los límites del dominio. Cambiarla: + permite comparar reflexión, escape o confinamiento; − puede modificar mucho la lectura del fenómeno si la dejas en un borde poco adecuado.",
    ),
    "auto_apply_preset_defaults": (
        "Aplicar ajustes sugeridos del preset",
        "Cuando está activo, cada preset puede cargar sus parámetros físicos y su condición inicial recomendada. Si lo apagas: + conservas tu calibración actual al cambiar de preset; − pierdes la puesta a punto sugerida para ese medio.",
    ),
    "overlay": (
        "Mapa explicativo sobre la imagen",
        "Te deja ver qué parte del medio estás estudiando: potencial, paredes sólidas o índice de refracción. Activarlo: + conecta mejor la física con lo que ves en pantalla; − añade una capa visual extra y puede distraer si solo quieres seguir la amplitud.",
    ),
    "app_theme": (
        "Tema del programa",
        "Cambia colores, contraste y presencia visual de la interfaz. Al cambiarlo: + puede hacer más cómoda la lectura durante sesiones largas; − si estabas usando la paleta sugerida por defecto, la simulación puede proponerte otra combinación visual.",
    ),
    "theme": (
        "Paleta de la simulación",
        "Cambia únicamente los colores con que se dibuja la onda y los overlays. Si la ajustas bien: + ciertos frentes, nodos o zonas de interferencia resaltan mucho mejor; − una mala elección puede aplastar contrastes finos.",
    ),
    "scale": (
        "Nitidez de la vista previa",
        "Reduce o aumenta la resolución con que se dibuja la imagen en pantalla, sin tocar la física interna. Si la bajas: + ganas fluidez; − la escena pierde definición visual.",
    ),
    "perf_overlay": (
        "Monitor de rendimiento",
        "Muestra FPS y memoria en pantalla. Activarlo: + te ayuda a cuidar recursos; − agrega un poco de texto encima de la simulación. El aviso rojo crítico aparece siempre.",
    ),
}

# Se llena después de definir PRESETS.
PRESET_META: Dict[str, Dict[str, object]] = {}

OVERLAY_OPTIONS: Dict[str, str] = {
    "Solo la onda (sin mapa extra)": "None",
    "Potencial V(x,y): paisaje de dispersión": "V",
    "Obstáculos sólidos: paredes y barreras": "Mask",
    "Índice de refracción n(x,y): regiones con distinta velocidad": "n",
}
OVERLAY_MODE_TO_DISPLAY: Dict[str, str] = {v: k for k, v in OVERLAY_OPTIONS.items()}
OVERLAY_MODE_TO_SHORT: Dict[str, str] = {
    "None": "sin mapa extra",
    "V": "mapa de potencial V(x,y)",
    "Mask": "mapa de obstáculos sólidos",
    "n": "mapa de índice de refracción n(x,y)",
}


def overlay_display(mode: str) -> str:
    return OVERLAY_MODE_TO_DISPLAY.get(str(mode), OVERLAY_MODE_TO_DISPLAY["None"])


def overlay_mode_from_text(text: str) -> str:
    if text in OVERLAY_OPTIONS:
        return OVERLAY_OPTIONS[text]
    if text in OVERLAY_MODE_TO_DISPLAY:
        return str(text)
    return "None"


def overlay_short_label(mode: str) -> str:
    return OVERLAY_MODE_TO_SHORT.get(str(mode), OVERLAY_MODE_TO_SHORT["None"])


# ----------------------------- Simulation core -----------------------------

@dataclass
class SimParams:
    # Domain
    L: float = 10.0
    grid: int = 320
    fps: int = 60
    spf: int = 2
    quality_mode: str = "Media"

    # PDE baseline
    c: float = 0.34
    gamma: float = 0.010

    # Absorbing layer at outer boundary
    absorb_strength: float = 3.2
    absorb_width: float = 0.14

    # Potential knobs
    V0: float = 180.0
    Vsig: float = 0.090

    # Refractive index knob (for c(x,y) maps)
    n_strength: float = 0.55

    # Initial packet
    x0: float = 1.85
    y0: float = 0.0
    R0: float = 0.66
    k0: float = 38.28
    edge: float = 0.14

    # Render style
    phase_freq: float = 6.5
    phase_contrast: float = 2.9
    amp_gain: float = 2.0
    amp_pow: float = 0.22
    glow: float = 0.9
    fringe: int = 2
    unsharp_sigma: float = 0.9
    unsharp_amount: float = 0.55

    # UI / overlays
    show_dots: bool = True
    border: bool = True
    preview_scale: float = 1.0
    overlay_mode: str = "None"  # None / V / Mask / n
    boundary_mode: str = "Sin borde (salida absorbente)"
    theme_name: str = "Original"
    app_theme_name: str = "Noche"
    show_perf_overlay: bool = True
    auto_reset_on_preset: bool = True
    auto_apply_preset_defaults: bool = True


QUALITY_PRESETS: Dict[str, int] = {
    "Baja": 224,
    "Media": 320,
    "Alta": 512,
}


def quality_label_for_grid(grid: int) -> str:
    for name, value in QUALITY_PRESETS.items():
        if int(grid) == int(value):
            return name
    return "Personalizada"


# ----------------------------- Boundary modes & color themes -----------------------------

BOUNDARY_MODES: Dict[str, Dict[str, object]] = {
    "Sin borde (salida absorbente)": {
        "absorb_edges": ("left", "right", "top", "bottom"),
        "wall_edges": (),
        "label": "bordes abiertos",
        "summary": "La onda se amortigua al llegar al borde, así que casi no rebota.",
    },
    "Reflexión en los 4 bordes": {
        "absorb_edges": (),
        "wall_edges": (),
        "label": "caja reflectante",
        "summary": "Los cuatro bordes reflejan la onda como una caja cerrada idealizada.",
    },
    "Caja rígida: u = 0 en los bordes": {
        "absorb_edges": (),
        "wall_edges": ("left", "right", "top", "bottom"),
        "label": "pared rígida",
        "summary": "Se impone un borde duro con amplitud nula en el contorno del dominio.",
    },
    "Tubo horizontal (reflexión arriba/abajo)": {
        "absorb_edges": ("left", "right"),
        "wall_edges": (),
        "label": "guía horizontal",
        "summary": "La onda rebota arriba y abajo, pero puede salir por la izquierda y la derecha.",
    },
    "Tubo vertical (reflexión izquierda/derecha)": {
        "absorb_edges": ("top", "bottom"),
        "wall_edges": (),
        "label": "guía vertical",
        "summary": "La onda rebota a izquierda y derecha, pero puede escapar por arriba y abajo.",
    },
}

THEMES: Dict[str, Dict[str, object]] = {
    "Original": {
        "mode": "original",
        "bg": (8, 9, 12),
        "border": (70, 60, 85),
    },
    "Viridis": {
        "mode": "colormap",
        "colormap": cv2.COLORMAP_VIRIDIS,
        "bg": (8, 16, 18),
        "border": (115, 154, 90),
    },
    "Turbo": {
        "mode": "colormap",
        "colormap": cv2.COLORMAP_TURBO,
        "bg": (16, 10, 8),
        "border": (210, 150, 72),
    },
    "Océano": {
        "mode": "colormap",
        "colormap": cv2.COLORMAP_OCEAN,
        "bg": (6, 10, 20),
        "border": (115, 92, 70),
    },
    "Calor": {
        "mode": "colormap",
        "colormap": cv2.COLORMAP_HOT,
        "bg": (18, 8, 6),
        "border": (160, 120, 80),
    },
    "Hueso": {
        "mode": "colormap",
        "colormap": cv2.COLORMAP_BONE,
        "bg": (10, 10, 10),
        "border": (135, 135, 135),
    },
}


RESOLUTION_PRESETS: Dict[str, Optional[Tuple[int, int]]] = {
    "Personalizado": None,
    "HD · 1280×720 · 16:9": (1280, 720),
    "Full HD · 1920×1080 · 16:9": (1920, 1080),
    "QHD · 2560×1440 · 16:9": (2560, 1440),
    "UHD 4K · 3840×2160 · 16:9": (3840, 2160),
    "XGA · 1024×768 · 4:3": (1024, 768),
    "UXGA · 1600×1200 · 4:3": (1600, 1200),
    "Instagram cuadrado · 1080×1080 · 1:1": (1080, 1080),
    "Instagram vertical · 1080×1350 · 4:5": (1080, 1350),
    "Stories / Reels · 1080×1920 · 9:16": (1080, 1920),
}


# ----------------------------- Resource monitoring -----------------------------

def _fmt_gib_from_bytes(nbytes: Optional[float]) -> str:
    if nbytes is None:
        return "N/D"
    return f"{float(nbytes) / (1024**3):.2f} GiB"


def _ratio_status(ratio: Optional[float]) -> str:
    if ratio is None:
        return "unknown"
    if ratio >= 0.92:
        return "danger"
    if ratio >= 0.85:
        return "warn"
    return "ok"


def _safe_float_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den in (None, 0):
        return None
    return float(num) / float(den)


def read_system_snapshot() -> Dict[str, object]:
    snap: Dict[str, object] = {
        "ram_proc": None,
        "ram_used": None,
        "ram_total": None,
        "ram_ratio": None,
        "vram_proc": None,
        "vram_used": None,
        "vram_total": None,
        "vram_ratio": None,
        "gpu_name": None,
        "gpu_available": False,
    }

    if psutil is not None:
        try:
            proc = psutil.Process(os.getpid())
            snap["ram_proc"] = float(proc.memory_info().rss)
            vm = psutil.virtual_memory()
            snap["ram_total"] = float(vm.total)
            snap["ram_used"] = float(vm.total - vm.available)
            snap["ram_ratio"] = _safe_float_div(snap["ram_used"], snap["ram_total"])
        except Exception:
            pass

    nvsmi = shutil.which("nvidia-smi")
    if nvsmi:
        try:
            cmd = [nvsmi, "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=1.2)
            lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
            total_mib = 0.0
            used_mib = 0.0
            gpu_names = []
            for ln in lines:
                parts = [p.strip() for p in ln.split(",")]
                if len(parts) >= 3:
                    gpu_names.append(parts[0])
                    used_mib += float(parts[-2])
                    total_mib += float(parts[-1])
            if total_mib > 0:
                snap["gpu_available"] = True
                snap["gpu_name"] = ", ".join(gpu_names)
                snap["vram_used"] = used_mib * 1024**2
                snap["vram_total"] = total_mib * 1024**2
                snap["vram_ratio"] = _safe_float_div(snap["vram_used"], snap["vram_total"])

            try:
                cmd_apps = [nvsmi, "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
                out_apps = subprocess.check_output(cmd_apps, stderr=subprocess.DEVNULL, text=True, timeout=1.2)
                pid = os.getpid()
                proc_mib = 0.0
                for ln in out_apps.splitlines():
                    parts = [p.strip() for p in ln.split(",")]
                    if len(parts) >= 2:
                        try:
                            if int(parts[0]) == pid:
                                proc_mib += float(parts[1])
                        except Exception:
                            continue
                if proc_mib > 0:
                    snap["vram_proc"] = proc_mib * 1024**2
            except Exception:
                pass
        except Exception:
            pass

    return snap


def build_perf_alert_text(snapshot: Dict[str, object]) -> Tuple[str, bool]:
    ram_ratio = snapshot.get("ram_ratio")
    vram_ratio = snapshot.get("vram_ratio")
    ram_status = _ratio_status(ram_ratio if isinstance(ram_ratio, (int, float)) else None)
    vram_status = _ratio_status(vram_ratio if isinstance(vram_ratio, (int, float)) else None)

    messages = []
    danger = False
    if ram_status in ("warn", "danger"):
        danger = True
        messages.append(
            f"RAM en uso alto: {_fmt_gib_from_bytes(snapshot.get('ram_used'))} / {_fmt_gib_from_bytes(snapshot.get('ram_total'))}"
        )
    if vram_status in ("warn", "danger"):
        danger = True
        messages.append(
            f"VRAM en uso alto: {_fmt_gib_from_bytes(snapshot.get('vram_used'))} / {_fmt_gib_from_bytes(snapshot.get('vram_total'))}"
        )
    if not messages:
        return "", False
    return "⚠ Riesgo de estrés de memoria: " + " | ".join(messages), danger


# Exportación de video:
# Recibe un generador de cuadros RGB y escribe un MP4.
# Primero intenta usar ffmpeg (mejor calidad y compatibilidad).
# Si ffmpeg no está disponible, cae a OpenCV como plan B.
class VideoFrameWriter:
    """Escritor incremental de cuadros RGB hacia MP4.

    Permite agregar cuadros uno a uno sin depender de un único generador
    monolítico. Esto hace más robusta la exportación cuando se encadenan
    varios presets en un solo video.
    """

    def __init__(self, out_path: str, W: int, H: int, fps: int, crf: int = 18, preset: str = "slow") -> None:
        self.out_path = os.path.abspath(out_path)
        self.W = int(W)
        self.H = int(H)
        self.fps = int(fps)
        self.crf = int(crf)
        self.preset = str(preset)
        self._mode = "opencv"
        self._proc = None
        self._writer = None
        os.makedirs(os.path.dirname(self.out_path) or '.', exist_ok=True)

        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            cmd = [
                ffmpeg, '-y',
                '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{self.W}x{self.H}',
                '-r', str(self.fps),
                '-i', '-',
                '-an',
                '-vcodec', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', self.preset,
                '-crf', str(self.crf),
                self.out_path,
            ]
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self._mode = "ffmpeg"
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self._writer = cv2.VideoWriter(self.out_path, fourcc, float(self.fps), (self.W, self.H))
            if not self._writer.isOpened():
                raise RuntimeError('No se pudo abrir el escritor de video. Instala ffmpeg o revisa los codecs de OpenCV.')

    def write(self, frame: np.ndarray) -> None:
        if frame is None:
            return
        arr = np.asarray(frame)
        if arr.shape != (self.H, self.W, 3):
            raise ValueError(f'Frame con forma inválida: {arr.shape}; se esperaba {(self.H, self.W, 3)}.')
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        if self._mode == "ffmpeg":
            if self._proc is None or self._proc.stdin is None:
                raise RuntimeError('ffmpeg no está disponible para escritura.')
            self._proc.stdin.write(arr.tobytes())
        else:
            assert self._writer is not None
            self._writer.write(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))

    def close(self) -> None:
        if self._mode == "ffmpeg":
            if self._proc is None:
                return
            try:
                if self._proc.stdin is not None:
                    self._proc.stdin.close()
                stderr = b''
                if self._proc.stderr is not None:
                    stderr = self._proc.stderr.read()
                self._proc.wait()
                if self._proc.returncode != 0:
                    err = stderr.decode('utf-8', errors='ignore').strip()
                    raise RuntimeError(err or 'ffmpeg terminó con error al codificar el video.')
            finally:
                self._proc = None
        else:
            if self._writer is not None:
                self._writer.release()
                self._writer = None

    def abort(self) -> None:
        if self._mode == "ffmpeg":
            if self._proc is not None:
                try:
                    if self._proc.stdin is not None:
                        self._proc.stdin.close()
                except Exception:
                    pass
                try:
                    self._proc.kill()
                    self._proc.wait(timeout=2)
                except Exception:
                    pass
                self._proc = None
        else:
            if self._writer is not None:
                self._writer.release()
                self._writer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.close()
        else:
            self.abort()
        return False

def write_video_ffmpeg(out_path: str, frames, W: int, H: int, fps: int, crf: int = 18, preset: str = "slow") -> None:
    """Escribe un MP4 desde un generador de cuadros RGB uint8.

    Usa ffmpeg si está disponible; si no, hace fallback a OpenCV VideoWriter.
    """
    with VideoFrameWriter(out_path, W=W, H=H, fps=fps, crf=crf, preset=preset) as writer:
        for frame in frames:
            writer.write(frame)


# ----------------------------- Numerics helpers -----------------------------

def _edge_profile(N: int, w: int, strength: float, edge: str) -> np.ndarray:
    idx = np.arange(N, dtype=np.float32)
    if edge == "left":
        d = idx
    elif edge == "right":
        d = (N - 1) - idx
    elif edge == "top":
        d = idx
    elif edge == "bottom":
        d = (N - 1) - idx
    else:
        raise ValueError(f"Borde desconocido: {edge}")
    t = np.clip(d / max(w, 1), 0, 1)
    t = t*t*(3 - 2*t)
    return np.exp(-float(strength) * (1 - t)**2).astype(np.float32)


def make_edge_absorb_mask(N: int, strength: float, width_frac: float, absorb_edges: Tuple[str, ...]) -> np.ndarray:
    mask = np.ones((N, N), dtype=np.float32)
    if not absorb_edges:
        return mask
    w = int(max(6, N * width_frac))
    for edge in absorb_edges:
        prof = _edge_profile(N, w, strength, edge)
        if edge in ("left", "right"):
            mask *= prof[None, :]
        else:
            mask *= prof[:, None]
    return mask.astype(np.float32)


def make_edge_wall_mask(N: int, wall_edges: Tuple[str, ...], thickness_px: int = 2) -> np.ndarray:
    mask = np.zeros((N, N), dtype=bool)
    if not wall_edges:
        return mask
    t = max(1, int(thickness_px))
    if "left" in wall_edges:
        mask[:, :t] = True
    if "right" in wall_edges:
        mask[:, -t:] = True
    if "top" in wall_edges:
        mask[:t, :] = True
    if "bottom" in wall_edges:
        mask[-t:, :] = True
    return mask


def build_boundary_state(N: int, P: SimParams) -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    meta = BOUNDARY_MODES.get(P.boundary_mode, BOUNDARY_MODES["Sin borde (salida absorbente)"])
    absorb_edges = tuple(meta["absorb_edges"])
    wall_edges = tuple(meta["wall_edges"])
    absorb = make_edge_absorb_mask(N, P.absorb_strength, P.absorb_width, absorb_edges)
    wall_mask = make_edge_wall_mask(N, wall_edges, thickness_px=2)
    return absorb, wall_mask, meta


def theme_meta(theme_name: str) -> Dict[str, object]:
    return THEMES.get(theme_name, THEMES["Original"])


def sample_valid_center(
    X: np.ndarray,
    Y: np.ndarray,
    obstacle_mask: Optional[np.ndarray],
    edge_wall_mask: Optional[np.ndarray],
    boundary_meta: Dict[str, object],
    P: SimParams,
    rng: np.random.Generator,
    dx: float,
) -> Tuple[float, float]:
    allowed = np.ones(X.shape, dtype=np.uint8)
    if obstacle_mask is not None:
        allowed[obstacle_mask] = 0
    if edge_wall_mask is not None:
        allowed[edge_wall_mask] = 0

    base_margin_px = max(4, int(math.ceil((P.R0 * (1.0 + P.edge)) / max(dx, 1e-8))))
    open_margin_px = max(base_margin_px, int(max(6, X.shape[0] * P.absorb_width)) + 2)

    absorb_edges = tuple(boundary_meta.get("absorb_edges", ()))
    if "left" in absorb_edges:
        allowed[:, :open_margin_px] = 0
    else:
        allowed[:, :base_margin_px] = 0
    if "right" in absorb_edges:
        allowed[:, -open_margin_px:] = 0
    else:
        allowed[:, -base_margin_px:] = 0
    if "top" in absorb_edges:
        allowed[:open_margin_px, :] = 0
    else:
        allowed[:base_margin_px, :] = 0
    if "bottom" in absorb_edges:
        allowed[-open_margin_px:, :] = 0
    else:
        allowed[-base_margin_px:, :] = 0

    radius_px = max(2, int(math.ceil((P.R0 + 0.25) / max(dx, 1e-8))))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*radius_px + 1, 2*radius_px + 1))
    safe = cv2.erode(allowed, ker, iterations=1)
    ys, xs = np.where(safe > 0)
    if xs.size == 0:
        ys, xs = np.where(allowed > 0)
    if xs.size == 0:
        return float(P.x0), float(P.y0)

    idx = int(rng.integers(0, xs.size))
    j = int(xs[idx])
    i = int(ys[idx])
    return float(X[i, j]), float(Y[i, j])


def init_disk(X: np.ndarray, Y: np.ndarray, x0: float, y0: float, R: float, k: float, edge: float) -> Tuple[np.ndarray, np.ndarray]:
    r = np.sqrt((X-x0)**2 + (Y-y0)**2)
    env = 0.5*(1 - np.tanh((r - R)/(edge*R + 1e-6))).astype(np.float32)
    u = (env * np.cos(k*(X-x0))).astype(np.float32)
    return u, env


def unsharp_u8(img: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    if amount <= 0:
        return img
    blur = cv2.GaussianBlur(img, (0,0), float(sigma))
    sharp = cv2.addWeighted(img, 1.0 + float(amount), blur, -float(amount), 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def build_dots_image(pts: np.ndarray, N: int, L: float, preview_scale: float) -> np.ndarray:
    """
    Construye la capa RGB de puntos brillantes asociada a centros de dispersores.

    Importante: esta función recibe explícitamente el tamaño N de la grilla donde se
    dibujará la imagen. Así evitamos inconsistencias entre la grilla de la vista en vivo
    y la grilla elegida para exportar MP4.
    """
    S = int(N)
    img = np.zeros((S, S), dtype=np.float32)
    sigma_px = max(1.6, 2.2 * float(preview_scale))
    rr = int(max(4, sigma_px * 3))
    for xi, yi in pts:
        px = (float(xi) + float(L)/2.0) / float(L) * S
        py = (float(L)/2.0 - float(yi)) / float(L) * S
        x0 = int(px); y0 = int(py)
        x1, x2 = max(0, x0-rr), min(S, x0+rr+1)
        y1, y2 = max(0, y0-rr), min(S, y0+rr+1)
        yy, xx = np.mgrid[y1:y2, x1:x2]
        g = np.exp(-((xx-px)**2 + (yy-py)**2) / (2*sigma_px*sigma_px)).astype(np.float32)
        img[y1:y2, x1:x2] += g
    img = img / (img.max() + 1e-6)
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    d = (img * 255).astype(np.uint8)
    return np.stack([d, d, d], axis=2)


def render_frame(u: np.ndarray,
                 dots_rgb: Optional[np.ndarray],
                 overlay: Optional[np.ndarray],
                 P: SimParams) -> np.ndarray:
    s = float(np.std(u) + 1e-6)
    us = u / (2.8*s)

    bands = np.sin(float(P.phase_freq) * us)
    band = 0.5 + 0.5 * np.tanh(float(P.phase_contrast) * bands)

    amp = np.clip(np.abs(us) * float(P.amp_gain), 0.0, 1.0) ** float(P.amp_pow)
    img01 = (band * amp).astype(np.float32)
    img01 = np.nan_to_num(img01, nan=0.0, posinf=1.0, neginf=0.0)
    np.clip(img01, 0.0, 1.0, out=img01)

    base = (img01 * 255.0).astype(np.uint8)
    base = unsharp_u8(base, sigma=P.unsharp_sigma, amount=P.unsharp_amount)

    tmeta = theme_meta(P.theme_name)
    if str(tmeta.get("mode", "original")) == "original":
        fr = int(P.fringe)
        r = np.roll(base, +fr, axis=1)
        g = base
        b = np.roll(base, -fr, axis=1)
        rgb = np.stack([r, g, b], axis=2).astype(np.uint8)
    else:
        rgb = cv2.applyColorMap(base, int(tmeta["colormap"]))
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

    if float(P.glow) > 0:
        bl = cv2.GaussianBlur(rgb, (0,0), float(P.glow))
        rgb = cv2.addWeighted(rgb, 0.84, bl, 0.16, 0)

    if overlay is not None:
        ov = (np.clip(overlay, 0, 1) * 255).astype(np.uint8)
        ov_rgb = np.stack([ov, ov, ov], axis=2)
        rgb = cv2.addWeighted(rgb, 0.88, ov_rgb, 0.12, 0)

    if P.show_dots and dots_rgb is not None:
        rgb = cv2.add(rgb, dots_rgb)

    return rgb


# ----------------------------- Variable-coefficient operator -----------------------------

def neumann_shift(u: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns (uR,uL,uU,uD) with Neumann-like edge reflection."""
    uR = np.empty_like(u); uL = np.empty_like(u); uU = np.empty_like(u); uD = np.empty_like(u)
    uR[:, :-1] = u[:, 1:];   uR[:, -1] = u[:, -2]
    uL[:, 1:]  = u[:, :-1];  uL[:, 0]  = u[:, 1]
    uU[:-1, :] = u[1:, :];   uU[-1, :] = u[-2, :]
    uD[1:, :]  = u[:-1, :];  uD[0, :]  = u[1, :]
    return uR, uL, uU, uD


def div_c2_grad(u: np.ndarray, c2: np.ndarray, dx: float) -> np.ndarray:
    """Discrete ∇·(c²∇u) using face-averaged c² and Neumann edges."""
    uR, uL, uU, uD = neumann_shift(u)
    cR, cL, cU, cD = neumann_shift(c2)

    c2R = 0.5*(c2 + cR)
    c2L = 0.5*(c2 + cL)
    c2U = 0.5*(c2 + cU)
    c2D = 0.5*(c2 + cD)

    return (c2R*(uR - u) - c2L*(u - uL) + c2U*(uU - u) - c2D*(u - uD)) / (dx*dx)


def compute_stable_substeps(dt_frame: float,
                            dx: float,
                            c2: Optional[np.ndarray],
                            V: Optional[np.ndarray],
                            spf_hint: int = 1) -> Tuple[int, float]:
    """Choose a conservative number of substeps for the explicit solver.

    The finite-difference update is constrained both by wave propagation
    (CFL-like bound using the fastest local speed in ``c2``) and by the
    local oscillation frequency induced by positive potentials ``V``.
    """
    spf = max(1, int(spf_hint))
    dt = float(dt_frame) / spf

    cmax = 0.0
    if c2 is not None and np.size(c2) > 0:
        c2_max = float(np.nanmax(np.clip(c2, 0.0, None)))
        cmax = math.sqrt(max(c2_max, 0.0))
    dt_wave = np.inf if cmax <= 0.0 else 0.55 * float(dx) / (cmax * math.sqrt(2.0) + 1e-12)

    vmax = 0.0
    if V is not None and np.size(V) > 0:
        vmax = float(np.nanmax(np.clip(V, 0.0, None)))
    dt_potential = np.inf if vmax <= 0.0 else 1.60 / (math.sqrt(vmax) + 1e-12)

    dt_limit = min(dt_wave, dt_potential)
    if not np.isfinite(dt_limit) or dt_limit <= 0.0:
        dt_limit = max(dt, 1e-6)

    if dt > dt_limit:
        spf = max(spf, int(math.ceil(dt / max(dt_limit, 1e-12))))
        dt = float(dt_frame) / spf

    return int(spf), float(dt)


# ----------------------------- Potential presets -----------------------------

def gauss_sum(X: np.ndarray, Y: np.ndarray, pts: np.ndarray, V0: float, sig: float) -> np.ndarray:
    V = np.zeros_like(X, dtype=np.float32)
    inv2s2 = 1.0/(2*sig*sig + 1e-12)
    for (xi, yi) in pts:
        V += float(V0) * np.exp(-((X-xi)**2 + (Y-yi)**2)*inv2s2).astype(np.float32)
    return V


def preset_lattice(X, Y, P, rng):
    rows, cols = 6, 12
    sx, sy = 0.55, 0.85
    x0, y0 = -3.10, -2.56
    pts = np.array([[x0 + c*sx, y0 + r*sy] for r in range(rows) for c in range(cols)], dtype=np.float32)
    V = gauss_sum(X, Y, pts, P.V0, P.Vsig).astype(np.float32)
    return V, None, None, pts


def preset_random_scatter(X, Y, P, rng):
    n = int(getattr(P, "Nscat", 72))
    pts = rng.uniform(-P.L/2*0.92, P.L/2*0.92, size=(n, 2)).astype(np.float32)
    V = gauss_sum(X, Y, pts, P.V0, P.Vsig).astype(np.float32)
    return V, None, None, pts


def preset_two_cylinders(X, Y, P, rng):
    sep = float(getattr(P, "cyl_sep", 1.6))
    rad = float(getattr(P, "cyl_rad", 0.22))
    sig = max(rad, P.Vsig)
    pts = np.array([[-sep/2, 0.0], [+sep/2, 0.0]], np.float32)
    V = gauss_sum(X, Y, pts, P.V0, sig).astype(np.float32)
    return V, None, None, pts


def preset_double_slit(X, Y, P, rng):
    wall_x = float(getattr(P, "wall_x", 0.0))
    thick = float(getattr(P, "wall_thick", 0.18))
    slit_h = float(getattr(P, "slit_h", 0.55))
    slit_sep = float(getattr(P, "slit_sep", 1.10))
    y1, y2 = +slit_sep/2, -slit_sep/2
    wall = (np.abs(X - wall_x) <= thick/2)
    slit = (np.abs(Y - y1) <= slit_h/2) | (np.abs(Y - y2) <= slit_h/2)
    mask = wall & (~slit)
    return np.zeros_like(X, np.float32), mask, None, np.zeros((0, 2), np.float32)


def preset_single_slit(X, Y, P, rng):
    wall_x = float(getattr(P, "wall_x", 0.0))
    thick = float(getattr(P, "wall_thick", 0.18))
    slit_h = float(getattr(P, "slit_h", 0.70))
    y0 = float(getattr(P, "slit_y", 0.0))
    wall = (np.abs(X - wall_x) <= thick/2)
    slit = (np.abs(Y - y0) <= slit_h/2)
    mask = wall & (~slit)
    return np.zeros_like(X, np.float32), mask, None, np.zeros((0, 2), np.float32)


def preset_ring_barrier(X, Y, P, rng):
    r0 = float(getattr(P, "ring_r", 2.2))
    th = float(getattr(P, "ring_th", 0.22))
    r = np.sqrt(X*X + Y*Y)
    mask = np.abs(r - r0) <= th/2
    return np.zeros_like(X, np.float32), mask, None, np.zeros((0, 2), np.float32)


def preset_waveguide(X, Y, P, rng):
    y0 = float(getattr(P, "wg_y0", 0.0))
    half = float(getattr(P, "wg_half", 1.0))
    thick = float(getattr(P, "wg_thick", 0.20))
    mask = (np.abs(Y - (y0 + half)) <= thick/2) | (np.abs(Y - (y0 - half)) <= thick/2)
    return np.zeros_like(X, np.float32), mask, None, np.zeros((0, 2), np.float32)


def _generate_maze_bitmap(rows: int, cols: int, seed: int = 20260309) -> np.ndarray:
    rng = np.random.default_rng(seed)
    grid = np.ones((2 * rows + 1, 2 * cols + 1), dtype=np.uint8)
    visited = np.zeros((rows, cols), dtype=bool)

    def carve(r: int, c: int):
        visited[r, c] = True
        grid[2 * r + 1, 2 * c + 1] = 0
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr, nc]:
                grid[2 * r + 1 + dr, 2 * c + 1 + dc] = 0
                carve(nr, nc)

    carve(0, 0)
    grid[1, 0] = 0
    grid[-2, -1] = 0
    return grid


def preset_maze_rects(X, Y, P, rng):
    h, w = X.shape
    maze = _generate_maze_bitmap(9, 11)
    canvas = np.zeros((h, w), dtype=np.uint8)
    pad_y = max(8, int(round(0.07 * h)))
    pad_x = max(8, int(round(0.07 * w)))
    inner = cv2.resize(
        maze * 255,
        (max(8, w - 2 * pad_x), max(8, h - 2 * pad_y)),
        interpolation=cv2.INTER_NEAREST,
    )
    canvas[pad_y:pad_y + inner.shape[0], pad_x:pad_x + inner.shape[1]] = inner
    k = max(1, int(round(min(h, w) / 240)))
    if k > 1:
        ker = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * k + 1, 2 * k + 1))
        canvas = cv2.dilate(canvas, ker, iterations=1)
    # abre la entrada y la salida para que el dibujo se lea como laberinto real
    canvas[max(0, pad_y + inner.shape[0] // 12 - 2 * k): min(h, pad_y + inner.shape[0] // 12 + 2 * k + 1), :pad_x + 2 * k] = 0
    canvas[max(0, pad_y + 11 * inner.shape[0] // 12 - 2 * k): min(h, pad_y + 11 * inner.shape[0] // 12 + 2 * k + 1), w - pad_x - 2 * k:] = 0
    mask = canvas > 127
    return np.zeros_like(X, np.float32), mask, None, np.zeros((0, 2), np.float32)


def preset_checkerboard_refract(X, Y, P, rng):
    kx = float(getattr(P, "cb_kx", 2.6))
    ky = float(getattr(P, "cb_ky", 2.0))
    patt = (np.sign(np.sin(kx*X) * np.sin(ky*Y)) + 1.0) / 2.0
    s = float(P.n_strength)
    n = 1.0 + s*(patt - 0.5)
    n = np.clip(n, 0.4, 3.0).astype(np.float32)
    return np.zeros_like(X, np.float32), None, n, np.zeros((0, 2), np.float32)


def preset_gaussian_lens_refract(X, Y, P, rng):
    sig = float(getattr(P, "lens_sig", 1.8))
    g = np.exp(-(X*X + Y*Y)/(2*sig*sig + 1e-12)).astype(np.float32)
    s = float(P.n_strength)
    n = 1.0 + s*g
    return np.zeros_like(X, np.float32), None, n.astype(np.float32), np.zeros((0, 2), np.float32)


def preset_periodic_cosine(X, Y, P, rng):
    period = max(0.8, 2.8 * float(P.Vsig) * float(P.L))
    k = 2*np.pi / period
    raw = 0.5*(np.cos(k*X) + np.cos(k*Y) + 2.0)
    raw = raw / (np.max(raw) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def preset_yukawa_central(X, Y, P, rng):
    lam = 0.65 + 6.0*float(P.Vsig)
    r = np.sqrt(X*X + Y*Y)
    raw = np.exp(-r/(lam + 1e-12)) / (r + 0.25)
    raw = raw / (np.max(np.abs(raw)) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def preset_heart_potential(X, Y, P, rng):
    sx = 2.0
    sy = 1.8
    xx = X / sx
    yy = (Y + 0.12) / sy
    heart = (((xx*xx + yy*yy - 1.0)**3 - xx*xx*yy*yy*yy) <= 0.0).astype(np.float32)
    blur_sigma = max(1.0, 18.0 * float(P.Vsig))
    raw = cv2.GaussianBlur(heart, (0, 0), blur_sigma)
    raw = raw / (np.max(raw) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def preset_ghost_8bit(X, Y, P, rng):
    rows = [
        "000000011110000000",
        "000001100001100000",
        "000001000000100000",
        "000010000000010000",
        "000010000000010000",
        "111010110011010011",
        "111110110011011111",
        "100110010001011001",
        "100000000000000001",
        "110000001100000010",
        "011000000000000110",
        "000100000000001000",
        "000100000000001000",
        "000100000000001000",
        "000100000000001000",
        "000010000000010000",
        "000001100001100000",
        "000001111111100000",
    ]
    ghost = np.array([[1.0 if ch == "1" else 0.0 for ch in row] for row in rows], dtype=np.float32)
    h, w = ghost.shape
    span_x = 5.8
    span_y = 5.4
    x_min, x_max = -span_x/2, span_x/2
    y_min, y_max = -span_y/2, span_y/2

    raw = np.zeros_like(X, dtype=np.float32)
    inside = (X >= x_min) & (X < x_max) & (Y >= y_min) & (Y < y_max)
    if np.any(inside):
        ix = np.floor((X[inside] - x_min) / (span_x / w)).astype(int)
        iy = np.floor((y_max - Y[inside]) / (span_y / h)).astype(int)
        ix = np.clip(ix, 0, w - 1)
        iy = np.clip(iy, 0, h - 1)
        raw[inside] = ghost[iy, ix]

    sigma = max(0.0, 8.0 * float(P.Vsig) - 0.1)
    if sigma > 0.05:
        raw = cv2.GaussianBlur(raw, (0, 0), sigmaX=sigma, sigmaY=sigma)

    raw = raw / (np.max(raw) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)



# Constructor genérico para presets tipo pixel art.
#
# Cada carácter de la matriz representa un "pixel físico" del potencial.
# Luego esa matriz se proyecta sobre el plano continuo (X,Y), de modo que
# todos los píxeles tengan el mismo tamaño geométrico.
def _pixel_art_potential(
    X: np.ndarray,
    Y: np.ndarray,
    P: SimParams,
    rows: list[str],
    palette_weights: Dict[str, float],
    *,
    span_x: float,
    span_y: float,
    sigma_scale: float = 8.0,
) -> Tuple[np.ndarray, None, None, np.ndarray]:
    if not rows:
        return np.zeros_like(X, dtype=np.float32), None, None, np.zeros((0, 2), np.float32)

    width = max(len(row) for row in rows)
    width = max(1, int(width))
    norm_rows = [str(row).ljust(width, '.') for row in rows]
    sprite = np.array([[float(palette_weights.get(ch, 0.0)) for ch in row] for row in norm_rows], dtype=np.float32)
    h, w = sprite.shape
    x_min, x_max = -span_x / 2.0, span_x / 2.0
    y_min, y_max = -span_y / 2.0, span_y / 2.0

    raw = np.zeros_like(X, dtype=np.float32)
    inside = (X >= x_min) & (X < x_max) & (Y >= y_min) & (Y < y_max)
    if np.any(inside):
        ix = np.floor((X[inside] - x_min) / (span_x / w)).astype(int)
        iy = np.floor((y_max - Y[inside]) / (span_y / h)).astype(int)
        ix = np.clip(ix, 0, w - 1)
        iy = np.clip(iy, 0, h - 1)
        raw[inside] = sprite[iy, ix]

    sigma = max(0.0, sigma_scale * float(P.Vsig) - 0.08)
    if sigma > 0.05:
        raw = cv2.GaussianBlur(raw, (0, 0), sigmaX=sigma, sigmaY=sigma)

    peak = float(np.max(raw))
    if peak > 1e-8:
        raw = raw / peak
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def preset_megaman_8bit(X, Y, P, rng):
    rows = [
        "............KKK...........",
        ".LKK......KKKLLK..........",
        ".KDDK....KDLLKLLK.....KKL.",
        "KDDDDK..KDDDDDKKKK...KDDK.",
        "KDDDKK..KDDDDDKLLDKLKDDDDK",
        ".KDDKDKKLDDDDDDKKDKLKKDDDK",
        ".LKDDDDKLDDY...DD.KKDKDDK.",
        "...KDDDKLDYW.KKYK.KDDDDKL.",
        "...LKKDLKDYW.KKYK.KDDDKL..",
        ".....KLLKDYY...YWYLDKKK...",
        "......KLLKDYYKKKYKLLKL....",
        "......LKLLKYKKKKKLLK......",
        "......LKLLLKYKKKLLKL......",
        "........KLLLLLLLLKKL......",
        "........KLLLLLLLLKLL......",
        "........KLLLLLLLLKKK......",
        "........KDDDDDDDDLLLK.....",
        "........KDDDDDDDLLLLLKK...",
        "........KLLDDDDLLLLLLKK...",
        "........KLLLLKKKKLLLLKK...",
        "........KLLLK....KDDDDK...",
        "........KLLDK....KDDDDDKL.",
        "........KDDDK....KKDDDDKL.",
        "........KDDDDK.....KKKK...",
        ".........KDDDK............",
        ".........KDDDK............",
        ".........KDDDK............",
        ".........KDDDK............",
        ".........KDDDK............",
        "..........KKK.............",
    ]
    weights = {
        ".": 0.00,
        "W": 0.08,
        "Y": 0.18,
        "L": 0.40,
        "D": 0.68,
        "K": 1.00,
    }
    return _pixel_art_potential(X, Y, P, rows, weights, span_x=6.7, span_y=7.7, sigma_scale=5.0)


def _filled_polar_potential(X: np.ndarray, Y: np.ndarray, r_edge: np.ndarray, P: SimParams) -> Tuple[np.ndarray, None, None, np.ndarray]:
    r = np.sqrt(X*X + Y*Y)
    inside = (r <= np.clip(r_edge, 0.0, None)).astype(np.float32)
    blur_sigma = max(0.8, 18.0 * float(P.Vsig))
    raw = cv2.GaussianBlur(inside, (0, 0), blur_sigma)
    raw = raw / (np.max(raw) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def _ring_polar_potential(X: np.ndarray, Y: np.ndarray, r_edge: np.ndarray, P: SimParams, thickness_scale: float = 1.0) -> Tuple[np.ndarray, None, None, np.ndarray]:
    r = np.sqrt(X*X + Y*Y)
    thick = max(0.08, (0.18 + 0.9 * float(P.Vsig)) * thickness_scale)
    raw = np.exp(-0.5 * ((r - np.clip(r_edge, 0.0, None)) / thick) ** 2).astype(np.float32)
    raw = cv2.GaussianBlur(raw, (0, 0), max(0.6, 5.0 * float(P.Vsig)))
    raw = raw / (np.max(raw) + 1e-6)
    V = (float(P.V0) * raw).astype(np.float32)
    return V, None, None, np.zeros((0, 2), np.float32)


def preset_polar_rose4(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 2.45 * np.abs(np.cos(2.0 * theta))
    return _filled_polar_potential(X, Y, r_edge, P)


def preset_polar_rose6(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 2.55 * np.abs(np.cos(3.0 * theta))
    return _filled_polar_potential(X, Y, r_edge, P)


def preset_polar_cardioid(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 1.15 + 1.15 * (1.0 + np.cos(theta))
    return _filled_polar_potential(X, Y, r_edge, P)


def preset_polar_lemniscate(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 2.25 * np.sqrt(np.maximum(np.cos(2.0 * theta), 0.0))
    return _filled_polar_potential(X, Y, r_edge, P)


def preset_polar_star8(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 2.05 * (0.58 + 0.42 * np.cos(8.0 * theta))
    return _ring_polar_potential(X, Y, r_edge, P, thickness_scale=0.9)


def preset_polar_crown12(X, Y, P, rng):
    theta = np.arctan2(Y, X)
    r_edge = 2.35 + 0.34 * np.cos(12.0 * theta)
    return _ring_polar_potential(X, Y, r_edge, P, thickness_scale=0.75)


# Banco principal de presets.
# Cada preset devuelve una combinación de:
#   V(x,y)   -> potencial escalar
#   mask     -> paredes/obstáculos duros
#   n_map    -> mapa de índice efectivo
#   pts      -> puntos decorativos/centros de dispersores
PRESETS: Dict[str, Callable] = {
    "1) Red cristalina de dispersores": preset_lattice,
    "2) Nube aleatoria de dispersores": preset_random_scatter,
    "3) Dúo de cilindros suaves": preset_two_cylinders,
    "4) Doble rendija dura": preset_double_slit,
    "5) Rendija única": preset_single_slit,
    "6) Anillo reflectante": preset_ring_barrier,
    "7) Guía de onda plana": preset_waveguide,
    "8) Laberinto realista": preset_maze_rects,
    "9) Damero refractivo": preset_checkerboard_refract,
    "10) Lente gaussiana": preset_gaussian_lens_refract,
    "11) Potencial cosenoidal 2D": preset_periodic_cosine,
    "12) Yukawa central": preset_yukawa_central,
    "13) Potencial corazón": preset_heart_potential,
    "14) 8-bit ghost": preset_ghost_8bit,
    "15) Rosa polar de 4 pétalos": preset_polar_rose4,
    "16) Rosa polar de 6 pétalos": preset_polar_rose6,
    "17) Cardioide polar": preset_polar_cardioid,
    "18) Lemniscata polar": preset_polar_lemniscate,
    "19) Estrella polar de 8 lóbulos": preset_polar_star8,
    "20) Corona polar de 12 sectores": preset_polar_crown12,
}

PRESET_META = {
    "1) Red cristalina de dispersores": {
        "kind": "potential",
        "channel": "Potencial cristalino",
        "overlay": "V",
        "idea": "Una red regular de gaussianas crea un paisaje periódico para la onda.",
        "observe": "Busca desvíos repetidos, franjas ordenadas y caminos preferentes.",
        "focus": "Sube V0 para endurecer la dispersión y σ para ensanchar cada dispersor.",
    },
    "2) Nube aleatoria de dispersores": {
        "kind": "potential",
        "channel": "Potencial desordenado",
        "overlay": "V",
        "idea": "Las gaussianas se distribuyen sin patrón fijo y el medio pierde simetría.",
        "observe": "Mira sombras locales, trayectorias quebradas y dispersión irregular.",
        "focus": "V0 aumenta el desorden efectivo; σ vuelve la nube más suave y menos granular.",
    },
    "3) Dúo de cilindros suaves": {
        "kind": "potential",
        "channel": "Potencial de dos centros",
        "overlay": "V",
        "idea": "Dos centros suaves bastan para estudiar dispersión alrededor de objetos separados.",
        "observe": "Fíjate en la zona entre ambos centros y en la sombra detrás de ellos.",
        "focus": "Úsalo con V0 moderado para ver curvatura sin saturar la escena.",
    },
    "4) Doble rendija dura": {
        "kind": "obstacle",
        "channel": "Pared sólida con dos aperturas",
        "overlay": "Mask",
        "idea": "Una pared rígida deja pasar la onda solo por dos rendijas coherentes.",
        "observe": "Delante domina la incidencia; detrás aparece un patrón claro de interferencia.",
        "focus": "Aquí manda la geometría de la pared y el tamaño del paquete incidente.",
    },
    "5) Rendija única": {
        "kind": "obstacle",
        "channel": "Pared sólida con una apertura",
        "overlay": "Mask",
        "idea": "La onda cruza una sola abertura angosta y luego se abre por difracción.",
        "observe": "Mira cómo el frente sale en abanico al pasar por la rendija.",
        "focus": "Compárala con la doble rendija para separar difracción de interferencia.",
    },
    "6) Anillo reflectante": {
        "kind": "obstacle",
        "channel": "Contorno reflector circular",
        "overlay": "Mask",
        "idea": "Una barrera circular obliga a la onda a negociar con una geometría cerrada.",
        "observe": "Busca rebotes curvos, ecos y focos geométricos aproximados.",
        "focus": "Con borde reflectante externo aparece una caja dentro de otra.",
    },
    "7) Guía de onda plana": {
        "kind": "obstacle",
        "channel": "Canal con paredes",
        "overlay": "Mask",
        "idea": "Dos paredes paralelas canalizan la propagación en una dirección preferente.",
        "observe": "Mira los rebotes laterales y el guiado sostenido de la energía.",
        "focus": "Baja γ si quieres que los ecos dentro del canal duren más.",
    },
    "8) Laberinto realista": {
        "kind": "obstacle",
        "channel": "Paredes de laberinto",
        "overlay": "Mask",
        "idea": "Hay pasillos, esquinas y salidas reales: la onda debe encontrar su ruta.",
        "observe": "Busca retrasos entre corredores, rebotes múltiples y zonas de sombra.",
        "focus": "Funciona mejor con paquetes compactos, para leer mejor cada recorrido.",
    },
    "9) Damero refractivo": {
        "kind": "refractive",
        "channel": "Índice de refracción alternado",
        "overlay": "n",
        "idea": "El medio alterna regiones con distinta velocidad local, como un tablero.",
        "observe": "Mira cómo el frente se quiebra al cruzar interfaces del damero.",
        "focus": "n_strength es la perilla principal: sube y la refracción se vuelve dominante.",
    },
    "10) Lente gaussiana": {
        "kind": "refractive",
        "channel": "Índice gaussiano",
        "overlay": "n",
        "idea": "Una variación suave del índice actúa como una lente distribuida.",
        "observe": "Busca curvatura progresiva, compresión lateral y desvío suave del frente.",
        "focus": "Sirve para distinguir refracción continua de reflexión en paredes duras.",
    },
    "11) Potencial cosenoidal 2D": {
        "kind": "potential",
        "channel": "Potencial periódico bidimensional",
        "overlay": "V",
        "idea": "El potencial modula toda la grilla con un relieve cosenoidal extendido.",
        "observe": "Fíjate en rutas preferidas y patrones que heredan la periodicidad del medio.",
        "focus": "σ cambia la escala del relieve; V0 cambia cuán difícil es atravesarlo.",
    },
    "12) Yukawa central": {
        "kind": "potential",
        "channel": "Potencial central de corto alcance",
        "overlay": "V",
        "idea": "La interacción es fuerte cerca del centro y cae rápido con la distancia.",
        "observe": "Mira la deformación local del frente cerca del origen y su decaimiento lejos.",
        "focus": "Compáralo con medios extensos: aquí el alcance corto es la clave.",
    },
    "13) Potencial corazón": {
        "kind": "potential",
        "channel": "Potencial geométrico",
        "overlay": "V",
        "idea": "La geometría del potencial dibuja una figura cerrada y marca la dinámica.",
        "observe": "Busca la huella de la silueta en la sombra y en la dispersión.",
        "focus": "Con σ bajo la forma se lee mejor; con σ alto se vuelve más suave.",
    },
    "14) 8-bit ghost": {
        "kind": "potential",
        "channel": "Potencial pixelado discreto",
        "overlay": "V",
        "idea": "Los píxeles oscuros levantan el potencial y los claros dejan paso libre a la onda.",
        "observe": "Busca contornos escalonados, sombras nítidas y dispersión con firma digital.",
        "focus": "σ pequeño conserva el estilo 8-bit; V0 alto vuelve más dura la interacción.",
        "postscript": "¿Por qué un fantasma? Porque lo soy. ¿Por qué en 8-bit? Porque luce genial. ¿Por qué estas palabras? Porque te las escribo.",
    },
    "15) Rosa polar de 4 pétalos": {
        "kind": "potential",
        "channel": "Potencial polar cerrado",
        "overlay": "V",
        "idea": "Una curva polar rellena cuatro lóbulos con simetría de orden cuatro.",
        "observe": "Mira cómo cada pétalo captura o desvía parte del frente.",
        "focus": "Buen puente entre geometría polar y lectura física del potencial.",
    },
    "16) Rosa polar de 6 pétalos": {
        "kind": "potential",
        "channel": "Potencial polar multipétalo",
        "overlay": "V",
        "idea": "La rosa de seis pétalos añade más estructura angular al mismo esquema polar.",
        "observe": "Compara la complejidad angular con la rosa de cuatro pétalos.",
        "focus": "Con paquete amplio iluminas varios lóbulos a la vez.",
    },
    "17) Cardioide polar": {
        "kind": "potential",
        "channel": "Potencial cardioide",
        "overlay": "V",
        "idea": "La cardioide rompe la simetría circular con una geometría limpia y anisótropa.",
        "observe": "Incide desde lados distintos y compara cómo cambia la dispersión.",
        "focus": "Úsalo para hablar de anisotropía geométrica sin recurrir al azar.",
    },
    "18) Lemniscata polar": {
        "kind": "potential",
        "channel": "Potencial de doble lóbulo",
        "overlay": "V",
        "idea": "Dos lóbulos unidos por un cuello central organizan la propagación en dos regiones.",
        "observe": "Mira cómo la onda reparte amplitud entre ambos brazos.",
        "focus": "El cuello central controla cuánta comunicación hay entre los lóbulos.",
    },
    "19) Estrella polar de 8 lóbulos": {
        "kind": "potential",
        "channel": "Barrera polar estrellada",
        "overlay": "V",
        "idea": "Un contorno estrellado selecciona direcciones y rompe la isotropía angular.",
        "observe": "Busca puntas, sombras direccionales y zonas de paso preferente.",
        "focus": "Con V0 medio-alto la estrella queda más legible en la dispersión.",
    },
    "20) Corona polar de 12 sectores": {
        "kind": "potential",
        "channel": "Anillo angular modulado",
        "overlay": "V",
        "idea": "Una corona casi circular respira con una modulación angular de doce sectores.",
        "observe": "Mira franjas radiales favorecidas y ventanas angulares de propagación.",
        "focus": "Ideal para hablar de simetría discreta en coordenadas polares.",
    },
}


PRESET_WAVE_DEFAULTS: Dict[str, Dict[str, float]] = {
    "1) Red cristalina de dispersores": {"x0": -3.80, "y0": 0.00, "R0": 0.62, "k0": 34.0, "edge": 0.14},
    "2) Nube aleatoria de dispersores": {"x0": -3.90, "y0": -1.20, "R0": 0.60, "k0": 34.0, "edge": 0.14},
    "3) Dúo de cilindros suaves": {"x0": -3.20, "y0": 0.00, "R0": 0.62, "k0": 36.0, "edge": 0.13},
    "4) Doble rendija dura": {"x0": -3.60, "y0": 0.00, "R0": 0.68, "k0": 34.0, "edge": 0.14},
    "5) Rendija única": {"x0": -3.60, "y0": 0.00, "R0": 0.66, "k0": 34.0, "edge": 0.14},
    "6) Anillo reflectante": {"x0": -2.20, "y0": 0.00, "R0": 0.56, "k0": 33.0, "edge": 0.14},
    "7) Guía de onda plana": {"x0": -3.70, "y0": 0.00, "R0": 0.54, "k0": 35.0, "edge": 0.13},
    "8) Laberinto realista": {"x0": -4.15, "y0": -3.25, "R0": 0.40, "k0": 29.0, "edge": 0.14},
    "9) Damero refractivo": {"x0": -3.80, "y0": 0.00, "R0": 0.66, "k0": 34.0, "edge": 0.14},
    "10) Lente gaussiana": {"x0": -3.50, "y0": 0.00, "R0": 0.62, "k0": 34.0, "edge": 0.14},
    "11) Potencial cosenoidal 2D": {"x0": -3.70, "y0": -1.00, "R0": 0.58, "k0": 32.0, "edge": 0.14},
    "12) Yukawa central": {"x0": -3.20, "y0": 0.00, "R0": 0.60, "k0": 30.0, "edge": 0.14},
    "13) Potencial corazón": {"x0": -3.20, "y0": -0.50, "R0": 0.58, "k0": 31.0, "edge": 0.14},
    "14) 8-bit ghost": {"x0": -4.10, "y0": 0.95, "R0": 1.00, "k0": 18.0, "edge": 0.22},
    "15) Rosa polar de 4 pétalos": {"x0": -3.25, "y0": 0.00, "R0": 0.62, "k0": 31.0, "edge": 0.15},
    "16) Rosa polar de 6 pétalos": {"x0": -3.35, "y0": 0.00, "R0": 0.62, "k0": 30.0, "edge": 0.15},
    "17) Cardioide polar": {"x0": -3.70, "y0": 0.35, "R0": 0.60, "k0": 31.0, "edge": 0.14},
    "18) Lemniscata polar": {"x0": -3.25, "y0": 0.00, "R0": 0.58, "k0": 30.0, "edge": 0.14},
    "19) Estrella polar de 8 lóbulos": {"x0": -3.20, "y0": -0.15, "R0": 0.56, "k0": 31.5, "edge": 0.14},
    "20) Corona polar de 12 sectores": {"x0": -3.20, "y0": 0.00, "R0": 0.60, "k0": 31.0, "edge": 0.14},
}

PRESET_MODEL_DEFAULTS: Dict[str, Dict[str, object]] = {
    "1) Red cristalina de dispersores": {"V0": 180.0, "Vsig": 0.090, "c": 0.34, "gamma": 0.010, "boundary_mode": "Sin borde (salida absorbente)"},
    "2) Nube aleatoria de dispersores": {"V0": 220.0, "Vsig": 0.075, "c": 0.34, "gamma": 0.012, "boundary_mode": "Sin borde (salida absorbente)"},
    "3) Dúo de cilindros suaves": {"V0": 280.0, "Vsig": 0.180, "c": 0.34, "gamma": 0.010, "boundary_mode": "Sin borde (salida absorbente)"},
    "4) Doble rendija dura": {"c": 0.34, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "5) Rendija única": {"c": 0.34, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "6) Anillo reflectante": {"c": 0.33, "gamma": 0.008, "boundary_mode": "Reflexión en los 4 bordes"},
    "7) Guía de onda plana": {"c": 0.35, "gamma": 0.006, "boundary_mode": "Tubo horizontal (reflexión arriba/abajo)"},
    "8) Laberinto realista": {"c": 0.31, "gamma": 0.011, "boundary_mode": "Sin borde (salida absorbente)"},
    "9) Damero refractivo": {"n_strength": 0.58, "c": 0.34, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "10) Lente gaussiana": {"n_strength": 0.82, "c": 0.34, "gamma": 0.006, "boundary_mode": "Sin borde (salida absorbente)"},
    "11) Potencial cosenoidal 2D": {"V0": 110.0, "Vsig": 0.120, "c": 0.34, "gamma": 0.009, "boundary_mode": "Sin borde (salida absorbente)"},
    "12) Yukawa central": {"V0": 220.0, "Vsig": 0.100, "c": 0.32, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "13) Potencial corazón": {"V0": 260.0, "Vsig": 0.120, "c": 0.34, "gamma": 0.009, "boundary_mode": "Sin borde (salida absorbente)"},
    "14) 8-bit ghost": {"V0": 320.0, "Vsig": 0.035, "c": 0.30, "gamma": 0.007, "boundary_mode": "Sin borde (salida absorbente)"},
    "15) Rosa polar de 4 pétalos": {"V0": 220.0, "Vsig": 0.090, "c": 0.33, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "16) Rosa polar de 6 pétalos": {"V0": 220.0, "Vsig": 0.085, "c": 0.33, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "17) Cardioide polar": {"V0": 250.0, "Vsig": 0.100, "c": 0.33, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "18) Lemniscata polar": {"V0": 240.0, "Vsig": 0.095, "c": 0.33, "gamma": 0.008, "boundary_mode": "Sin borde (salida absorbente)"},
    "19) Estrella polar de 8 lóbulos": {"V0": 280.0, "Vsig": 0.060, "c": 0.32, "gamma": 0.007, "boundary_mode": "Sin borde (salida absorbente)"},
    "20) Corona polar de 12 sectores": {"V0": 300.0, "Vsig": 0.055, "c": 0.32, "gamma": 0.007, "boundary_mode": "Sin borde (salida absorbente)"},
}



_PRESET_RENAME = {
    "1) Red cristalina de dispersores": "Red cristalina de dispersores",
    "2) Nube aleatoria de dispersores": "Nube aleatoria de dispersores",
    "3) Dúo de cilindros suaves": "Dúo de cilindros suaves",
    "4) Doble rendija dura": "Doble rendija dura",
    "5) Rendija única": "Rendija única",
    "6) Anillo reflectante": "Anillo reflectante",
    "7) Guía de onda plana": "Guía de onda plana",
    "8) Laberinto realista": "Laberinto realista",
    "9) Damero refractivo": "Damero refractivo",
    "10) Lente gaussiana": "Lente gaussiana",
    "11) Potencial cosenoidal 2D": "Potencial cosenoidal 2D",
    "12) Yukawa central": "Yukawa central",
    "13) Potencial corazón": "Potencial corazón",
    "14) 8-bit ghost": "8-bit ghost",
    "15) Rosa polar de 4 pétalos": "Rosa polar de 4 pétalos",
    "16) Rosa polar de 6 pétalos": "Rosa polar de 6 pétalos",
    "17) Cardioide polar": "Cardioide polar",
    "18) Lemniscata polar": "Lemniscata polar",
    "19) Estrella polar de 8 lóbulos": "Estrella polar de 8 lóbulos",
    "20) Corona polar de 12 sectores": "Corona polar de 12 sectores",
}

_PRESET_ORDER = [
    "8-bit ghost",
    "8-bit Mega Man",
    "Red cristalina de dispersores",
    "Nube aleatoria de dispersores",
    "Dúo de cilindros suaves",
    "Doble rendija dura",
    "Rendija única",
    "Anillo reflectante",
    "Guía de onda plana",
    "Laberinto realista",
    "Damero refractivo",
    "Lente gaussiana",
    "Potencial cosenoidal 2D",
    "Yukawa central",
    "Potencial corazón",
    "Rosa polar de 4 pétalos",
    "Rosa polar de 6 pétalos",
    "Cardioide polar",
    "Lemniscata polar",
    "Estrella polar de 8 lóbulos",
    "Corona polar de 12 sectores",
]

def _rekey_preset_table(table: Dict[str, object]) -> Dict[str, object]:
    return {str(_PRESET_RENAME.get(k, k)): v for k, v in table.items()}

def _reorder_preset_table(table: Dict[str, object]) -> Dict[str, object]:
    return {k: table[k] for k in _PRESET_ORDER if k in table}

PRESETS = _reorder_preset_table(_rekey_preset_table(PRESETS))
PRESET_META = _reorder_preset_table(_rekey_preset_table(PRESET_META))
PRESET_WAVE_DEFAULTS = _reorder_preset_table(_rekey_preset_table(PRESET_WAVE_DEFAULTS))
PRESET_MODEL_DEFAULTS = _reorder_preset_table(_rekey_preset_table(PRESET_MODEL_DEFAULTS))

PRESETS["8-bit Mega Man"] = preset_megaman_8bit
PRESET_META["8-bit Mega Man"] = {
    "kind": "potential",
    "channel": "Potencial pixelado multicapa",
    "overlay": "V",
    "idea": "El sprite usa varios niveles de potencial: contorno duro, azules intermedios y zonas claras más suaves.",
    "observe": "Mira cómo la onda distingue el contorno, la armadura y los detalles claros del sprite.",
    "focus": "V0 sube o baja toda la figura; σ suaviza los píxeles; cada color ya trae su propio peso en el potencial.",
}
PRESET_WAVE_DEFAULTS["8-bit Mega Man"] = {"x0": -4.35, "y0": 0.75, "R0": 0.92, "k0": 18.0, "edge": 0.20}
PRESET_MODEL_DEFAULTS["8-bit Mega Man"] = {"V0": 340.0, "Vsig": 0.018, "c": 0.30, "gamma": 0.007, "boundary_mode": "Sin borde (salida absorbente)"}

PRESET_META["8-bit ghost"]["channel"] = "Potencial pixelado discreto"
PRESET_META["8-bit ghost"]["postscript"] = PRESET_META["8-bit ghost"].get("postscript", "")

PRESETS = _reorder_preset_table(PRESETS)
PRESET_META = _reorder_preset_table(PRESET_META)
PRESET_WAVE_DEFAULTS = _reorder_preset_table(PRESET_WAVE_DEFAULTS)
PRESET_MODEL_DEFAULTS = _reorder_preset_table(PRESET_MODEL_DEFAULTS)

PRESET_NAME_ALIASES = {old: new for old, new in _PRESET_RENAME.items()}
PRESET_NAME_ALIASES.update({name: name for name in PRESETS})

# Memoria local simple: guarda el último estado útil del programa
# sin requerir perfiles ni cuentas de usuario.
APP_MEMORY_PATH = os.path.join(os.path.expanduser("~"), ".wavebox_potential_lab_memory.json")
MEMORY_FIELDS = [
    "L", "grid", "fps", "spf", "quality_mode", "c", "gamma", "absorb_strength", "absorb_width",
    "V0", "Vsig", "n_strength", "x0", "y0", "R0", "k0", "edge",
    "phase_freq", "phase_contrast", "amp_gain", "amp_pow", "glow", "fringe",
    "unsharp_sigma", "unsharp_amount", "show_dots", "border", "preview_scale",
    "overlay_mode", "boundary_mode", "theme_name", "app_theme_name",
    "show_perf_overlay", "auto_reset_on_preset", "auto_apply_preset_defaults",
]


def load_memory_blob() -> Dict[str, object]:
    try:
        with open(APP_MEMORY_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_memory_blob(data: Dict[str, object]) -> None:
    try:
        with open(APP_MEMORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass






# ----------------------------- UI helpers -----------------------------

# Estos spin boxes están pensados para edición directa:
# al hacer click, el número se selecciona completo para escribir encima
# sin pelear con el cursor o con flechas pequeñas.
class _FriendlySpinMixin:
    def _friendly_init(self):
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setAccelerated(True)
        self.setKeyboardTracking(False)
        self.setCorrectionMode(QtWidgets.QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        le = self.lineEdit()
        if le is not None:
            le.installEventFilter(self)

    def eventFilter(self, obj, event):
        le = self.lineEdit()
        if obj is le and event.type() in (QtCore.QEvent.Type.MouseButtonPress, QtCore.QEvent.Type.FocusIn):
            QtCore.QTimer.singleShot(0, le.selectAll)
        return super().eventFilter(obj, event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        le = self.lineEdit()
        if le is not None:
            QtCore.QTimer.singleShot(0, le.selectAll)


class FriendlySpinBox(_FriendlySpinMixin, QtWidgets.QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._friendly_init()


class FriendlyDoubleSpinBox(_FriendlySpinMixin, QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._friendly_init()


def wrap_with_step_buttons(spin: QtWidgets.QAbstractSpinBox, step_text_small: bool = False) -> QtWidgets.QWidget:
    row = QtWidgets.QWidget()
    lay = QtWidgets.QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)

    btn_minus = QtWidgets.QPushButton("−")
    btn_plus = QtWidgets.QPushButton("+")
    btn_minus.setFixedWidth(34 if step_text_small else 38)
    btn_plus.setFixedWidth(34 if step_text_small else 38)
    btn_minus.clicked.connect(spin.stepDown)
    btn_plus.clicked.connect(spin.stepUp)

    spin.setMinimumHeight(34)
    lay.addWidget(btn_minus)
    lay.addWidget(spin, 1)
    lay.addWidget(btn_plus)
    return row


def make_info_browser(html: str = "") -> QtWidgets.QTextBrowser:
    box = QtWidgets.QTextBrowser()
    box.setOpenExternalLinks(True)
    box.setOpenLinks(True)
    box.setReadOnly(True)
    box.setMinimumHeight(150)
    box.setHtml(html)
    return box


def project_info_html() -> str:
    return """
    <div style="max-width:920px; line-height:1.50; font-size:10.4pt;">
      <h1 style="margin-bottom:4px;">WaveBox Potential Lab</h1>
      <div style="color:#8da2c8; margin-bottom:14px;">Modelo, lecturas sugeridas y notas finales del proyecto</div>

      <h2>1. Qué ecuación integra</h2>
      <p>
        El programa evoluciona una ecuación de onda escalar lineal en dos dimensiones,
        <div style="margin:10px 0 14px 0; padding:10px 14px; border:1px solid #445a84; border-radius:10px; background:#0d1320; font-family:'Cambria Math','STIX Two Math','Times New Roman',serif; font-size:15pt; text-align:center;"><span style="font-style:italic;">u</span><sub>tt</sub> + γ <span style="font-style:italic;">u</span><sub>t</sub> = ∇·(<span style="font-style:italic;">c</span>(x,y)<sup>2</sup> ∇<span style="font-style:italic;">u</span>) − <span style="font-style:italic;">V</span>(x,y)<span style="font-style:italic;">u</span></div>.
        Aquí <b>u(x,y,t)</b> es la amplitud del campo, <b>c(x,y)</b> controla la velocidad local
        de propagación, <b>V(x,y)</b> actúa como paisaje de dispersión y <b>γ</b> introduce
        amortiguamiento lineal. Además, ciertas máscaras geométricas se usan como paredes
        efectivas imponiendo una condición tipo <code>u=0</code>.
      </p>

      <h2>2. Cómo conviene leer la física</h2>
      <p>
        La interpretación más precisa es la de un <b>laboratorio numérico de ondas escalares</b>
        en medios heterogéneos. Según el preset, el comportamiento recuerda problemas de
        óptica escalar, propagación en medios con índice variable, difracción por obstáculos
        y dispersión por potenciales estáticos. No pretende agotar una teoría física única:
        más bien muestra una familia de analogías útiles para pensar la propagación.
      </p>

      <h2>3. Dónde estudiar estos temas</h2>
      <ul>
        <li><a href="https://ocw.mit.edu/courses/8-03sc-physics-iii-vibrations-and-waves-fall-2016/">MIT OCW — Vibrations and Waves</a></li>
        <li><a href="https://farside.ph.utexas.edu/teaching/315/Waveshtml/Waveshtml.html">UT Austin — Waves (Richard Fitzpatrick)</a></li>
        <li><a href="https://www.damtp.cam.ac.uk/user/tong/em.html">David Tong — Electromagnetism</a></li>
        <li><a href="https://www.damtp.cam.ac.uk/user/tong/qm.html">David Tong — Quantum Mechanics</a></li>
        <li><a href="https://assets.openstax.org/oscms-prodcms/media/documents/UniversityPhysicsVolume3-WEB.pdf">OpenStax — University Physics Vol. 3</a></li>
      </ul>

      <h2>4. Bibliografía breve</h2>
      <ul>
        <li>Hecht, <i>Optics</i>.</li>
        <li>Griffiths, <i>Introduction to Quantum Mechanics</i>.</li>
        <li>Jackson, <i>Classical Electrodynamics</i>.</li>
        <li>Arfken, Weber &amp; Harris, <i>Mathematical Methods for Physicists</i>.</li>
        <li>Evans, <i>Partial Differential Equations</i>.</li>
      </ul>

      <h2>5. Notas finales</h2>
      <p>
        El proyecto es un experimento de probar los límites de lo que se puede hacer con
        <b>ChatGPT 5.2–5.4 Thinking / pensamiento ampliado</b> en tareas de simulación física
        y computación numérica, con el enfoque de aproximar la física teórica a la observación
        gráfica de sus modelos en el tiempo mediante simulaciones en tiempo real hechas con IA.
      </p>
      <blockquote style="margin:14px 0; padding:12px 14px; border-left:4px solid #6b8fff; background:#121722; border-radius:8px; color:#e9f0ff;">
        > Yo soy solo el mono detrás de la máquina de escribir que, por suerte del infinito, escribió el Quijote; salvo que no he escrito el Quijote, ni he escrito el código del programa. Como buen Quijote persiguiendo molinos de viento, esperando algún día el favor de Dulcinea, ¿no es eso cierto, Sancho?
      </blockquote>
      <p>
        La invitación es simple: mirar el código, cuestionarlo, corregirlo y usarlo como punto de
        partida para explorar mejor la relación entre modelo, simulación e intuición física.
      </p>
    </div>
    """


def make_metric_card(title: str, value: str = "—") -> Tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("metricCard")
    frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(8, 7, 8, 7)
    lay.setSpacing(2)

    lbl_title = QtWidgets.QLabel(title)
    lbl_title.setObjectName("metricTitle")
    lbl_title.setWordWrap(True)

    lbl_value = QtWidgets.QLabel(value)
    lbl_value.setObjectName("metricValue")
    lbl_value.setWordWrap(True)
    lbl_value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

    lay.addWidget(lbl_title)
    lay.addWidget(lbl_value)
    return frame, lbl_value



class AccordionSection(QtWidgets.QFrame):
    def __init__(self, title: str, content: QtWidgets.QWidget, parent=None):
        super().__init__(parent)
        self.title = title
        self._expanded = False
        self.setObjectName("accordionSection")
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self.header = QtWidgets.QPushButton(f"▸  {self.title}")
        self.header.setObjectName("accordionHeader")
        self.header.setCheckable(False)
        self.header.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

        self.body = QtWidgets.QFrame()
        self.body.setObjectName("accordionBody")
        self.body.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)

        body_lay = QtWidgets.QVBoxLayout(self.body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(content)

        lay.addWidget(self.header)
        lay.addWidget(self.body)
        self.set_expanded(False)

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        arrow = "▾" if self._expanded else "▸"
        self.header.setText(f"{arrow}  {self.title}")
        self.header.setProperty("expanded", self._expanded)
        self.header.style().unpolish(self.header)
        self.header.style().polish(self.header)
        self.body.setVisible(self._expanded)
        self.body.setMaximumHeight(16777215 if self._expanded else 0)
        self.updateGeometry()

    def is_expanded(self) -> bool:
        return bool(self._expanded)


# Widget principal: contiene el simulador, la interfaz de control
# y la lógica que sincroniza parámetros, presets y exportación.
class WaveBoxWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        pg.setConfigOptions(antialias=True)

        self.P = SimParams()
        self.default_P = SimParams()
        self.rng = np.random.default_rng(7)
        self.preset_name = list(PRESETS.keys())[0]

        self._running = True
        self.param_cards: Dict[str, QtWidgets.QWidget] = {}
        self.param_widgets: Dict[str, QtWidgets.QWidget] = {}
        loaded_memory = self._load_memory_state()
        if not loaded_memory:
            self._apply_preset_model_defaults(self.preset_name)
            self._apply_preset_wave_defaults(self.preset_name)
        self._setup_domain()

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)
        root.addWidget(split)

        # ---------- Left visual panel ----------
        left = QtWidgets.QWidget()
        llay = QtWidgets.QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        llay.setSpacing(6)

        top_info = QtWidgets.QFrame()
        top_info.setObjectName("panelCard")
        top_lay = QtWidgets.QHBoxLayout(top_info)
        top_lay.setContentsMargins(12, 10, 12, 10)
        top_lay.setSpacing(10)

        info_text_box = QtWidgets.QWidget()
        info_text_lay = QtWidgets.QVBoxLayout(info_text_box)
        info_text_lay.setContentsMargins(0, 0, 0, 0)
        info_text_lay.setSpacing(4)
        self.lbl_scene_title = QtWidgets.QLabel("Fenómeno actual")
        self.lbl_scene_title.setObjectName("titleMini")
        self.lbl_scene_caption = QtWidgets.QLabel("")
        self.lbl_scene_caption.setObjectName("caption")
        self.lbl_scene_caption.setWordWrap(True)
        info_text_lay.addWidget(self.lbl_scene_title)
        info_text_lay.addWidget(self.lbl_scene_caption)

        self.lbl_medium_badge = QtWidgets.QLabel("-")
        self.lbl_medium_badge.setObjectName("badge")
        self.lbl_medium_badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_medium_badge.setMinimumWidth(180)

        top_lay.addWidget(info_text_box, 1)
        top_lay.addWidget(self.lbl_medium_badge, 0)
        llay.addWidget(top_info)

        self.quick_actions_box = self._build_actions_group()
        self.quick_actions_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)
        llay.addWidget(self.quick_actions_box)

        self.view = pg.GraphicsLayoutWidget()
        self.view.setBackground((8, 9, 12))
        self.plot = self.view.addPlot(row=0, col=0)
        self.plot.hideAxis("left")
        self.plot.hideAxis("bottom")
        self.plot.setAspectLocked(True)
        self.img_item = pg.ImageItem(axisOrder="row-major")
        self.plot.addItem(self.img_item)

        self.hud = QtWidgets.QLabel("FPS: --")
        self.hud.setObjectName("hud")
        self.hud.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)

        self.alert_overlay = QtWidgets.QLabel("")
        self.alert_overlay.setObjectName("alertOverlay")
        self.alert_overlay.setWordWrap(True)
        self.alert_overlay.hide()

        hud_wrap = QtWidgets.QWidget()
        hud_lay = QtWidgets.QVBoxLayout(hud_wrap)
        hud_lay.setContentsMargins(10, 10, 10, 10)
        hud_lay.setSpacing(8)
        hud_lay.addWidget(self.hud, alignment=QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        hud_lay.addWidget(self.alert_overlay, alignment=QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        hud_lay.addStretch(1)

        stack = QtWidgets.QStackedLayout()
        frame = QtWidgets.QFrame()
        frame.setLayout(stack)
        stack.addWidget(self.view)
        stack.addWidget(hud_wrap)
        stack.setStackingMode(QtWidgets.QStackedLayout.StackingMode.StackAll)
        llay.addWidget(frame, 1)

        bottom_info = QtWidgets.QFrame()
        bottom_info.setObjectName("panelCard")
        bottom_info.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)
        bottom_lay = QtWidgets.QVBoxLayout(bottom_info)
        bottom_lay.setContentsMargins(10, 8, 10, 8)
        bottom_lay.setSpacing(6)

        self.lbl_status = QtWidgets.QLabel("Resumen rápido del estado actual")
        self.lbl_status.setObjectName("sectionCaption")
        bottom_lay.addWidget(self.lbl_status)

        metrics_grid = QtWidgets.QGridLayout()
        metrics_grid.setHorizontalSpacing(6)
        metrics_grid.setVerticalSpacing(6)

        metric_items = [
            ("Preset / canal", "metric_preset"),
            ("Mapa visible", "metric_overlay"),
            ("Bordes", "metric_boundary"),
            ("Dinámica", "metric_dynamics"),
            ("Parámetros", "metric_params"),
            ("Cómputo", "metric_compute"),
        ]
        for idx, (title, attr) in enumerate(metric_items):
            card, value_lbl = make_metric_card(title)
            setattr(self, attr, value_lbl)
            metrics_grid.addWidget(card, idx // 3, idx % 3)

        bottom_lay.addLayout(metrics_grid)
        self.lbl_hint = QtWidgets.QLabel("")
        self.lbl_hint.setObjectName("caption")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setMinimumHeight(22)
        bottom_lay.addWidget(self.lbl_hint)
        llay.addWidget(bottom_info)

        split.addWidget(left)

        # ---------- Right pedagogical sidebar ----------
        right_panel = QtWidgets.QWidget()
        right_panel.setMinimumWidth(350)
        right_panel.setMaximumWidth(500)
        right_panel_lay = QtWidgets.QVBoxLayout(right_panel)
        right_panel_lay.setContentsMargins(0, 0, 0, 0)
        right_panel_lay.setSpacing(8)

        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        right = QtWidgets.QWidget()
        rlay = QtWidgets.QVBoxLayout(right)
        rlay.setContentsMargins(8, 4, 8, 8)
        rlay.setSpacing(8)

        self.sidebar_sections: list[AccordionSection] = []
        sidebar_sections = [
            (self._build_preset_group(), "1. Elige el fenómeno físico"),
            (self._build_tech_group(), "2. Ajustes técnicos y visualización"),
            (self._build_model_group(), "3. Parámetros físicos del medio"),
            (self._build_visual_group(), "4. Personaliza la imagen y las ayudas visuales"),
        ]
        for idx, (widget, title) in enumerate(sidebar_sections):
            if isinstance(widget, QtWidgets.QGroupBox):
                widget.setTitle("")
                widget.setFlat(True)
                widget.setStyleSheet("QGroupBox { border: none; margin-top: 0px; padding: 0px; background: transparent; }")
            section = AccordionSection(title, widget)
            section.header.clicked.connect(lambda _checked=False, i=idx: self._toggle_sidebar_section(i))
            self.sidebar_sections.append(section)
            rlay.addWidget(section)

        rlay.addStretch(1)
        self._set_open_sidebar_section(0)

        right_scroll.setWidget(right)
        right_panel_lay.addWidget(right_scroll, 1)
        split.addWidget(right_panel)

        split.setStretchFactor(0, 6)
        split.setStretchFactor(1, 3)
        split.setSizes([1040, 420])

        # timers
        self._frames = 0
        self._fps_last = time.time()
        self._fps_value = 0.0
        self.perf_snapshot = read_system_snapshot()

        self.timer = QtCore.QTimer(self)
        self.timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

        self._debounce = QtCore.QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._rebuild_medium)

        self._perf_timer = QtCore.QTimer(self)
        self._perf_timer.setInterval(1200)
        self._perf_timer.timeout.connect(self._update_performance_snapshot)
        self._perf_timer.start()

        self._apply_app_theme()
        self._apply_theme_to_view()
        self._refresh_pedagogical_panel()
        self._update_performance_snapshot()
        self._remember_state()

    def _set_open_sidebar_section(self, index: int):
        if not hasattr(self, "sidebar_sections"):
            return
        for i, section in enumerate(self.sidebar_sections):
            section.set_expanded(i == index)

    def _toggle_sidebar_section(self, index: int):
        if not hasattr(self, "sidebar_sections"):
            return
        should_open = True
        if 0 <= index < len(self.sidebar_sections):
            should_open = not self.sidebar_sections[index].is_expanded()
        for i, section in enumerate(self.sidebar_sections):
            section.set_expanded(should_open if i == index else False)


    def _default_value_for_key(self, key: str):
        preset_model = PRESET_MODEL_DEFAULTS.get(self.preset_name, {})
        preset_wave = PRESET_WAVE_DEFAULTS.get(self.preset_name, {})
        if key in preset_model:
            return preset_model[key]
        if key in preset_wave:
            return preset_wave[key]
        mapping = {
            "quality_mode": quality_label_for_grid(int(getattr(self.default_P, "grid", 320))),
            "app_theme": self.default_P.app_theme_name,
            "theme": self.default_P.theme_name,
            "scale": self.default_P.preview_scale,
            "overlay": PRESET_META.get(self.preset_name, {}).get("overlay", self.default_P.overlay_mode),
            "perf_overlay": self.default_P.show_perf_overlay,
            "auto_apply_preset_defaults": self.default_P.auto_apply_preset_defaults,
        }
        if key in mapping:
            return mapping[key]
        return getattr(self.default_P, key, None)

    def _load_memory_state(self) -> bool:
        data = load_memory_blob()
        if not data:
            return False
        params = data.get("params")
        if isinstance(params, dict):
            for key in MEMORY_FIELDS:
                if key in params and hasattr(self.P, key):
                    try:
                        setattr(self.P, key, params[key])
                    except Exception:
                        pass
        preset_name = data.get("preset_name")
        preset_name = PRESET_NAME_ALIASES.get(preset_name, preset_name)
        if isinstance(preset_name, str) and preset_name in PRESETS:
            self.preset_name = preset_name
        else:
            self.preset_name = list(PRESETS.keys())[0]
        if str(getattr(self.P, "app_theme_name", "Noche")) not in APP_THEMES:
            self.P.app_theme_name = self.default_P.app_theme_name
        if str(getattr(self.P, "theme_name", "Original")) not in THEMES:
            self.P.theme_name = self.default_P.theme_name
        if str(getattr(self.P, "boundary_mode", self.default_P.boundary_mode)) not in BOUNDARY_MODES:
            self.P.boundary_mode = self.default_P.boundary_mode
        if str(getattr(self.P, "overlay_mode", self.default_P.overlay_mode)) not in set(OVERLAY_MODE_TO_DISPLAY.keys()):
            self.P.overlay_mode = self.default_P.overlay_mode
        qmode = str(getattr(self.P, "quality_mode", quality_label_for_grid(int(self.P.grid))))
        if qmode not in {"Baja", "Media", "Alta", "Personalizada"}:
            self.P.quality_mode = quality_label_for_grid(int(self.P.grid))
        return True

    def _remember_state(self):
        payload = {
            "version": 23,
            "preset_name": self.preset_name,
            "params": {key: getattr(self.P, key) for key in MEMORY_FIELDS if hasattr(self.P, key)},
        }
        save_memory_blob(payload)

    def _reset_single_param(self, key: str):
        default = self._default_value_for_key(key)
        if default is None:
            return
        if key == "quality_mode":
            self.param_widgets[key].setCurrentText(str(default))
        elif key in {"grid", "fps"}:
            self.param_widgets[key].setValue(int(default))
        elif key in {"V0", "Vsig", "n_strength", "c", "gamma", "scale"}:
            self.param_widgets[key].setValue(float(default))
        elif key in {"boundary_mode", "app_theme", "theme"}:
            self.param_widgets[key].setCurrentText(str(default))
        elif key == "overlay":
            self.cb_overlay.setCurrentText(str(default))
        elif key == "perf_overlay":
            self.chk_perf_overlay.setChecked(bool(default))
        elif key == "auto_apply_preset_defaults" and hasattr(self, "chk_apply_preset_defaults"):
            self.chk_apply_preset_defaults.setChecked(bool(default))
        self._remember_state()

    # ---------- domain ----------

    def _dt_sim(self) -> float:
        dt_frame = 1.0 / max(1, int(self.P.fps))
        spf, dt = compute_stable_substeps(
            dt_frame,
            self.dx,
            getattr(self, "c2", None),
            getattr(self, "V", None),
            max(1, int(self.P.spf)),
        )
        self.P.spf = int(spf)
        self.dt = float(dt)
        return self.dt

    def _setup_domain(self):
        N = int(self.P.grid)
        L = float(self.P.L)
        self.dx = L / N

        x = np.linspace(-L/2, L/2 - self.dx, N, dtype=np.float32)
        y = np.linspace(-L/2, L/2 - self.dx, N, dtype=np.float32)
        self.X, self.Y = np.meshgrid(x, y)

        self._rebuild_boundary_state()
        self._rebuild_medium()

        u, env = init_disk(self.X, self.Y, self.P.x0, self.P.y0, self.P.R0, self.P.k0, self.P.edge)
        ut = (-self.P.c * self.P.k0 * env * np.sin(self.P.k0*(self.X - self.P.x0))).astype(np.float32)
        dt = self._dt_sim()
        self.u = (u * self.absorb).astype(np.float32)
        self.u_prev = ((u - dt*ut) * self.absorb).astype(np.float32)
        self._apply_obstacle(self.u)
        self._apply_obstacle(self.u_prev)

    def _rebuild_boundary_state(self):
        self.absorb, self.edge_wall_mask, self.boundary_meta = build_boundary_state(int(self.P.grid), self.P)

    def _apply_app_theme(self):
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss_app_theme(self.P.app_theme_name))

    def _apply_theme_to_view(self):
        tmeta = theme_meta(self.P.theme_name)
        self.view.setBackground(tuple(tmeta["bg"]))

    def _dots_image(self, pts: np.ndarray) -> np.ndarray:
        return build_dots_image(pts, int(self.P.grid), float(self.P.L), float(self.P.preview_scale))

    def _rebuild_medium(self):
        self._dt_sim()
        self._rebuild_boundary_state()

        fn = PRESETS[self.preset_name]
        V, mask, n_map, pts = fn(self.X, self.Y, self.P, self.rng)

        self.V = V.astype(np.float32)
        merged_mask = np.zeros_like(self.V, dtype=bool)
        if mask is not None:
            merged_mask |= mask.astype(bool)
        if self.edge_wall_mask is not None:
            merged_mask |= self.edge_wall_mask.astype(bool)
        self.mask = merged_mask if np.any(merged_mask) else None

        if n_map is None:
            self.c2 = (float(self.P.c)**2) * np.ones_like(self.V, dtype=np.float32)
            self.n_map = None
        else:
            n = np.clip(n_map.astype(np.float32), 0.2, 6.0)
            self.n_map = n
            self.c2 = (float(self.P.c)**2) / (n*n)

        self.ov_V = None
        if np.max(self.V) > 1e-9:
            self.ov_V = np.clip(self.V / (np.percentile(self.V, 99) + 1e-6), 0, 1).astype(np.float32)

        self.ov_mask = None
        if self.mask is not None:
            self.ov_mask = self.mask.astype(np.float32)

        self.ov_n = None
        if self.n_map is not None:
            n = self.n_map
            self.ov_n = np.clip((n - np.min(n)) / (np.max(n) - np.min(n) + 1e-6), 0, 1).astype(np.float32)

        self.pts = pts
        self.dots_rgb = self._dots_image(pts) if (pts is not None and pts.shape[0] > 0) else None
        if hasattr(self, 'view'):
            self._apply_theme_to_view()
        if hasattr(self, 'lbl_status'):
            self._refresh_status_texts()

    def _apply_obstacle(self, arr: np.ndarray):
        if self.mask is not None:
            arr[self.mask] = 0.0

    def _apply_preset_wave_defaults(self, preset_name: Optional[str] = None):
        name = str(preset_name or self.preset_name)
        defaults = PRESET_WAVE_DEFAULTS.get(name, {})
        for key, value in defaults.items():
            setattr(self.P, key, float(value))

    def _apply_preset_model_defaults(self, preset_name: Optional[str] = None):
        name = str(preset_name or self.preset_name)
        defaults = PRESET_MODEL_DEFAULTS.get(name, {})
        for key, value in defaults.items():
            setattr(self.P, key, value)

    def _sync_controls_from_params(self, keys: Optional[list[str]] = None):
        if not hasattr(self, "param_widgets"):
            return
        sync_keys = keys or list(self.param_widgets.keys())
        for key in sync_keys:
            if key == "overlay" and hasattr(self, "cb_overlay"):
                widget = self.cb_overlay
            else:
                widget = self.param_widgets.get(key)
            if widget is None:
                continue
            old = widget.blockSignals(True)
            try:
                if key == "quality_mode" and hasattr(self, "cb_quality"):
                    self.cb_quality.setCurrentText(str(getattr(self.P, "quality_mode", quality_label_for_grid(int(self.P.grid)))))
                elif key == "grid" and hasattr(self, "sb_grid"):
                    self.sb_grid.setValue(int(self.P.grid))
                elif key == "fps" and hasattr(self, "sb_fps"):
                    self.sb_fps.setValue(int(self.P.fps))
                elif key == "V0" and hasattr(self, "ds_V0"):
                    self.ds_V0.setValue(float(self.P.V0))
                elif key == "Vsig" and hasattr(self, "ds_Vsig"):
                    self.ds_Vsig.setValue(float(self.P.Vsig))
                elif key == "n_strength" and hasattr(self, "ds_nstr"):
                    self.ds_nstr.setValue(float(self.P.n_strength))
                elif key == "c" and hasattr(self, "ds_c"):
                    self.ds_c.setValue(float(self.P.c))
                elif key == "gamma" and hasattr(self, "ds_gamma"):
                    self.ds_gamma.setValue(float(self.P.gamma))
                elif key == "boundary_mode" and hasattr(self, "cb_boundary_mode"):
                    self.cb_boundary_mode.setCurrentText(str(self.P.boundary_mode))
                elif key == "app_theme" and hasattr(self, "cb_app_theme"):
                    self.cb_app_theme.setCurrentText(str(self.P.app_theme_name))
                elif key == "theme" and hasattr(self, "cb_theme"):
                    self.cb_theme.setCurrentText(str(self.P.theme_name))
                elif key == "scale" and hasattr(self, "ds_scale"):
                    self.ds_scale.setValue(float(self.P.preview_scale))
                elif key == "overlay" and hasattr(self, "cb_overlay"):
                    self.cb_overlay.setCurrentText(overlay_display(str(self.P.overlay_mode)))
                elif key == "perf_overlay" and hasattr(self, "chk_perf_overlay"):
                    self.chk_perf_overlay.setChecked(bool(self.P.show_perf_overlay))
                elif key == "auto_apply_preset_defaults" and hasattr(self, "chk_apply_preset_defaults"):
                    self.chk_apply_preset_defaults.setChecked(bool(getattr(self.P, "auto_apply_preset_defaults", True)))
            finally:
                widget.blockSignals(old)

    def _preset_wave_summary(self, preset_name: Optional[str] = None) -> str:
        name = str(preset_name or self.preset_name)
        d = PRESET_WAVE_DEFAULTS.get(name, {})
        if not d:
            return "condición inicial libre"
        return (
            f"x0 = {float(d.get('x0', self.P.x0)):.2f}, "
            f"y0 = {float(d.get('y0', self.P.y0)):.2f}, "
            f"R0 = {float(d.get('R0', self.P.R0)):.2f}, "
            f"k0 = {float(d.get('k0', self.P.k0)):.1f}"
        )

    def _preset_model_summary(self, preset_name: Optional[str] = None) -> str:
        name = str(preset_name or self.preset_name)
        d = PRESET_MODEL_DEFAULTS.get(name, {})
        parts = []
        if 'V0' in d:
            parts.append(f"V0 = {float(d['V0']):.0f}")
        if 'Vsig' in d:
            parts.append(f"σ = {float(d['Vsig']):.3f}")
        if 'n_strength' in d:
            parts.append(f"n_strength = {float(d['n_strength']):.2f}")
        if 'c' in d:
            parts.append(f"c = {float(d['c']):.2f}")
        if 'gamma' in d:
            parts.append(f"γ = {float(d['gamma']):.3f}")
        if 'boundary_mode' in d:
            parts.append(str(d['boundary_mode']))
        return " · ".join(parts) if parts else "usa los controles actuales"

    # ---------- pedagogy / UI ----------

    def _build_preset_group(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("1. Elige el fenómeno físico")
        lay = QtWidgets.QVBoxLayout(g)
        lay.setSpacing(6)

        lbl = QtWidgets.QLabel("Preset del medio")
        lbl.setObjectName("titleMini")
        self.cb_preset = QtWidgets.QComboBox()
        self.cb_preset.addItems(list(PRESETS.keys()))
        self.cb_preset.setCurrentText(self.preset_name)
        self.cb_preset.currentIndexChanged.connect(self._on_preset)
        self.cb_preset.setToolTip("Selecciona el tipo de medio u obstáculo que guiará la propagación de la onda.")

        self.preset_help = make_info_browser()
        self.preset_help.setMinimumHeight(150)

        lay.addWidget(lbl)
        lay.addWidget(self.cb_preset)
        lay.addWidget(self.preset_help)
        return g

    def _param_card(self, key: str, control_widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        title, desc = PARAM_TEXT[key]
        card = QtWidgets.QFrame()
        card.setObjectName("paramCard")
        lay = QtWidgets.QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setObjectName("titleMini")
        btn_reset = QtWidgets.QPushButton("Restablecer")
        btn_reset.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_reset.setMinimumWidth(96)
        btn_reset.setMaximumWidth(120)
        btn_reset.setToolTip("Vuelve solo este parámetro a su valor base del programa.")
        btn_reset.clicked.connect(lambda _=False, k=key: self._reset_single_param(k))
        top.addWidget(lbl_t, 1)
        top.addWidget(btn_reset, 0)

        lbl_d = QtWidgets.QLabel(desc)
        lbl_d.setObjectName("caption")
        lbl_d.setWordWrap(True)

        card.setToolTip(desc)
        control_widget.setToolTip(desc)

        lay.addLayout(top)
        lay.addWidget(lbl_d)
        lay.addWidget(control_widget)
        self.param_cards[key] = card
        return card

    def _build_tech_group(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("2. Ajustes técnicos y visualización")
        lay = QtWidgets.QVBoxLayout(g)
        lay.setSpacing(6)

        self.cb_quality = QtWidgets.QComboBox()
        self.cb_quality.addItems(["Baja", "Media", "Alta", "Personalizada"])
        self.cb_quality.setCurrentText(str(getattr(self.P, "quality_mode", quality_label_for_grid(int(self.P.grid)))))
        self.cb_quality.currentIndexChanged.connect(self._on_quality_changed)
        self.param_widgets["quality_mode"] = self.cb_quality
        lay.addWidget(self._param_card("quality_mode", self.cb_quality))

        self.sb_grid = FriendlySpinBox()
        self.sb_grid.setRange(128, 1024)
        self.sb_grid.setSingleStep(32)
        self.sb_grid.setValue(int(self.P.grid))
        self.sb_grid.valueChanged.connect(self._on_domain)
        self.param_widgets["grid"] = self.sb_grid
        lay.addWidget(self._param_card("grid", wrap_with_step_buttons(self.sb_grid)))

        self.sb_fps = FriendlySpinBox()
        self.sb_fps.setRange(10, 120)
        self.sb_fps.setSingleStep(5)
        self.sb_fps.setValue(int(self.P.fps))
        self.sb_fps.valueChanged.connect(self._on_domain)
        self.param_widgets["fps"] = self.sb_fps
        lay.addWidget(self._param_card("fps", wrap_with_step_buttons(self.sb_fps)))

        return g

    def _build_model_group(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("3. Parámetros físicos del medio")
        lay = QtWidgets.QVBoxLayout(g)
        lay.setSpacing(6)

        self.cb_boundary_mode = QtWidgets.QComboBox()
        self.cb_boundary_mode.addItems(list(BOUNDARY_MODES.keys()))
        self.cb_boundary_mode.setCurrentText(self.P.boundary_mode)
        self.cb_boundary_mode.currentIndexChanged.connect(self._on_boundary_mode)
        self.param_widgets["boundary_mode"] = self.cb_boundary_mode
        lay.addWidget(self._param_card("boundary_mode", self.cb_boundary_mode))

        self.chk_apply_preset_defaults = QtWidgets.QCheckBox("Aplicar ajustes sugeridos del preset")
        self.chk_apply_preset_defaults.setChecked(bool(getattr(self.P, "auto_apply_preset_defaults", True)))
        self.chk_apply_preset_defaults.toggled.connect(self._on_auto_apply_preset_defaults_changed)
        self.param_widgets["auto_apply_preset_defaults"] = self.chk_apply_preset_defaults
        lay.addWidget(self._param_card("auto_apply_preset_defaults", self.chk_apply_preset_defaults))

        self.ds_V0 = FriendlyDoubleSpinBox()
        self.ds_V0.setRange(-800.0, 800.0)
        self.ds_V0.setSingleStep(10.0)
        self.ds_V0.setDecimals(1)
        self.ds_V0.setValue(float(self.P.V0))
        self.ds_V0.valueChanged.connect(self._on_medium_params)
        self.param_widgets["V0"] = self.ds_V0
        lay.addWidget(self._param_card("V0", wrap_with_step_buttons(self.ds_V0)))

        self.ds_Vsig = FriendlyDoubleSpinBox()
        self.ds_Vsig.setRange(0.01, 0.50)
        self.ds_Vsig.setSingleStep(0.01)
        self.ds_Vsig.setDecimals(3)
        self.ds_Vsig.setValue(float(self.P.Vsig))
        self.ds_Vsig.valueChanged.connect(self._on_medium_params)
        self.param_widgets["Vsig"] = self.ds_Vsig
        lay.addWidget(self._param_card("Vsig", wrap_with_step_buttons(self.ds_Vsig)))

        self.ds_nstr = FriendlyDoubleSpinBox()
        self.ds_nstr.setRange(0.0, 1.5)
        self.ds_nstr.setSingleStep(0.05)
        self.ds_nstr.setDecimals(3)
        self.ds_nstr.setValue(float(self.P.n_strength))
        self.ds_nstr.valueChanged.connect(self._on_medium_params)
        self.param_widgets["n_strength"] = self.ds_nstr
        lay.addWidget(self._param_card("n_strength", wrap_with_step_buttons(self.ds_nstr)))

        self.ds_c = FriendlyDoubleSpinBox()
        self.ds_c.setRange(0.05, 1.20)
        self.ds_c.setSingleStep(0.02)
        self.ds_c.setDecimals(3)
        self.ds_c.setValue(float(self.P.c))
        self.ds_c.valueChanged.connect(self._on_wave_params)
        self.param_widgets["c"] = self.ds_c
        lay.addWidget(self._param_card("c", wrap_with_step_buttons(self.ds_c)))

        self.ds_gamma = FriendlyDoubleSpinBox()
        self.ds_gamma.setRange(0.0, 0.08)
        self.ds_gamma.setSingleStep(0.002)
        self.ds_gamma.setDecimals(4)
        self.ds_gamma.setValue(float(self.P.gamma))
        self.ds_gamma.valueChanged.connect(self._on_wave_params)
        self.param_widgets["gamma"] = self.ds_gamma
        lay.addWidget(self._param_card("gamma", wrap_with_step_buttons(self.ds_gamma)))

        return g

    def _build_visual_group(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("3. Personaliza la imagen y las ayudas visuales")
        lay = QtWidgets.QVBoxLayout(g)
        lay.setSpacing(6)

        self.cb_overlay = QtWidgets.QComboBox()
        self.cb_overlay.addItems(list(OVERLAY_OPTIONS.keys()))
        self.cb_overlay.setCurrentText(overlay_display(self.P.overlay_mode))
        self.cb_overlay.currentIndexChanged.connect(self._on_style)
        self.cb_overlay.setToolTip(
            "Elige qué mapa físico quieres dibujar encima de la onda: el potencial V(x,y), las paredes sólidas del medio o el índice de refracción n(x,y)."
        )
        lay.addWidget(self._param_card("overlay", self.cb_overlay))

        self.cb_app_theme = QtWidgets.QComboBox()
        self.cb_app_theme.addItems(list(APP_THEMES.keys()))
        self.cb_app_theme.setCurrentText(self.P.app_theme_name)
        self.cb_app_theme.currentIndexChanged.connect(self._on_app_theme_changed)
        self.param_widgets["app_theme"] = self.cb_app_theme
        lay.addWidget(self._param_card("app_theme", self.cb_app_theme))

        self.cb_theme = QtWidgets.QComboBox()
        self.cb_theme.addItems(list(THEMES.keys()))
        self.cb_theme.setCurrentText(self.P.theme_name)
        self.cb_theme.currentIndexChanged.connect(self._on_style)
        self.param_widgets["theme"] = self.cb_theme
        lay.addWidget(self._param_card("theme", self.cb_theme))

        chk_card = QtWidgets.QFrame()
        chk_card.setObjectName("paramCard")
        chk_lay = QtWidgets.QVBoxLayout(chk_card)
        chk_lay.setContentsMargins(10, 10, 10, 10)
        chk_lay.setSpacing(6)

        self.chk_dots = QtWidgets.QCheckBox("Mostrar centros de dispersores")
        self.chk_dots.setChecked(bool(self.P.show_dots))
        self.chk_dots.toggled.connect(self._on_style)

        self.chk_border = QtWidgets.QCheckBox("Mostrar marco visual de la imagen")
        self.chk_border.setChecked(bool(self.P.border))
        self.chk_border.toggled.connect(self._on_style)

        self.chk_perf_overlay = QtWidgets.QCheckBox("Mostrar monitor de rendimiento en pantalla")
        self.chk_perf_overlay.setChecked(bool(self.P.show_perf_overlay))
        self.chk_perf_overlay.toggled.connect(self._on_style)
        self.param_widgets["perf_overlay"] = self.chk_perf_overlay

        txt = QtWidgets.QLabel("Estas opciones no cambian la física del modelo: cambian cómo se ve y qué ayudas visuales aparecen para leer mejor la escena.")
        txt.setObjectName("caption")
        txt.setWordWrap(True)

        chk_lay.addWidget(self.chk_dots)
        chk_lay.addWidget(self.chk_border)
        chk_lay.addWidget(self.chk_perf_overlay)
        chk_lay.addWidget(txt)
        lay.addWidget(chk_card)

        self.ds_scale = FriendlyDoubleSpinBox()
        self.ds_scale.setRange(0.50, 1.00)
        self.ds_scale.setSingleStep(0.05)
        self.ds_scale.setDecimals(2)
        self.ds_scale.setValue(float(self.P.preview_scale))
        self.ds_scale.valueChanged.connect(self._on_style)
        self.param_widgets["scale"] = self.ds_scale
        lay.addWidget(self._param_card("scale", wrap_with_step_buttons(self.ds_scale)))
        return g

    def _build_actions_group(self) -> QtWidgets.QWidget:
        frame = QtWidgets.QFrame()
        frame.setObjectName("panelCard")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(10)
        title = QtWidgets.QLabel("Acciones rápidas")
        title.setObjectName("titleMini")
        subtitle = QtWidgets.QLabel("Siempre visibles para pausar, reiniciar o lanzar otra condición inicial sin abrir pestañas.")
        subtitle.setObjectName("caption")
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        self.chk_reset_on_preset = QtWidgets.QCheckBox("Reiniciar onda al cambiar de preset")
        self.chk_reset_on_preset.setChecked(bool(self.P.auto_reset_on_preset))
        self.chk_reset_on_preset.toggled.connect(self._on_auto_reset_changed)

        top_row.addWidget(title, 0)
        top_row.addWidget(subtitle, 1)
        top_row.addWidget(self.chk_reset_on_preset, 0)

        row = QtWidgets.QGridLayout()
        row.setHorizontalSpacing(8)
        row.setVerticalSpacing(8)
        self.btn_run = QtWidgets.QPushButton("Pausar")
        self.btn_run.clicked.connect(self._toggle_run)
        self.btn_reset = QtWidgets.QPushButton("Reiniciar onda")
        self.btn_reset.clicked.connect(self._reset_wave)
        self.btn_rand = QtWidgets.QPushButton("Randomizar inicio")
        self.btn_rand.clicked.connect(self._randomize)
        self.btn_defaults = QtWidgets.QPushButton("Valores sugeridos")
        self.btn_defaults.clicked.connect(self._restore_defaults)

        buttons = (self.btn_run, self.btn_reset, self.btn_rand, self.btn_defaults)
        for i, btn in enumerate(buttons):
            btn.setMinimumWidth(132)
            row.addWidget(btn, i // 2, i % 2)
        row.setColumnStretch(0, 1)
        row.setColumnStretch(1, 1)

        lay.addLayout(top_row)
        lay.addLayout(row)
        return frame

    def _build_theory_group(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("4. Documentación, física y visión abierta")
        lay = QtWidgets.QVBoxLayout(g)
        lay.setSpacing(6)

        theory_html = (
            "<b>Qué resuelve este laboratorio</b><br>"
            "<div style='margin:8px 0 12px 0; padding:8px 12px; border:1px solid #445a84; border-radius:10px; background:#0d1320; font-family:&quot;Cambria Math&quot;,&quot;STIX Two Math&quot;,&quot;Times New Roman&quot;,serif; font-size:14pt; text-align:center;'>"
            "<span style='font-style:italic;'>u</span><sub>tt</sub> + γ <span style='font-style:italic;'>u</span><sub>t</sub> = ∇·(<span style='font-style:italic;'>c</span>(x,y)<sup>2</sup> ∇<span style='font-style:italic;'>u</span>) − <span style='font-style:italic;'>V</span>(x,y)<span style='font-style:italic;'>u</span>"
            "</div>"
            "<b>Cómo leerlo sin humo</b>"
            "<ul>"
            "<li><b>u(x,y,t)</b> es la amplitud de una onda escalar 2D.</li>"
            "<li><b>c(x,y)</b> cambia la velocidad local y por eso puede torcer el frente: ahí aparece refracción.</li>"
            "<li><b>V(x,y)</b> actúa como paisaje de dispersión: no es una teoría cuántica completa, sino un motor pedagógico para ver cómo un potencial espacial deforma la propagación.</li>"
            "<li><b>Máscara / obstáculos</b> impone regiones donde la onda no entra, generando reflexión y difracción.</li>"
            "<li><b>gamma</b> amortigua y ayuda a controlar ecos o acumulación numérica.</li>"
            "</ul>"
            "<b>Qué es y qué no es</b><br>"
            "Este proyecto no pretende vender una simulación exacta de todos los sistemas físicos. Es un punto de partida visual y honesto para cursos iniciales, útil para discutir reflexión, difracción, dispersión, refracción y el rol de la geometría del medio.<br><br>"
            "<b>Visión abierta del proyecto</b><br>"
            "Sí: este laboratorio fue construido con ayuda de IA y está pensado como código abierto. La idea no es ocultarlo, sino usarlo como puntapié inicial para que otras personas modifiquen el motor, mejoren la física, pulan la interfaz y exploren cómo la IA puede acelerar proyectos pedagógicos serios.<br><br>"
            "<b>Sugerencia de uso</b><br>"
            "Fija un preset, mira el mapa superpuesto, cambia un parámetro por vez y compara. Esa metodología enseña más que mover todo al mismo tiempo."
        )
        self.theory_box = make_info_browser(theory_html)
        self.theory_box.setMinimumHeight(220)
        lay.addWidget(self.theory_box)
        return g

    def _refresh_pedagogical_panel(self):
        meta = PRESET_META[self.preset_name]
        kind = str(meta["kind"])
        overlay = str(meta["overlay"])
        channel = str(meta["channel"])
        postscript = str(meta.get("postscript", "")).strip()
        help_html = (
            f"<b>{self.preset_name}</b><br><br>"
            f"<b>Resumen:</b> {meta['idea']}<br><br>"
            f"<b>Mira esto:</b> {meta['observe']}<br><br>"
            f"<b>Prueba esto:</b> {meta['focus']}<br><br>"
            f"<b>Onda sugerida:</b> {self._preset_wave_summary(self.preset_name)}.<br><br>"
            f"<b>Ajustes sugeridos:</b> {self._preset_model_summary(self.preset_name)}.<br><br>"
            f"<b>Canal dominante:</b> {channel}."
            + (f"<br><br><b>P. D.:</b> {postscript}" if postscript else "")
        )
        self.preset_help.setHtml(help_html)
        self.lbl_scene_title.setText(self.preset_name)
        self.lbl_scene_caption.setText(str(meta["idea"]))
        self.lbl_medium_badge.setText(channel)

        self._set_param_enabled("V0", True)
        self._set_param_enabled("Vsig", True)
        self._set_param_enabled("n_strength", True)

        idx = self.cb_overlay.findText(overlay_display(str(overlay)))
        if idx >= 0:
            self.cb_overlay.blockSignals(True)
            self.cb_overlay.setCurrentIndex(idx)
            self.cb_overlay.blockSignals(False)
            self.P.overlay_mode = overlay

        self._refresh_status_texts()

    def _set_param_enabled(self, key: str, enabled: bool):
        card = self.param_cards.get(key)
        widget = self.param_widgets.get(key)
        if card is not None:
            card.setEnabled(enabled)
        if widget is not None:
            widget.setEnabled(enabled)

    def _refresh_status_texts(self):
        if not hasattr(self, 'lbl_status'):
            return
        meta = PRESET_META[self.preset_name]
        kind = str(meta["kind"])
        boundary_summary = str(self.boundary_meta.get("summary", ""))
        boundary_label = str(self.boundary_meta.get("label", self.P.boundary_mode))
        channel = str(meta["channel"])

        if kind == "potential":
            dynamics = "domina V(x,y): dispersión"
        elif kind == "obstacle":
            dynamics = "dominan paredes: reflexión y difracción"
        else:
            dynamics = "domina n(x,y): refracción"

        overlay_txt = overlay_short_label(self.P.overlay_mode)

        ram_ratio = self.perf_snapshot.get("ram_ratio") if isinstance(getattr(self, "perf_snapshot", None), dict) else None
        ram_txt = f"RAM sistema {100*float(ram_ratio):.0f}%" if isinstance(ram_ratio, (int, float)) else "RAM sistema N/D"

        self.metric_preset.setText(f"{self.preset_name} · {channel}")
        self.metric_overlay.setText(overlay_txt)
        self.metric_boundary.setText(f"{boundary_label}\n{boundary_summary}")
        self.metric_dynamics.setText(dynamics)
        self.metric_params.setText(
            f"c = {self.P.c:.3f} · γ = {self.P.gamma:.4f}\n"
            f"grid = {self.P.grid} · dt ≈ {getattr(self, 'dt', 0.0):.5f}"
        )
        self.metric_compute.setText(
            f"FPS ≈ {self._fps_value:.0f} · spf = {self.P.spf}\n{ram_txt}"
        )

        self.lbl_hint.setText(
            "Lectura recomendada: fija el fenómeno, mira el overlay y cambia un solo parámetro por vez para identificar qué produce reflexión, difracción, dispersión o refracción."
        )

    def _restore_defaults(self):
        self.P = SimParams()
        self.default_P = SimParams()

        self.cb_preset.setCurrentIndex(0)
        self._apply_preset_model_defaults(self.preset_name)
        self._apply_preset_wave_defaults(self.preset_name)
        self.P.quality_mode = quality_label_for_grid(int(self.P.grid))
        self._sync_controls_from_params(["quality_mode", "grid", "fps", "V0", "Vsig", "n_strength", "c", "gamma", "boundary_mode", "app_theme", "theme", "scale", "overlay", "perf_overlay", "auto_apply_preset_defaults"])
        self.chk_dots.setChecked(bool(self.P.show_dots))
        self.chk_border.setChecked(bool(self.P.border))
        self.chk_perf_overlay.setChecked(bool(self.P.show_perf_overlay))
        self.chk_reset_on_preset.setChecked(bool(self.P.auto_reset_on_preset))
        self._setup_domain()
        self._refresh_pedagogical_panel()
        self._remember_state()

    def _update_quality_combo_from_grid(self):
        if not hasattr(self, "cb_quality"):
            return
        if str(getattr(self.P, "quality_mode", "")) in QUALITY_PRESETS and QUALITY_PRESETS[self.P.quality_mode] == int(self.P.grid):
            target = self.P.quality_mode
        else:
            target = quality_label_for_grid(int(self.P.grid))
            if target not in QUALITY_PRESETS:
                target = "Personalizada"
            self.P.quality_mode = target
        old = self.cb_quality.blockSignals(True)
        self.cb_quality.setCurrentText(target)
        self.cb_quality.blockSignals(old)

    def _on_quality_changed(self):
        choice = str(self.cb_quality.currentText())
        self.P.quality_mode = choice
        if choice in QUALITY_PRESETS:
            target_grid = int(QUALITY_PRESETS[choice])
            if int(self.P.grid) != target_grid:
                self.P.grid = target_grid
                old = self.sb_grid.blockSignals(True)
                self.sb_grid.setValue(target_grid)
                self.sb_grid.blockSignals(old)
                self._setup_domain()
                self._refresh_status_texts()
        self._remember_state()

    # callbacks
    def _on_auto_reset_changed(self):
        self.P.auto_reset_on_preset = bool(self.chk_reset_on_preset.isChecked())
        self._remember_state()

    def _on_auto_apply_preset_defaults_changed(self):
        self.P.auto_apply_preset_defaults = bool(self.chk_apply_preset_defaults.isChecked())
        self._remember_state()

    def _on_preset(self):
        self.preset_name = str(self.cb_preset.currentText())
        applied_defaults = bool(getattr(self.P, "auto_apply_preset_defaults", True))
        if applied_defaults:
            self._apply_preset_model_defaults(self.preset_name)
            self._apply_preset_wave_defaults(self.preset_name)
        self._sync_controls_from_params(["quality_mode", "V0", "Vsig", "n_strength", "c", "gamma", "boundary_mode", "auto_apply_preset_defaults"])
        self._rebuild_medium()
        self.u *= self.absorb
        self.u_prev *= self.absorb
        self._apply_obstacle(self.u)
        self._apply_obstacle(self.u_prev)
        if bool(self.P.auto_reset_on_preset):
            self._reset_wave()
            if applied_defaults:
                self.lbl_hint.setText(
                    "Se cambió el preset y la onda se reinició con la condición inicial y los parámetros sugeridos para ese medio."
                )
            else:
                self.lbl_hint.setText(
                    "Se cambió el preset y la onda se reinició, pero conservando tus parámetros actuales porque la aplicación automática del preset está desactivada."
                )
        else:
            if applied_defaults:
                self.lbl_hint.setText(
                    "Se cambió el preset y quedaron cargados sus parámetros sugeridos. La onda actual no se reinició porque esta opción está desactivada."
                )
            else:
                self.lbl_hint.setText(
                    "Se cambió el preset, pero se conservaron tus parámetros actuales y la onda siguió corriendo sin reinicio."
                )
        self._refresh_pedagogical_panel()
        self._remember_state()

    def _on_domain(self):
        self.P.grid = int(self.sb_grid.value())
        self.P.fps = int(self.sb_fps.value())
        self.P.quality_mode = quality_label_for_grid(int(self.P.grid))
        if hasattr(self, "cb_quality") and self.cb_quality.currentText() in QUALITY_PRESETS and QUALITY_PRESETS[self.cb_quality.currentText()] != int(self.P.grid):
            self.P.quality_mode = "Personalizada"
        self._update_quality_combo_from_grid()
        self._setup_domain()
        self._refresh_status_texts()
        self._remember_state()

    def _on_medium_params(self):
        self.P.V0 = float(self.ds_V0.value())
        self.P.Vsig = float(self.ds_Vsig.value())
        self.P.n_strength = float(self.ds_nstr.value())
        self._debounce.start(60)
        self._refresh_status_texts()
        self._remember_state()

    def _on_wave_params(self):
        self.P.c = float(self.ds_c.value())
        self.P.gamma = float(self.ds_gamma.value())
        self._dt_sim()
        self._debounce.start(60)
        self._refresh_status_texts()
        self._remember_state()

    def _on_boundary_mode(self):
        self.P.boundary_mode = str(self.cb_boundary_mode.currentText())
        self._setup_domain()
        self._refresh_status_texts()
        self._remember_state()

    def _on_app_theme_changed(self):
        old_app = getattr(self.P, "app_theme_name", "Noche")
        old_default = str(app_theme_meta(old_app).get("sim_default", "Original"))
        current_sim = str(self.cb_theme.currentText())

        self.P.app_theme_name = str(self.cb_app_theme.currentText())
        self._apply_app_theme()

        if current_sim == old_default:
            new_default = str(app_theme_meta(self.P.app_theme_name).get("sim_default", "Original"))
            idx = self.cb_theme.findText(new_default)
            if idx >= 0:
                self.cb_theme.blockSignals(True)
                self.cb_theme.setCurrentIndex(idx)
                self.cb_theme.blockSignals(False)
                self.P.theme_name = new_default

        self._apply_theme_to_view()
        self._refresh_status_texts()
        self._refresh_overlay_labels()
        self._remember_state()

    def _on_style(self):
        self.P.overlay_mode = overlay_mode_from_text(str(self.cb_overlay.currentText()))
        self.P.theme_name = str(self.cb_theme.currentText())
        self.P.show_dots = bool(self.chk_dots.isChecked())
        self.P.border = bool(self.chk_border.isChecked())
        self.P.show_perf_overlay = bool(self.chk_perf_overlay.isChecked())
        self.P.preview_scale = float(self.ds_scale.value())
        self.dots_rgb = self._dots_image(self.pts) if (self.pts is not None and self.pts.shape[0] > 0) else None
        self._apply_theme_to_view()
        self._refresh_status_texts()
        self._refresh_overlay_labels()
        self._remember_state()

    def _perf_summary_lines(self) -> str:
        snap = dict(self.perf_snapshot) if isinstance(self.perf_snapshot, dict) else {}
        ram_proc = _fmt_gib_from_bytes(snap.get("ram_proc"))
        ram_used = _fmt_gib_from_bytes(snap.get("ram_used"))
        ram_total = _fmt_gib_from_bytes(snap.get("ram_total"))
        ram_ratio = snap.get("ram_ratio")
        if isinstance(ram_ratio, (int, float)):
            ram_line = f"RAM app: {ram_proc} | RAM sistema: {ram_used} / {ram_total} ({100*float(ram_ratio):.0f}%)"
        else:
            ram_line = f"RAM app: {ram_proc} | RAM sistema: N/D"

        gpu_available = bool(snap.get("gpu_available", False))
        vram_proc = _fmt_gib_from_bytes(snap.get("vram_proc"))
        if gpu_available:
            vram_used = _fmt_gib_from_bytes(snap.get("vram_used"))
            vram_total = _fmt_gib_from_bytes(snap.get("vram_total"))
            vram_ratio = snap.get("vram_ratio")
            gpu_name = str(snap.get("gpu_name") or "GPU")
            if isinstance(vram_ratio, (int, float)):
                vram_line = f"VRAM app: {vram_proc} | VRAM total: {vram_used} / {vram_total} ({100*float(vram_ratio):.0f}%)"
            else:
                vram_line = f"VRAM app: {vram_proc} | VRAM total: {vram_used} / {vram_total}"
            vram_line += f"\nGPU: {gpu_name}"
        else:
            vram_line = "VRAM: no detectada por nvidia-smi"
        return ram_line + "\n" + vram_line

    def _refresh_overlay_labels(self):
        show_hud = bool(self.P.show_perf_overlay)
        alert_text, has_alert = build_perf_alert_text(self.perf_snapshot)
        self.hud.setVisible(show_hud)
        if show_hud:
            overlay_name = overlay_short_label(self.P.overlay_mode)
            self.hud.setText(
                f"FPS: {self._fps_value:.1f}\n"
                f"grid = {self.P.grid} | spf = {self.P.spf}\n"
                f"preset = {self.preset_name} | {overlay_name}\n"
                f"{self.boundary_meta.get('label', self.P.boundary_mode)}\n"
                f"{self._perf_summary_lines()}"
            )
        if has_alert:
            self.alert_overlay.setText(alert_text)
            self.alert_overlay.show()
        else:
            self.alert_overlay.hide()

    def _update_performance_snapshot(self):
        self.perf_snapshot = read_system_snapshot()
        self._refresh_overlay_labels()

    def _toggle_run(self):
        self._running = not self._running
        self.btn_run.setText("Pausar" if self._running else "Reanudar")

    def _reset_wave(self):
        u, env = init_disk(self.X, self.Y, self.P.x0, self.P.y0, self.P.R0, self.P.k0, self.P.edge)
        ut = (-self.P.c * self.P.k0 * env * np.sin(self.P.k0*(self.X - self.P.x0))).astype(np.float32)
        dt = self._dt_sim()
        self.u = (u * self.absorb).astype(np.float32)
        self.u_prev = ((u - dt*ut) * self.absorb).astype(np.float32)
        self._apply_obstacle(self.u)
        self._apply_obstacle(self.u_prev)

    def _randomize(self):
        self.rng = np.random.default_rng(int(time.time()) & 0xFFFFFFFF)
        x0, y0 = sample_valid_center(
            self.X,
            self.Y,
            self.mask,
            self.edge_wall_mask,
            self.boundary_meta,
            self.P,
            self.rng,
            self.dx,
        )
        self.P.x0 = float(x0)
        self.P.y0 = float(y0)
        self._reset_wave()
        self.lbl_hint.setText(
            f"Nueva posición inicial: x0 = {self.P.x0:.2f}, y0 = {self.P.y0:.2f}. La onda se ubicó dentro de una zona libre del dominio."
        )
        self._remember_state()

    # ---------- simulation tick ----------

    def _step_sub(self):
        dt = self.dt
        div = div_c2_grad(self.u, self.c2, self.dx)
        u_next = (2*self.u - self.u_prev
                  + (dt*dt) * (div - self.V*self.u)
                  - float(self.P.gamma)*dt*(self.u - self.u_prev)).astype(np.float32)

        u_next *= self.absorb
        np.nan_to_num(u_next, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(u_next, -1.0e6, 1.0e6, out=u_next)

        if self.mask is not None:
            u_next[self.mask] = 0.0

        self.u_prev, self.u = self.u, u_next

    def _tick(self):
        if self._running:
            self._dt_sim()
            for _ in range(int(max(1, self.P.spf))):
                self._step_sub()

        overlay = None
        if self.P.overlay_mode == "V":
            overlay = self.ov_V
        elif self.P.overlay_mode == "Mask":
            overlay = self.ov_mask
        elif self.P.overlay_mode == "n":
            overlay = self.ov_n

        N = int(self.P.grid)
        S = int(round(N * float(self.P.preview_scale)))
        S = max(128, min(N, S))

        if S != N:
            u_vis = cv2.resize(self.u, (S, S), interpolation=cv2.INTER_AREA)
            ov = cv2.resize(overlay, (S, S), interpolation=cv2.INTER_AREA) if (overlay is not None) else None
            dots = cv2.resize(self.dots_rgb, (S, S), interpolation=cv2.INTER_AREA) if (self.dots_rgb is not None) else None
        else:
            u_vis = self.u
            ov = overlay
            dots = self.dots_rgb

        rgb = render_frame(u_vis, dots, ov, self.P)

        if self.P.border:
            cv2.rectangle(rgb, (0, 0), (rgb.shape[1]-1, rgb.shape[0]-1), tuple(theme_meta(self.P.theme_name)["border"]), 2, lineType=cv2.LINE_AA)

        self.img_item.setImage(rgb, autoLevels=False)

        self._frames += 1
        now = time.time()
        if now - self._fps_last >= 0.5:
            fps = self._frames / (now - self._fps_last)
            self._fps_value = float(fps)
            self._fps_last = now
            self._frames = 0
            overlay_name = overlay_short_label(self.P.overlay_mode)
            self.hud.setText(
                f"FPS: {fps:.0f}\n"
                f"grid = {self.P.grid} | spf = {self.P.spf}\n"
                f"preset = {self.preset_name}\n"
                f"{overlay_name} | {self.boundary_meta.get('label', self.P.boundary_mode)}"
            )
            self._refresh_status_texts()


class InfoTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        header = QtWidgets.QFrame()
        header.setObjectName('panelCard')
        hl = QtWidgets.QVBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(4)
        title = QtWidgets.QLabel('Información')
        title.setObjectName('titleMini')
        subtitle = QtWidgets.QLabel('Modelo físico, bibliografía breve y nota abierta sobre cómo se construyó el proyecto.')
        subtitle.setObjectName('caption')
        subtitle.setWordWrap(True)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        lay.addWidget(header, 0)

        browser = make_info_browser(project_info_html())
        browser.setMinimumHeight(520)
        lay.addWidget(browser, 1)


class ExportTab(QtWidgets.QWidget):
    """Offline render to MP4 with single presets or sequential mixes."""
    def __init__(self, wave: WaveBoxWidget, parent=None):
        super().__init__(parent)
        self.wave = wave
        self.worker = None
        self._mix_rows = []

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer = QtWidgets.QWidget()
        main = QtWidgets.QVBoxLayout(outer)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(8)

        intro = QtWidgets.QGroupBox("Exportar MP4 (offline)")
        intro_lay = QtWidgets.QVBoxLayout(intro)
        intro_lay.setSpacing(8)

        msg = QtWidgets.QLabel(
            "La exportación recalcula la simulación cuadro por cuadro y usa ffmpeg para codificar el video. Puedes renderizar un preset único o encadenar una mezcla de hasta 5 tramos, cada uno con su propia duración."
        )
        msg.setObjectName("caption")
        msg.setWordWrap(True)
        intro_lay.addWidget(msg)

        file_card = QtWidgets.QFrame()
        file_card.setObjectName("paramCard")
        file_lay = QtWidgets.QVBoxLayout(file_card)
        file_lay.setContentsMargins(10, 10, 10, 10)
        file_lay.setSpacing(6)
        file_title = QtWidgets.QLabel("Archivo de salida")
        file_title.setObjectName("titleMini")
        file_desc = QtWidgets.QLabel("Elige el nombre y la ruta del MP4 que se generará.")
        file_desc.setObjectName("caption")
        file_desc.setWordWrap(True)
        file_row = QtWidgets.QHBoxLayout()
        self.ed_out = QtWidgets.QLineEdit("video.mp4")
        self.btn_browse = QtWidgets.QPushButton("Examinar…")
        self.btn_browse.clicked.connect(self._browse_out)
        file_row.addWidget(self.ed_out, 1)
        file_row.addWidget(self.btn_browse, 0)
        file_lay.addWidget(file_title)
        file_lay.addWidget(file_desc)
        file_lay.addLayout(file_row)
        intro_lay.addWidget(file_card)

        self.cb_mode = QtWidgets.QComboBox()
        self.cb_mode.addItems(["Preset único", "Mezcla secuencial (hasta 5 tramos)"])
        self.cb_mode.currentIndexChanged.connect(self._update_export_mode)
        intro_lay.addWidget(self._make_export_card(
            "Modo de exportación",
            self.cb_mode,
            "Preset único usa el medio escogido. La mezcla exporta varios presets seguidos, cada uno arrancando con sus ajustes sugeridos.",
        ))

        self.cb_resolution = QtWidgets.QComboBox()
        self.cb_resolution.addItems(list(RESOLUTION_PRESETS.keys()))
        self.cb_resolution.setCurrentText("Full HD · 1920×1080 · 16:9")
        self.cb_resolution.currentIndexChanged.connect(self._apply_resolution_preset)

        self.sb_W = FriendlySpinBox(); self.sb_W.setRange(256, 4096); self.sb_W.setSingleStep(64); self.sb_W.setValue(1920)
        self.sb_H = FriendlySpinBox(); self.sb_H.setRange(256, 4096); self.sb_H.setSingleStep(64); self.sb_H.setValue(1080)
        self.sb_W.valueChanged.connect(self._mark_resolution_custom)
        self.sb_H.valueChanged.connect(self._mark_resolution_custom)
        self.sb_fps = FriendlySpinBox(); self.sb_fps.setRange(10, 120); self.sb_fps.setSingleStep(5); self.sb_fps.setValue(30)
        self.ds_dur = FriendlyDoubleSpinBox(); self.ds_dur.setRange(1.0, 300.0); self.ds_dur.setSingleStep(1.0); self.ds_dur.setDecimals(1); self.ds_dur.setValue(12.0)
        self.sb_grid = FriendlySpinBox(); self.sb_grid.setRange(128, 1536); self.sb_grid.setSingleStep(64); self.sb_grid.setValue(512)
        self.sb_crf = FriendlySpinBox(); self.sb_crf.setRange(10, 30); self.sb_crf.setSingleStep(1); self.sb_crf.setValue(18)
        for w in [self.sb_W, self.sb_H, self.sb_fps, self.ds_dur, self.sb_grid, self.sb_crf]:
            if isinstance(w, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
                w.setKeyboardTracking(False)

        res_box = QtWidgets.QFrame()
        res_box.setObjectName("paramCard")
        res_lay = QtWidgets.QVBoxLayout(res_box)
        res_lay.setContentsMargins(10, 10, 10, 10)
        res_lay.setSpacing(6)
        res_title = QtWidgets.QLabel("Resolución final del video")
        res_title.setObjectName("titleMini")
        res_desc = QtWidgets.QLabel("Elige una plantilla estándar o ajusta manualmente ancho y alto en una sola fila para mantener clara la relación de aspecto.")
        res_desc.setObjectName("caption")
        res_desc.setWordWrap(True)
        res_lay.addWidget(res_title)
        res_lay.addWidget(res_desc)
        res_lay.addWidget(self.cb_resolution)

        dims_row = QtWidgets.QHBoxLayout()
        dims_row.setSpacing(8)
        w_wrap = wrap_with_step_buttons(self.sb_W, step_text_small=True)
        h_wrap = wrap_with_step_buttons(self.sb_H, step_text_small=True)
        sep = QtWidgets.QLabel("×")
        sep.setObjectName("titleMini")
        sep.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        w_col = QtWidgets.QVBoxLayout()
        w_col.setSpacing(4)
        w_lbl = QtWidgets.QLabel("Ancho (px)")
        w_lbl.setObjectName("caption")
        w_col.addWidget(w_lbl)
        w_col.addWidget(w_wrap)

        h_col = QtWidgets.QVBoxLayout()
        h_col.setSpacing(4)
        h_lbl = QtWidgets.QLabel("Alto (px)")
        h_lbl.setObjectName("caption")
        h_col.addWidget(h_lbl)
        h_col.addWidget(h_wrap)

        dims_row.addLayout(w_col, 1)
        dims_row.addWidget(sep, 0)
        dims_row.addLayout(h_col, 1)
        res_lay.addLayout(dims_row)

        common_grid = QtWidgets.QGridLayout()
        common_grid.setHorizontalSpacing(8)
        common_grid.setVerticalSpacing(8)
        common_grid.setColumnStretch(0, 1)
        common_grid.setColumnStretch(1, 1)
        common_grid.addWidget(res_box, 0, 0, 1, 2)
        common_cards = [
            self._make_export_card("FPS del video", wrap_with_step_buttons(self.sb_fps, step_text_small=True), "Cuadros por segundo del archivo final."),
            self._make_export_card("Grilla offline", wrap_with_step_buttons(self.sb_grid, step_text_small=True), "Más alta = más detalle, pero también más tiempo y memoria."),
            self._make_export_card("CRF H.264", wrap_with_step_buttons(self.sb_crf, step_text_small=True), "Menor CRF = mejor calidad y archivo más pesado."),
        ]
        for idx, card in enumerate(common_cards):
            common_grid.addWidget(card, 1 + idx // 2, idx % 2)
        intro_lay.addLayout(common_grid)

        self.cb_preset = QtWidgets.QComboBox()
        self.cb_preset.addItems(list(PRESETS.keys()))
        self.cb_preset.setCurrentText(self.wave.preset_name)
        self.single_box = QtWidgets.QGroupBox("Preset único")
        single_lay = QtWidgets.QGridLayout(self.single_box)
        single_lay.setHorizontalSpacing(8)
        single_lay.setVerticalSpacing(8)
        single_lay.addWidget(self._make_export_card("Preset a exportar", self.cb_preset, "Si coincide con el preset actual, usa tus ajustes vivos. Si no, parte desde los valores sugeridos del preset."), 0, 0)
        single_lay.addWidget(self._make_export_card("Duración del video (s)", wrap_with_step_buttons(self.ds_dur, step_text_small=True), "Tiempo total del tramo único."), 0, 1)
        intro_lay.addWidget(self.single_box)

        self.mix_box = QtWidgets.QGroupBox("Mezcla secuencial de presets")
        mix_lay = QtWidgets.QVBoxLayout(self.mix_box)
        mix_hint = QtWidgets.QLabel(
            "Activa hasta 5 tramos. En cada tramo puedes decidir si la onda se reinicia con la condición inicial sugerida del preset o si continúa desde el estado alcanzado en el tramo anterior. Si entras a un tramo sin reinicio y la onda ya se amortiguó, el resultado puede verse casi vacío: eso es parte de la dinámica heredada."
        )
        mix_hint.setObjectName("caption")
        mix_hint.setWordWrap(True)
        mix_lay.addWidget(mix_hint)
        for i in range(5):
            row_frame = QtWidgets.QFrame()
            row_frame.setObjectName("paramCard")
            row_lay = QtWidgets.QHBoxLayout(row_frame)
            row_lay.setContentsMargins(10, 8, 10, 8)
            row_lay.setSpacing(8)
            chk = QtWidgets.QCheckBox(f"Tramo {i+1}")
            chk.setChecked(i == 0)
            cb = QtWidgets.QComboBox(); cb.addItems(list(PRESETS.keys()))
            cb.setCurrentIndex(min(i, cb.count()-1))
            dur = FriendlyDoubleSpinBox(); dur.setRange(1.0, 120.0); dur.setSingleStep(1.0); dur.setDecimals(1); dur.setValue(6.0 if i else 8.0)
            dur.setKeyboardTracking(False)
            restart_chk = QtWidgets.QCheckBox("reiniciar onda")
            restart_chk.setChecked(True)
            if i == 0:
                restart_chk.setToolTip("En el primer tramo se parte desde el estado inicial sugerido del preset.")
            else:
                restart_chk.setToolTip("Si se desactiva, este tramo hereda la onda que dejó el tramo anterior.")
            row_lay.addWidget(chk, 0)
            row_lay.addWidget(cb, 1)
            row_lay.addWidget(QtWidgets.QLabel("duración (s)"), 0)
            row_lay.addWidget(wrap_with_step_buttons(dur, step_text_small=True), 0)
            row_lay.addWidget(restart_chk, 0)
            mix_lay.addWidget(row_frame)
            self._mix_rows.append((chk, cb, dur, restart_chk))
        intro_lay.addWidget(self.mix_box)

        self.status_badge = QtWidgets.QLabel("ffmpeg debe estar instalado y visible en PATH.")
        self.status_badge.setObjectName("softBadge")
        self.status_badge.setWordWrap(True)
        intro_lay.addWidget(self.status_badge)

        self.pb = QtWidgets.QProgressBar(); self.pb.setRange(0, 100); self.pb.setValue(0)
        self.btn = QtWidgets.QPushButton("Renderizar MP4")
        self.btn.clicked.connect(self._render)
        intro_lay.addWidget(self.btn)
        intro_lay.addWidget(self.pb)

        main.addWidget(intro)
        main.addStretch(1)
        scroll.setWidget(outer)
        lay.addWidget(scroll)
        self._update_export_mode()

    def _make_export_card(self, title: str, widget: QtWidgets.QWidget, caption: str = "") -> QtWidgets.QWidget:
        frame = QtWidgets.QFrame()
        frame.setObjectName("paramCard")
        frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)
        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(4)
        lbl = QtWidgets.QLabel(title)
        lbl.setObjectName("titleMini")
        v.addWidget(lbl)
        if caption:
            txt = QtWidgets.QLabel(caption)
            txt.setObjectName("caption")
            txt.setWordWrap(True)
            v.addWidget(txt)
        v.addWidget(widget)
        return frame

    def _update_export_mode(self):
        mix_mode = self.cb_mode.currentIndex() == 1
        self.single_box.setVisible(not mix_mode)
        self.mix_box.setVisible(mix_mode)

    def _apply_resolution_preset(self):
        name = self.cb_resolution.currentText()
        dims = RESOLUTION_PRESETS.get(name)
        if dims is None:
            return
        w, h = dims
        b1 = self.sb_W.blockSignals(True)
        b2 = self.sb_H.blockSignals(True)
        self.sb_W.setValue(int(w))
        self.sb_H.setValue(int(h))
        self.sb_W.blockSignals(b1)
        self.sb_H.blockSignals(b2)

    def _mark_resolution_custom(self, *_args):
        current = self.cb_resolution.currentText()
        dims = RESOLUTION_PRESETS.get(current)
        if dims is None:
            return
        if (int(self.sb_W.value()), int(self.sb_H.value())) != dims:
            old = self.cb_resolution.blockSignals(True)
            self.cb_resolution.setCurrentText("Personalizado")
            self.cb_resolution.blockSignals(old)

    def _browse_out(self):
        suggested = self.ed_out.text().strip() or "video.mp4"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar video MP4", suggested, "Video MP4 (*.mp4)")
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.ed_out.setText(path)

    def _collect_segments(self):
        if self.cb_mode.currentIndex() == 0:
            return [(str(self.cb_preset.currentText()), float(self.ds_dur.value()), True)]
        segs = []
        for idx, (chk, cb, dur, restart_chk) in enumerate(self._mix_rows):
            if chk.isChecked():
                segs.append((str(cb.currentText()), float(dur.value()), bool(restart_chk.isChecked()) or idx == 0))
        return segs

    def _render(self):
        if self.worker is not None:
            return
        out = self.ed_out.text().strip()
        if not out:
            return
        segments = self._collect_segments()
        if not segments:
            QtWidgets.QMessageBox.warning(self, "Mezcla vacía", "Activa al menos un tramo para exportar la mezcla.")
            return

        P_live = self.wave.P
        W = int(self.sb_W.value()); H = int(self.sb_H.value())
        fps = int(self.sb_fps.value())
        grid = int(self.sb_grid.value())
        crf = int(self.sb_crf.value())

        self.btn.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.pb.setValue(0)
        if len(segments) == 1:
            self.status_badge.setText("Renderizando preset único… este proceso usa más tiempo y memoria que la vista previa en vivo.")
        else:
            self.status_badge.setText(f"Renderizando mezcla secuencial de {len(segments)} tramos…")

        class RenderThread(QtCore.QThread):
            prog = QtCore.pyqtSignal(int)
            done = QtCore.pyqtSignal(str)
            err = QtCore.pyqtSignal(str)

            def run(self_nonlocal):
                try:
                    L = float(P_live.L)
                    N = int(grid)
                    dx = L / N
                    x = np.linspace(-L/2, L/2 - dx, N, dtype=np.float32)
                    y = np.linspace(-L/2, L/2 - dx, N, dtype=np.float32)
                    X, Y = np.meshgrid(x, y)

                    total_frames = sum(max(1, int(round(duration * fps))) for _, duration, _ in segments)
                    done_frames = 0

                    def clone_live_params() -> SimParams:
                        return SimParams(**vars(P_live))

                    def build_segment_params(preset_name: str) -> SimParams:
                        P_seg = clone_live_params()
                        # Conserva el estilo visual del usuario, pero aplica los
                        # parámetros físicos sugeridos de cada preset.
                        P_seg.grid = grid
                        P_seg.fps = P_live.fps
                        P_seg.spf = P_live.spf
                        for key, value in PRESET_MODEL_DEFAULTS.get(preset_name, {}).items():
                            setattr(P_seg, key, value)
                        for key, value in PRESET_WAVE_DEFAULTS.get(preset_name, {}).items():
                            setattr(P_seg, key, float(value))
                        return P_seg

                    current_live_preset = getattr(self.wave, 'preset_name', '')
                    prev_u = None
                    prev_u_prev = None
                    prev_dt = None

                    with VideoFrameWriter(out, W=W, H=H, fps=fps, crf=crf, preset="slow") as writer:
                        for seg_idx, (preset_name, duration, restart_wave) in enumerate(segments):
                            use_live_state = len(segments) == 1 and preset_name == current_live_preset
                            P_seg = clone_live_params() if use_live_state else build_segment_params(preset_name)
                            absorb, edge_wall_mask, _ = build_boundary_state(N, P_seg)
                            rng = np.random.default_rng(7 + seg_idx)
                            V, mask, n_map, pts = PRESETS[preset_name](X, Y, P_seg, rng)
                            V = V.astype(np.float32)
                            merged_mask = np.zeros_like(V, dtype=bool)
                            if mask is not None:
                                merged_mask |= mask.astype(bool)
                            merged_mask |= edge_wall_mask.astype(bool)
                            mask = merged_mask if np.any(merged_mask) else None

                            if n_map is None:
                                c2 = (float(P_seg.c)**2) * np.ones_like(V, dtype=np.float32)
                                overlay_n = None
                            else:
                                n = np.clip(n_map.astype(np.float32), 0.2, 6.0)
                                c2 = (float(P_seg.c)**2) / (n*n)
                                overlay_n = np.clip((n - np.min(n)) / (np.max(n) - np.min(n) + 1e-6), 0, 1).astype(np.float32)

                            overlay_V = None
                            if np.max(V) > 1e-9:
                                overlay_V = np.clip(V / (np.percentile(V, 99) + 1e-6), 0, 1).astype(np.float32)
                            overlay_M = mask.astype(np.float32) if mask is not None else None
                            dots_rgb = build_dots_image(pts, N, float(P_seg.L), float(P_seg.preview_scale)) if (pts is not None and pts.shape[0] > 0) else None

                            dt_frame = 1.0 / fps
                            spf, dt = compute_stable_substeps(
                                dt_frame,
                                dx,
                                c2,
                                V,
                                max(1, int(P_seg.spf)),
                            )

                            if use_live_state or restart_wave or prev_u is None or prev_u_prev is None or prev_dt is None:
                                u, env = init_disk(X, Y, P_seg.x0, P_seg.y0, P_seg.R0, P_seg.k0, P_seg.edge)
                                ut = (-float(P_seg.c) * float(P_seg.k0) * env * np.sin(float(P_seg.k0) * (X - float(P_seg.x0)))).astype(np.float32)
                                u = (u * absorb).astype(np.float32)
                                u_prev = ((u - dt * ut) * absorb).astype(np.float32)
                            else:
                                u = (prev_u * absorb).astype(np.float32)
                                ut_est = ((prev_u - prev_u_prev) / max(prev_dt, 1e-12)).astype(np.float32)
                                u_prev = ((u - dt * ut_est) * absorb).astype(np.float32)
                            if mask is not None:
                                u[mask] = 0.0
                                u_prev[mask] = 0.0

                            n_frames = max(1, int(round(duration * fps)))
                            overlay_mode = PRESET_META.get(preset_name, {}).get('overlay', P_seg.overlay_mode)
                            for _ in range(n_frames):
                                for _sub in range(spf):
                                    div = div_c2_grad(u, c2, dx)
                                    u_next = (2*u - u_prev + (dt*dt)*(div - V*u) - float(P_seg.gamma)*dt*(u - u_prev)).astype(np.float32)
                                    u_next *= absorb
                                    np.nan_to_num(u_next, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
                                    np.clip(u_next, -1.0e6, 1.0e6, out=u_next)
                                    if mask is not None:
                                        u_next[mask] = 0.0
                                    u_prev, u = u, u_next

                                overlay = None
                                if overlay_mode == "V":
                                    overlay = overlay_V
                                elif overlay_mode == "Mask":
                                    overlay = overlay_M
                                elif overlay_mode == "n":
                                    overlay = overlay_n

                                rgb_sq = render_frame(u, dots_rgb, overlay, P_seg)
                                if P_seg.border:
                                    cv2.rectangle(rgb_sq, (0, 0), (rgb_sq.shape[1]-1, rgb_sq.shape[0]-1), tuple(theme_meta(P_seg.theme_name)["border"]), 2, lineType=cv2.LINE_AA)

                                frame = np.zeros((H, W, 3), dtype=np.uint8)
                                S = min(W, H)
                                sq = cv2.resize(rgb_sq, (S, S), interpolation=cv2.INTER_CUBIC)
                                ox = (W - S)//2
                                oy = (H - S)//2
                                frame[oy:oy+S, ox:ox+S] = sq
                                # El visor de pyqtgraph se muestra con el eje vertical invertido;
                                # para que el MP4 coincida con lo visto en pantalla, corregimos
                                # aquí la orientación vertical del cuadro exportado.
                                frame = np.flipud(frame).copy()
                                writer.write(frame)

                                done_frames += 1
                                if done_frames % max(1, fps // 2) == 0 or done_frames == total_frames:
                                    self_nonlocal.prog.emit(int(round(100 * done_frames / total_frames)))

                            prev_u = u.copy()
                            prev_u_prev = u_prev.copy()
                            prev_dt = dt

                    self_nonlocal.prog.emit(100)
                    self_nonlocal.done.emit(out)
                except Exception as e:
                    self_nonlocal.err.emit(str(e))

        th = RenderThread(self)
        th.prog.connect(self.pb.setValue)
        th.done.connect(self._done)
        th.err.connect(self._err)
        self.worker = th
        th.start()

    def _done(self, out_path: str):
        self.worker = None
        self.btn.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.pb.setValue(100)
        self.status_badge.setText(f"Listo. Video exportado en: {out_path}")
        QtWidgets.QMessageBox.information(self, "Listo", f"Exportado:\n{out_path}")

    def _err(self, msg: str):
        self.worker = None
        self.btn.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.status_badge.setText("Ocurrió un error durante la exportación.")
        QtWidgets.QMessageBox.critical(self, "Error", msg)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WaveBox Potential Lab v0.30.0 — release pública")
        tabs = QtWidgets.QTabWidget()
        self.wave = WaveBoxWidget()
        self.export = ExportTab(self.wave)
        self.info = InfoTab()
        tabs.addTab(self.wave, "Simulador")
        tabs.addTab(self.export, "Exportar")
        tabs.addTab(self.info, "Información")
        self.setCentralWidget(tabs)

    def closeEvent(self, event):
        try:
            self.wave._remember_state()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss_app_theme("Noche"))
    win = MainWindow()
    win.setMinimumSize(1180, 760)
    win.resize(1480, 900)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
