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
from ..ui.widgets import Button, currency_row, draw_icon_frame, draw_panel
from ..util import fmt_num
from .base import Dialog, Scene


class SelectScene(Scene):
    music = "menu"

    def __init__(self, app) -> None:
        super().__init__(app)
        s = self.save
        self.ci = CHAR_ORDER.index(s["last_char"]) if s["last_char"] in CHAR_ORDER else 0
        self.biome = s["last_map"] if s["last_map"] in s["unlocked_maps"] else "farm"
        self.mode = s["last_mode"] if s["last_mode"] in ("quick", "full") else "quick"
        self.diff = s["last_diff"] if s["last_diff"] in s["unlocked_diffs"] else "normal"
        self.add(Button((10, 10, 70, 64), "", self.back, icon="back", style="dark"))
        self.add(Button((10, 200, 56, 120), "", self.prev, icon="back", style="dark", key=pygame.K_LEFT))
        nb = self.add(Button((W - 66, 200, 56, 120), "", self.next, icon="play", style="dark", key=pygame.K_RIGHT))
        nb.icon_scale = 3
        self.b_buy = self.add(Button((W // 2 - 150, 386, 300, 64), "Koupit", self.buy_char, style="gold",
                                     icon="cur_egg"))
        self.map_rects = [pygame.Rect(14 + i * 103, 508, 97, 112) for i in range(5)]
        self.b_quick = self.add(Button((24, 640, 238, 70), "Rychlý", lambda: self.set_mode("quick"), sub="3 minuty",
                                       icon="clock"))
        self.b_full = self.add(Button((278, 640, 238, 70), "Plný", lambda: self.set_mode("full"), sub="10 minut",
                                      icon="clock"))
        self.b_diff = []
        for i, did in enumerate(DIFF_ORDER):
            b = self.add(Button((24 + i * 168, 724, 156, 64), DIFFICULTIES[did].name,
                                lambda d=did: self.set_diff(d), scale=2))
            self.b_diff.append(b)
        self.b_start = self.add(Button((24, 812, W - 48, 100), "START!", self.start, icon="play", style="primary",
                                       scale=5, key=pygame.K_RETURN))
        self.thumbs = {}
        for bid in BIOME_ORDER:
            t = ground_tiles(BIOMES[bid])[0]
            self.thumbs[bid] = pygame.transform.scale(t.subsurface((0, 0, 96, 96)), (89, 70))
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
        self.b_quick.style = "primary" if self.mode == "quick" else "secondary"
        self.b_full.style = "primary" if self.mode == "full" else "secondary"
        for did, b in zip(DIFF_ORDER, self.b_diff):
            ok = did in self.save["unlocked_diffs"]
            b.enabled = ok
            b.style = "primary" if did == self.diff else "secondary"
            b.color = DIFFICULTIES[did].color if did == self.diff else None
            b.sub = "" if ok else "zamčeno"

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
        if 90 < ev.y < 380:
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
        surf.fill((36, 26, 44))
        c = self.char
        un = self.unlocked(c.id)
        font.draw(surf, "Vyber zvíře", (W // 2, 20), (255, 230, 150), 3, "midtop", outline=C_OUTLINE)
        currency_row(surf, W - 12, 92, self.save, anchor_right=True)
        r = pygame.Rect(76, 112, W - 152, 268)
        draw_panel(surf, r, (58, 44, 68))
        anim = assets.sprites.players[c.id]
        img = pa.scale(anim.frames[0][int(self.t * 4) % 2], 2)
        if not un:
            img = pa.silhouette(img, (20, 14, 26))
        hop = abs(math.sin(self.t * 3)) * 8 if un else 0
        surf.blit(pa.make_shadow(70, 16, 90), (r.centerx - 35, r.y + 128))
        surf.blit(img, img.get_rect(midbottom=(r.centerx, r.y + 138 - hop)))
        font.draw(surf, c.name if un else "???", (r.centerx, r.y + 146), c.color if un else C_TEXT, 3, "midtop",
                  outline=C_OUTLINE)
        if un or c.unlock != "secret":
            w = WEAPONS[c.weapon]
            draw_icon_frame(surf, (r.x + 10, r.y + 186, 44, 44), w.icon, scale=3, gray=not un)
            font.draw(surf, w.name, (r.x + 62, r.y + 188), (255, 230, 180), 2, "topleft")
            lines = font.wrap(c.passive_name + ": " + c.passive_desc, r.w - 72, 1)[:2]
            for i, ln in enumerate(lines):
                font.draw(surf, ln, (r.x + 62, r.y + 210 + i * 13), (180, 230, 180), 1, "topleft")
            font.draw(surf, "Slabina: " + c.weakness, (r.x + 12, r.y + 244), (255, 160, 150), 1, "topleft")
        if not un:
            img = assets.icons.get("lock", 5)
            surf.blit(img, img.get_rect(center=(r.centerx + 70, r.y + 80)))
            if c.unlock != "eggs":
                font.draw(surf, c.unlock_text, (W // 2, 400), (255, 200, 140), 2, "midtop", outline=C_OUTLINE)
        else:
            lines = font.wrap(c.desc, W - 60, 2)[:2]
            for i, ln in enumerate(lines):
                font.draw(surf, ln, (W // 2, 392 + i * 24), (220, 210, 230), 2, "midtop")
        # tečky postav
        for i, cid in enumerate(CHAR_ORDER):
            x = W // 2 + (i - 3) * 26
            col = (255, 214, 70) if i == self.ci else (120, 110, 130) if self.unlocked(cid) else (60, 50, 66)
            pygame.draw.circle(surf, col, (x, 452), 7 if i == self.ci else 5)
        # mapy
        font.draw(surf, "Mapa", (24, 478), (255, 230, 150), 2, "topleft", outline=C_OUTLINE)
        for bid, rr in zip(BIOME_ORDER, self.map_rects):
            b = BIOMES[bid]
            ok = bid in self.save["unlocked_maps"]
            sel = bid == self.biome
            pygame.draw.rect(surf, (255, 214, 70) if sel else (24, 16, 28), rr.inflate(6, 6) if sel else rr)
            pygame.draw.rect(surf, (24, 16, 28), rr)
            th = self.thumbs[bid]
            if not ok:
                th = th.copy()
                th.fill((90, 90, 90), special_flags=pygame.BLEND_MULT)
            surf.blit(th, (rr.x + 4, rr.y + 4))
            font.draw(surf, b.short or b.name, (rr.centerx, rr.y + 80),
                      C_TEXT if ok else (150, 140, 150), 1, "midtop", outline=C_OUTLINE)
            if not ok:
                img = assets.icons.get("lock", 3)
                surf.blit(img, img.get_rect(center=(rr.centerx, rr.y + 38)))
                font.draw(surf, fmt_num(b.unlock_cost), (rr.centerx, rr.y + 96), C_GOLD, 1, "midtop", outline=C_OUTLINE)
        font.draw(surf, BIOMES[self.biome].desc, (W // 2, 624), (200, 190, 210), 1, "midtop")
        font.draw(surf, "Obtížnost", (24, 704), (255, 230, 150), 1, "topleft")
        self.draw_buttons(surf)
        self.draw_overlays(surf)
