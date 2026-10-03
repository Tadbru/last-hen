"""Výzvy a achievementy."""
from __future__ import annotations

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, W
from ..data.meta import CHALLENGES
from ..ui.widgets import Button, ScrollArea, draw_panel, draw_title_bar, MARGIN
from ..util import fmt_num
from .base import Scene

ROW = 120


class ChallengesScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((MARGIN, 10, 64, 64), "", self.back, icon="back", style="dark"))
        self.scroll = ScrollArea((10, 130, W - 20, 820), len(CHALLENGES) * ROW)

    def on_down(self, ev) -> None:
        self.scroll.down(ev.x, ev.y)

    def on_move(self, ev) -> None:
        self.scroll.move(ev.x, ev.y)

    def on_up(self, ev) -> None:
        self.scroll.up()

    def on_wheel(self, ev) -> None:
        self.scroll.wheel(ev.dy)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.scroll.update(dt)

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((34, 30, 44))
        draw_title_bar(surf, "VÝZVY")
        done = sum(1 for c in CHALLENGES if self.save["challenges"].get(c["id"]))
        font.draw(surf, f"Splněno {done}/{len(CHALLENGES)}", (W // 2, 80), (210, 210, 230), 2, "midtop")
        r = self.scroll.rect
        clip = surf.get_clip()
        surf.set_clip(r)
        for i, c in enumerate(CHALLENGES):
            y = r.y + i * ROW - int(self.scroll.offset)
            if y > r.bottom or y + ROW < r.y:
                continue
            ok = self.save["challenges"].get(c["id"], False)
            rr = pygame.Rect(r.x, y, r.w - 10, ROW - 10)
            draw_panel(surf, rr, (70, 62, 40) if ok else (52, 46, 62), shadow=False)
            icon = assets.icons.get("trophy" if ok else "lock", 4, gray=not ok)
            surf.blit(icon, icon.get_rect(center=(rr.x + 42, rr.centery)))
            tx, tw = rr.x + 84, rr.w - 84 - 44
            font.draw(surf, c["name"], (tx, rr.y + 8), (255, 230, 170) if ok else (230, 220, 240), 2, "topleft",
                      outline=C_OUTLINE)
            yy = rr.y + 32
            for ln in font.wrap(c["desc"], tw, 2)[:2]:
                font.draw(surf, ln, (tx, yy), (215, 205, 225), 2, "topleft")
                yy += 22
            # odměna ikonami (čitelně, bez dlouhé věty)
            eggs, gold = c["reward"]
            x = tx
            ry = rr.bottom - 18
            for icon, val in (("cur_egg", eggs), ("cur_gold", gold)):
                if val:
                    ic = assets.icons.get(icon, 2)
                    surf.blit(ic, (x, ry - ic.get_height() // 2))
                    x += ic.get_width() + 4
                    font.draw(surf, fmt_num(val), (x, ry), C_GOLD, 2, "midleft", outline=C_OUTLINE)
                    x += font.width(fmt_num(val), 2) + 14
            if c.get("unlock") == "char:peacock":
                font.draw(surf, "+ Páv Diva", (x, ry), (150, 200, 255), 2, "midleft", outline=C_OUTLINE)
            if ok:
                font.draw(surf, "✓", (rr.right - 14, rr.centery), (140, 255, 140), 4, "midright", outline=C_OUTLINE)
        surf.set_clip(clip)
        self.scroll.draw_scrollbar(surf)
        self.draw_buttons(surf)
        self.draw_overlays(surf)
