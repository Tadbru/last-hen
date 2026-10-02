"""Výzvy a achievementy."""
from __future__ import annotations

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, W
from ..data.meta import CHALLENGES
from ..ui.widgets import Button, ScrollArea, draw_panel
from ..util import fmt_num
from .base import Scene

ROW = 104


class ChallengesScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((10, 10, 70, 64), "", self.back, icon="back", style="dark"))
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
        font.draw(surf, "VÝZVY", (W // 2, 18), (255, 220, 150), 5, "midtop", outline=C_OUTLINE)
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
            font.draw(surf, c["name"], (rr.x + 84, rr.y + 12), (255, 230, 170) if ok else (230, 220, 240), 3, "topleft",
                      outline=C_OUTLINE)
            font.draw(surf, c["desc"], (rr.x + 84, rr.y + 48), (210, 200, 220), 1, "topleft")
            eggs, gold = c["reward"]
            rw = []
            if eggs:
                rw.append(f"{fmt_num(eggs)} vajec")
            if gold:
                rw.append(f"{gold} zl. vejce")
            if c.get("unlock") == "char:peacock":
                rw.append("odemkne Páva Divu")
            font.draw(surf, "Odměna: " + ", ".join(rw), (rr.x + 84, rr.y + 68), C_GOLD, 1, "topleft")
            if ok:
                font.draw(surf, "✓", (rr.right - 20, rr.centery), (140, 255, 140), 4, "midright", outline=C_OUTLINE)
        surf.set_clip(clip)
        self.scroll.draw_scrollbar(surf)
        self.draw_buttons(surf)
        self.draw_overlays(surf)
