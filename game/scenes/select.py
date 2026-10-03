"""Výběr zvířete, mapy, módu a obtížnosti."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..data.biomes import BIOME_ORDER, BIOMES
from ..data.characters import CHAR_ORDER, CHARACTERS
from ..data.meta import DIFF_ORDER, DIFFICULTIES
from ..data.weapons import WEAPONS
from ..gfx import pixelart as pa
from ..gfx.tiles import ground_tiles
from ..ui.widgets import MARGIN as M
from ..ui.widgets import (SELECT_COLOR, Button, currency_row, draw_frame, draw_icon_frame, draw_panel,
                          draw_title_bar)
from ..util import fmt_num
from .base import Dialog, Scene, draw_scene_bg


class SelectScene(Scene):
    music = "menu"

    def __init__(self, app) -> None:
        super().__init__(app)
        s = self.save
        self.ci = CHAR_ORDER.index(s["last_char"]) if s["last_char"] in CHAR_ORDER else 0
        self.biome = s["last_map"] if s["last_map"] in s["unlocked_maps"] else "farm"
        self.mode = s["last_mode"] if s["last_mode"] in ("quick", "full") else "quick"
        self.diff = s["last_diff"] if s["last_diff"] in s["unlocked_diffs"] else "normal"
        self.add(Button((M, 10, 64, 64), "", self.back, icon="back", style="dark"))
        self.add(Button((M, 196, 52, 120), "", self.prev, icon="back", style="dark", key=pygame.K_LEFT))
        self.add(Button((W - M - 52, 196, 52, 120), "", self.next, icon="forward", style="dark", key=pygame.K_RIGHT))
        self.b_buy = self.add(Button((W // 2 - 150, 436, 300, 60), "Koupit", self.buy_char, style="gold",
                                     icon="cur_egg"))
        self.map_rects = [pygame.Rect(M + i * 104, 524, 96, 94) for i in range(5)]
        half = (W - 2 * M - 12) // 2
        self.b_quick = self.add(Button((M, 652, half, 66), "Rychlý", lambda: self.set_mode("quick"),
                                       sub="3 minuty", icon="clock"))
        self.b_full = self.add(Button((W - M - half, 652, half, 66), "Plný", lambda: self.set_mode("full"),
                                      sub="10 minut", icon="clock"))
        self.b_diff = []
        dw = (W - 2 * M - 24) // 3
        for i, did in enumerate(DIFF_ORDER):
            bt = self.add(Button((M + i * (dw + 12), 756, dw, 62), DIFFICULTIES[did].name,
                                 lambda d=did: self.set_diff(d), scale=2))
            self.b_diff.append(bt)
        self.b_start = self.add(Button((M, 834, W - 2 * M, 96), "START!", self.start, icon="play", style="primary",
                                       scale=5, key=pygame.K_RETURN))
        self.thumbs = {}
        for bid in BIOME_ORDER:
            t = ground_tiles(BIOMES[bid])[0]
            self.thumbs[bid] = pygame.transform.scale(t.subsurface((0, 0, 96, 64)), (88, 58))
        self._sync()

    # --- stav ------------------------------------------------------------------------------------
    @property
    def char(self):
        return CHARACTERS[CHAR_ORDER[self.ci]]

    def unlocked(self, cid: str) -> bool:
        return cid in self.save["unlocked_chars"]

    def _sync(self) -> None:
        c = self.char
        un = self.unlocked(c.id)
        self.b_buy.visible = (not un) and c.unlock == "eggs"
        self.b_buy.text = f"Koupit {fmt_num(c.cost)}"
        self.b_buy.enabled = self.save["eggs"] >= c.cost
        self.b_start.enabled = un and self.biome in self.save["unlocked_maps"]
        # jednotný styl „vybráno“ = rámeček + fajfka; oranžová zůstává jen akcím (B-36)
        self.b_quick.selected = self.mode == "quick"
        self.b_full.selected = self.mode == "full"
        for did, bt in zip(DIFF_ORDER, self.b_diff):
            ok = did in self.save["unlocked_diffs"]
            bt.enabled = ok
            bt.selected = did == self.diff
            bt.sel_color = DIFFICULTIES[did].color      # barva obtížnosti jen jako rámeček – text čitelný (B-34)
            bt.sub = "" if ok else "zamčeno"

    def prev(self) -> None:
        self.ci = (self.ci - 1) % len(CHAR_ORDER)
        self._sync()

    def next(self) -> None:
        self.ci = (self.ci + 1) % len(CHAR_ORDER)
        self._sync()

    def set_mode(self, m: str) -> None:
        self.mode = m
        self._sync()

    def set_diff(self, d: str) -> None:
        self.diff = d
        self._sync()

    def buy_char(self) -> None:
        c = self.char
        if self.save["eggs"] < c.cost:
            self.toast("Málo vajec!", (255, 120, 120))
            return

        def do():
            self.save["eggs"] -= c.cost
            self.save["unlocked_chars"].append(c.id)
            self.save.save()
            assets.audio.play("fanfare")
            self.toast(f"{c.name} se přidává do boje!", C_GOLD)
            self._sync()
        self.modal = Dialog("Odemknout?", f"{c.name} za {fmt_num(c.cost)} vajec?",
                            [("Koupit", do, "gold"), ("Zpět", None, "secondary")])

    def on_down(self, ev) -> None:
        for bid, r in zip(BIOME_ORDER, self.map_rects):
            if r.collidepoint(ev.x, ev.y):
                self.pick_map(bid)
                return
        # swipe přes postavu
        if 100 < ev.y < 420:
            self._swipe = ev.x

    def on_up(self, ev) -> None:
        sx = getattr(self, "_swipe", None)
        self._swipe = None
        if sx is not None:
            if ev.x - sx > 60:
                self.prev()
            elif sx - ev.x > 60:
                self.next()

    def pick_map(self, bid: str) -> None:
        b = BIOMES[bid]
        if bid in self.save["unlocked_maps"]:
            self.biome = bid
            assets.audio.play("click")
            self._sync()
            return
        if self.save["eggs"] < b.unlock_cost:
            self.toast(f"{b.name}: vyhraj na předchozí mapě nebo zaplať {fmt_num(b.unlock_cost)} vajec", (255, 170, 120))
            return

        def do():
            self.save["eggs"] -= b.unlock_cost
            self.save["unlocked_maps"].append(bid)
            self.save.save()
            self.biome = bid
            assets.audio.play("fanfare")
            self._sync()
        self.modal = Dialog("Odemknout mapu?", f"{b.name} za {fmt_num(b.unlock_cost)} vajec?",
                            [("Koupit", do, "gold"), ("Zpět", None, "secondary")])

    def start(self) -> None:
        from .game import GameScene, build_config
        s = self.save
        s["last_char"] = self.char.id
        s["last_map"] = self.biome
        s["last_mode"] = self.mode
        s["last_diff"] = self.diff
        s.save()
        self.app.switch(GameScene(self.app, build_config(self.app, self.char.id, self.biome, self.mode, self.diff)))

    # --- kreslení --------------------------------------------------------------------------------
    def draw(self, surf) -> None:
        font = assets.font
        draw_scene_bg(surf, self.t, (36, 26, 44))
        c = self.char
        un = self.unlocked(c.id)
        draw_title_bar(surf, "Vyber zvíře")
        currency_row(surf, W // 2, 92, self.save, center=True)
        r = pygame.Rect(76, 112, W - 152, 300)
        draw_panel(surf, r, (58, 44, 68))
        anim = assets.sprites.players[c.id]
        img = pa.scale(anim.frames[0][int(self.t * 4) % 2], 2)
        if not un:
            img = pa.silhouette(img, (20, 14, 26))
        hop = abs(math.sin(self.t * 3)) * 8 if un else 0
        surf.blit(pa.make_shadow(70, 16, 90), (r.centerx - 35, r.y + 118))
        surf.blit(img, img.get_rect(midbottom=(r.centerx, r.y + 128 - hop)))
        if not un:
            lk = assets.icons.get("lock", 5)
            surf.blit(lk, lk.get_rect(center=(r.centerx + 70, r.y + 70)))
        font.draw(surf, c.name if un else "???", (r.centerx, r.y + 134), c.color if un else C_TEXT, 3, "midtop",
                  outline=C_OUTLINE)
        if un or c.unlock != "secret":
            tw = r.w - 24
            w = WEAPONS[c.weapon]
            y = r.y + 176
            draw_icon_frame(surf, (r.x + 12, y, 40, 40), w.icon, scale=3, gray=not un)
            font.draw(surf, font.fit(w.name, tw - 52, 2), (r.x + 60, y + 9), (255, 230, 180), 2, "topleft",
                      outline=C_OUTLINE)
            y += 48
            for ln in font.wrap(c.passive_desc, tw, 2)[:2]:
                font.draw(surf, ln, (r.x + 12, y), (170, 235, 170), 2, "topleft", outline=C_OUTLINE)
                y += font.line_h(2)
            font.draw(surf, font.fit("Slabina: " + c.weakness, tw, 2), (r.x + 12, y + 2), (255, 160, 150), 2,
                      "topleft", outline=C_OUTLINE)
        # tečky postav – nad tlačítkem Koupit (B-42)
        for i, cid in enumerate(CHAR_ORDER):
            x = W // 2 + (i - 3) * 26
            col = (255, 214, 70) if i == self.ci else (130, 120, 140) if self.unlocked(cid) else (66, 56, 72)
            pygame.draw.circle(surf, col, (x, 424), 7 if i == self.ci else 5)
        if not un:
            if c.unlock != "eggs":
                for j, ln in enumerate(font.wrap(c.unlock_text, W - 2 * M, 2)[:2]):
                    font.draw(surf, ln, (W // 2, 442 + j * 24), (255, 200, 140), 2, "midtop", outline=C_OUTLINE)
        else:
            for j, ln in enumerate(font.wrap(c.desc, W - 2 * M, 2)[:2]):
                font.draw(surf, ln, (W // 2, 440 + j * 24), (220, 210, 230), 2, "midtop")
        # mapy
        section(surf, "Mapa", 498)
        for bid, rr in zip(BIOME_ORDER, self.map_rects):
            bm = BIOMES[bid]
            ok = bid in self.save["unlocked_maps"]
            pygame.draw.rect(surf, (24, 16, 28), rr)
            th = self.thumbs[bid]
            if not ok:
                th = th.copy()
                th.fill((90, 90, 90), special_flags=pygame.BLEND_MULT)
            surf.blit(th, (rr.x + 4, rr.y + 4))
            if ok:
                font.draw(surf, bm.short or bm.name, (rr.centerx, rr.y + 66), C_TEXT, 2, "midtop", outline=C_OUTLINE)
            else:
                lk = assets.icons.get("lock", 3)
                surf.blit(lk, lk.get_rect(center=(rr.centerx, rr.y + 32)))
                font.draw(surf, fmt_num(bm.unlock_cost), (rr.centerx, rr.y + 66), C_GOLD, 2, "midtop",
                          outline=C_OUTLINE)
            if bid == self.biome:
                draw_frame(surf, rr, SELECT_COLOR, 3, 6)
        section(surf, "Mód", 626)
        section(surf, "Obtížnost", 730)
        self.draw_buttons(surf)
        self.draw_overlays(surf)


def section(surf, text: str, y: int) -> None:
    """Nadpis sekce – jednotně u všech skupin (B-35)."""
    assets.font.draw(surf, text, (M, y), (255, 230, 150), 2, "topleft", outline=C_OUTLINE)
