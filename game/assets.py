"""Globální registr sdílených prostředků. Inicializuje App (nebo testy) přes init()."""
from __future__ import annotations

font = None        # BitmapFont
sprites = None     # SpriteBank
icons = None       # IconBank
audio = None       # Audio
headless = False   # simulace bez grafiky (bot, testy)
_ready = False


def init(headless_sim: bool = False, audio_enabled: bool = True) -> None:
    """Načte font, sprity, ikony a zvuk. headless_sim=True přeskočí grafiku (čistá simulace)."""
    global font, sprites, icons, audio, headless, _ready
    from .audio.sound import Audio
    from .gfx.font import BitmapFont
    from .gfx.icons import IconBank
    from .gfx.sprites import SpriteBank

    headless = headless_sim
    if font is None:
        font = BitmapFont()
    if sprites is None:
        sprites = SpriteBank()
        icons = IconBank()
    if audio is None:
        audio = Audio(enabled=audio_enabled)
    _ready = True
