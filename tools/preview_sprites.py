"""Vyrenderuje contact sheet všech spritů a ukázku fontu do PNG (kontrola grafiky).

    python tools/preview_sprites.py [výstup.png]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "sprite_sheet.png"
    pygame.init()
    pygame.display.set_mode((1, 1))
    from game.gfx.font import BitmapFont
    from game.gfx.sprites import SpriteBank
    from game.gfx import icons

    font = BitmapFont()
    bank = SpriteBank()
    ic = icons.IconBank()
    sheet = pygame.Surface((1400, 1500))
    sheet.fill((70, 110, 60))
    x, y, row_h = 10, 10, 0

    def put(img, label):
        nonlocal x, y, row_h
        w, h = img.get_size()
        if x + max(w, 60) > 1390:
            x = 10
            y += row_h + 26
            row_h = 0
        sheet.blit(img, (x, y))
        font.draw(sheet, label[:12], (x, y + h + 2), (255, 255, 255), 1)
        x += max(w, font.width(label[:12], 1)) + 14
        row_h = max(row_h, h)

    for k, a in bank.players.items():
        for i, f in enumerate(a.frames[0]):
            put(f, f"{k}{i}")
        put(a.flash[1][0], "flash")
    for k, h in bank.hats.items():
        put(h, k)
    for k, a in bank.enemies.items():
        put(a.frames[0][0], k)
    for k, s in bank.small.items():
        put(s, k)
    for k, s in bank.decor.items():
        put(s, k)
    for k, s in bank.misc.items():
        put(s, k)
    for k, s in ic.icons.items():
        put(s, k)
    y += row_h + 40
    font.draw(sheet, "Příliš žluťoučký kůň úpěl ďábelské ódy! 0123456789", (10, y), (255, 240, 200), 2)
    font.draw(sheet, "PŘÍLIŠ ŽLUŤOUČKÝ KŮŇ ÚPĚL ĎÁBELSKÉ ÓDY – Ěščřžýáíé ŮŤŇĎ", (10, y + 30), (255, 255, 255), 2,
              outline=(20, 10, 20))
    font.draw(sheet, "LAST CHICKEN 3:00 ×2 +15% ♥★→←", (10, y + 60), (255, 214, 70), 4)
    pygame.image.save(sheet, out)
    print("saved", out)


if __name__ == "__main__":
    main()
