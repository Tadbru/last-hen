"""Vygeneruje ikonu aplikace a úvodní obrazovku (presplash) z herních spritů do app_assets/.

    python tools/make_app_assets.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    from game.config import C_OUTLINE
    from game.gfx import pixelart as pa
    from game.gfx.font import BitmapFont
    from game.gfx.sprites import SpriteBank

    out = os.path.join(ROOT, "app_assets")
    os.makedirs(out, exist_ok=True)
    font = BitmapFont()
    bank = SpriteBank()
    hen_small = bank.players["hen"].frames[0][0]          # 51×51 (×3)

    # --- ikona 512×512 ---
    icon = pygame.Surface((512, 512))
    for y in range(512):
        k = y / 512
        pygame.draw.line(icon, (int(60 + 40 * k), int(34 + 20 * k), int(90 - 20 * k)), (0, y), (512, y))
    pygame.draw.circle(icon, (250, 236, 190), (390, 110), 56)
    pygame.draw.ellipse(icon, (64, 110, 60), (-80, 360, 672, 300))
    fox = pa.scale(bank.enemies["fox"].frames[1][0], 2)
    icon.blit(fox, (12, 330))
    icon.blit(pa.flip(fox), (512 - fox.get_width() - 12, 336))
    hen = pa.scale(hen_small, 5.4)
    icon.blit(pa.make_shadow(220, 50, 110), (146, 418))
    icon.blit(hen, hen.get_rect(midbottom=(256, 448)))
    pygame.image.save(icon, os.path.join(out, "icon.png"))

    # --- presplash 540×960 ---
    sp = pygame.Surface((540, 960))
    sp.fill((28, 20, 34))
    font.draw(sp, "LAST", (270, 250), (255, 240, 220), 9, "midtop", outline=C_OUTLINE)
    font.draw(sp, "CHICKEN", (270, 340), (255, 214, 70), 9, "midtop", outline=C_OUTLINE)
    h = pa.scale(hen_small, 3)
    sp.blit(h, h.get_rect(midbottom=(270, 640)))
    font.draw(sp, "Načítám kurník…", (270, 700), (210, 200, 220), 3, "midtop")
    pygame.image.save(sp, os.path.join(out, "presplash.png"))
    print("app_assets/icon.png + presplash.png hotovo")


if __name__ == "__main__":
    main()
