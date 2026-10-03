"""Globální konstanty hry."""
from __future__ import annotations

import os
import sys

TITLE = "LAST CHICKEN"
VERSION = "1.0.6"   # při buildu APK ji přepíše GitHub Actions (1.0.<číslo buildu>)

# Logické rozlišení (portrait). Vše se kreslí sem a škáluje do okna.
W, H = 540, 960
LOGIC_HZ = 60
DT = 1.0 / LOGIC_HZ
MAX_FRAME_SKIP = 5          # max logických kroků na jeden render (ochrana proti spirále smrti)

PX = 3                      # měřítko pixel artu (1 art pixel = 3 logické pixely)

# Cesty – vše relativně ke složce projektu.
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from .device import MOBILE, data_dir  # noqa: E402

DATA_DIR = data_dir(ROOT)
SAVE_PATH = os.path.join(DATA_DIR, "save.json")
CRASH_LOG = os.path.join(DATA_DIR, "crash.log")
SHARES_DIR = os.path.join(DATA_DIR, "shares")

# Herní limity (výkon) – na telefonu o něco nižší
MAX_ENEMIES = 320 if MOBILE else 420
MAX_PROJECTILES = 300 if MOBILE else 360
MAX_PARTICLES = 450 if MOBILE else 700
MAX_PICKUPS = 380
MAX_TEXTS = 70

# Barvy UI
C_BG = (28, 20, 34)
C_PANEL = (52, 38, 58)
C_PANEL_HI = (78, 58, 86)
C_TEXT = (250, 244, 230)
C_DIM = (170, 160, 175)
C_GOLD = (255, 214, 70)
C_RED = (235, 70, 70)
C_GREEN = (120, 220, 90)
C_PURPLE = (170, 90, 220)
C_BLUE = (90, 170, 245)
C_OUTLINE = (24, 16, 28)
RARITY_COLORS = [(200, 200, 210), (80, 170, 255), (210, 110, 255)]
RARITY_NAMES = ["Běžná", "Vzácná", "Epická"]


class Flags:
    """Runtime přepínače z CLI."""
    debug = False
    quick = False
    headless = False
