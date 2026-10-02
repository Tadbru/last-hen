"""Hnízdo – trvalá vylepšení za vejce."""
from __future__ import annotations

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, C_TEXT, W
from ..data.meta import NEST_UPGRADES
from ..ui.widgets import Button, currency_row, draw_icon_frame, draw_panel
from ..util import fmt_num
from .base import Dialog, Scene


class NestScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((10, 10, 70, 64), "", self.back, icon="back", style="dark"))
        self.rows = []
        y = 150
        for u in NEST_UPGRADES:
            b = self.add(Button((W - 186, y + 14, 166, 74), "", lambda u=u: self.buy(u), icon="cur_egg", style="gold"))
            self.rows.append((u, pygame.Rect(16, y, W - 32, 102), b))
            y += 114
        self.add(Button((W // 2 - 140, y + 6, 280, 64), "Vrátit vše", self.refund, icon="reroll", style="secondary"))
        self._sync()

    def _sync(self) -> None:
        meta = self.save["meta"]
        for u, r, b in self.rows:
            lv = meta.get(u["id"], 0)
            if lv >= len(u["costs"]):
                b.text = "MAX"
                b.icon = "check"
                b.enabled = False
            else:
                cost = u["costs"][lv]
                b.text = fmt_num(cost)
                b.enabled = self.save["eggs"] >= cost

    def buy(self, u) -> None:
        meta = self.save["meta"]
        lv = meta.get(u["id"], 0)
        if lv >= len(u["costs"]):
            return
        cost = u["costs"][lv]
        if self.save["eggs"] < cost:
            return
        self.save["eggs"] -= cost
        meta[u["id"]] = lv + 1
        self.save.save()
        assets.audio.play("levelup")
        self.toast(f"{u['name']} → úroveň {lv + 1}", C_GOLD)
        self._sync()

    def refund(self) -> None:
        meta = self.save["meta"]
        total = 0
        for u in NEST_UPGRADES:
            total += sum(u["costs"][: meta.get(u["id"], 0)])
        if total == 0:
            self.toast("Není co vracet.")
            return

        def do():
            for u in NEST_UPGRADES:
                meta[u["id"]] = 0
            self.save["eggs"] += total
            self.save.save()
            self._sync()
            self.toast(f"Vráceno {fmt_num(total)} vajec", C_GOLD)
        self.modal = Dialog("Vrátit vylepšení?", f"Získáš zpět {fmt_num(total)} vajec.",
                            [("Vrátit", do, "danger"), ("Zpět", None, "secondary")])

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((44, 32, 34))
        font.draw(surf, "HNÍZDO", (W // 2, 18), (255, 220, 150), 5, "midtop", outline=C_OUTLINE)
        font.draw(surf, "Trvalá vylepšení pro všechna zvířata", (W // 2, 72), (220, 200, 190), 2, "midtop")
        currency_row(surf, W // 2 - 140, 118, self.save)
        meta = self.save["meta"]
        for u, r, b in self.rows:
            draw_panel(surf, r, (66, 50, 52))
            draw_icon_frame(surf, (r.x + 12, r.y + 14, 74, 74), u["icon"], scale=4)
            sc = 3 if font.width(u["name"], 3) < r.w - 290 else 2
            font.draw(surf, u["name"], (r.x + 98, r.y + 14), (255, 240, 210), sc, "topleft", outline=C_OUTLINE)
            font.draw(surf, u["desc"] + " / úroveň", (r.x + 98, r.y + 50), (210, 200, 200), 1, "topleft")
            lv = meta.get(u["id"], 0)
            for i in range(len(u["costs"])):
                col = C_GOLD if i < lv else (40, 30, 34)
                pygame.draw.rect(surf, (20, 12, 18), (r.x + 98 + i * 26, r.y + 72, 22, 14))
                pygame.draw.rect(surf, col, (r.x + 100 + i * 26, r.y + 74, 18, 10))
        _ = C_TEXT
        self.draw_buttons(surf)
        self.draw_overlays(surf)
