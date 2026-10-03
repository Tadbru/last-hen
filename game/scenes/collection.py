"""Sbírka – encyklopedie nepřátel, bossů, zbraní, evolucí a pasivek."""
from __future__ import annotations

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..data.bosses import BOSSES
from ..data.enemies import ENEMIES
from ..data.passives import PASSIVES
from ..data.weapons import WEAPONS
from ..gfx import pixelart as pa
from ..ui.widgets import Button, ScrollArea, draw_icon_frame, draw_panel, draw_title_bar, MARGIN
from .base import Scene

TABS = [("enemies", "Lišky"), ("bosses", "Bossové"), ("weapons", "Zbraně"), ("evolutions", "Evoluce"),
        ("passives", "Pasivky")]
TILE = 96


class CollectionScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((MARGIN, 10, 64, 64), "", self.back, icon="back", style="dark"))
        self.tab = "enemies"
        self.tab_btns = []
        tw = (W - 20) // len(TABS)
        for i, (tid, name) in enumerate(TABS):
            sc = 2 if assets.font.width(name, 2) <= tw - 16 else 1
            b = self.add(Button((10 + i * tw, 132, tw - 4, 64), name, lambda t=tid: self.set_tab(t), scale=sc))
            self.tab_btns.append((tid, b))
        self.scroll = ScrollArea((10, 206, W - 20, 470))
        self.sel = None
        self._thumbs: dict = {}
        self.set_tab("enemies")

    def set_tab(self, tid: str) -> None:
        self.tab = tid
        self.sel = None
        for t, b in self.tab_btns:
            b.selected = t == tid          # vybraná záložka = rámeček, ne oranžová akce (B-36)
        items = progression.COLLECTION_CATS[tid][1]
        rows = (len(items) + 4) // 5
        self.scroll.content_h = rows * (TILE + 8)
        self.scroll.offset = 0

    def items(self):
        return progression.COLLECTION_CATS[self.tab][1]

    def _thumb(self, cat: str, iid: str, known: bool) -> pygame.Surface:
        key = (cat, iid, known)
        s = self._thumbs.get(key)
        if s is not None:
            return s
        if cat in ("enemies", "bosses"):
            spr = ENEMIES[iid].sprite if cat == "enemies" else BOSSES[iid].sprite
            img = assets.sprites.enemies[spr].frames[0][0]
            k = min(1.0, 80 / max(img.get_width(), img.get_height()))
            s = pa.scale(img, k) if k < 1 else img
            if not known:
                s = pa.silhouette(s, (20, 14, 26))
        else:
            icon = WEAPONS[iid].icon if cat in ("weapons", "evolutions") else PASSIVES[iid].icon
            s = assets.icons.get(icon, 5, evo=cat == "evolutions", gray=not known)
        self._thumbs[key] = s
        return s

    def on_down(self, ev) -> None:
        self.scroll.down(ev.x, ev.y)

    def on_move(self, ev) -> None:
        self.scroll.move(ev.x, ev.y)

    def on_up(self, ev) -> None:
        if self.scroll.up():
            r = self.scroll.rect
            lx = ev.x - r.x
            ly = ev.y - r.y + self.scroll.offset
            col = int(lx // (TILE + 8))
            row = int(ly // (TILE + 8))
            idx = row * 5 + col
            if 0 <= col < 5 and 0 <= idx < len(self.items()):
                self.sel = self.items()[idx]
                assets.audio.play("click")

    def on_wheel(self, ev) -> None:
        self.scroll.wheel(ev.dy)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.scroll.update(dt)

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((30, 30, 44))
        draw_title_bar(surf, "SBÍRKA")
        have, total = progression.collection_progress(self.save)
        font.draw(surf, f"Objeveno {have}/{total} ({int(100 * have / max(1, total))} %)", (W // 2, 74),
                  (210, 210, 230), 2, "midtop")
        font.draw(surf, "100 % kategorie = 3 zlatá vejce", (W // 2, 100), (255, 214, 120), 2, "midtop")
        r = self.scroll.rect
        clip = surf.get_clip()
        surf.set_clip(r)
        items = self.items()
        for i, iid in enumerate(items):
            col, row = i % 5, i // 5
            x = r.x + col * (TILE + 8)
            y = r.y + row * (TILE + 8) - int(self.scroll.offset)
            if y > r.bottom or y + TILE < r.y:
                continue
            known = self.save.is_discovered(self.tab, iid)
            rr = pygame.Rect(x, y, TILE, TILE)
            pygame.draw.rect(surf, (255, 214, 70) if self.sel == iid else (16, 12, 20), rr)
            pygame.draw.rect(surf, (54, 50, 72) if known else (36, 32, 46), rr.inflate(-6, -6))
            img = self._thumb(self.tab, iid, known)
            surf.blit(img, img.get_rect(center=rr.center))
            if not known:
                font.draw(surf, "?", rr.center, (200, 190, 210), 3, "center", outline=C_OUTLINE)
        surf.set_clip(clip)
        self.scroll.draw_scrollbar(surf)
        # detail
        dr = pygame.Rect(10, H - 270, W - 20, 256)
        draw_panel(surf, dr, (52, 46, 66))
        if self.sel is None:
            font.draw(surf, "Klepni na položku", dr.center, (180, 170, 190), 2, "center")
        else:
            iid = self.sel
            known = self.save.is_discovered(self.tab, iid)
            if self.tab == "enemies":
                d = ENEMIES[iid]
                name, desc = d.name, d.desc
                extra = f"Zdraví {int(d.hp)} · Rychlost {int(d.speed)} · Poškození {int(d.dmg)}"
            elif self.tab == "bosses":
                d = BOSSES[iid]
                name, desc = d.name, d.desc
                extra = f"„{d.intro}“"
            elif self.tab in ("weapons", "evolutions"):
                d = WEAPONS[iid]
                name, desc = d.name, d.desc
                if d.evolution:
                    base = WEAPONS[d.evolved_from]
                    extra = f"{base.name} úr. 8 + {PASSIVES[base.evo_passive].name}"
                else:
                    extra = f"Evoluce: {WEAPONS[d.evo_to].name} (+ {PASSIVES[d.evo_passive].name})" if d.evo_to else ""
            else:
                d = PASSIVES[iid]
                name, desc = d.name, f"{d.desc} na úroveň. {d.flavor}"
                extra = ""
            if not known:
                name, desc, extra = "???", "Ještě jsi to nepotkala. Hraj dál!", ""
            img = self._thumb(self.tab, iid, known)
            surf.blit(img, img.get_rect(center=(dr.x + 64, dr.y + 70)))
            font.draw(surf, name, (dr.x + 130, dr.y + 20), (255, 230, 170), 3, "topleft", outline=C_OUTLINE)
            font.draw_wrapped(surf, desc, pygame.Rect(dr.x + 130, dr.y + 62, dr.w - 146, 120), C_TEXT, 2)
            if extra:
                font.draw_wrapped(surf, extra, pygame.Rect(dr.x + 20, dr.bottom - 60, dr.w - 40, 50), C_GOLD, 2)
        self.draw_buttons(surf)
        self.draw_overlays(surf)
