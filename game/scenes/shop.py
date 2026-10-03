"""Obchod – kosmetické skiny (za zlatá vejce) a truhly (za žetony). Žádný pay-to-win."""
from __future__ import annotations

import random

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, W
from ..data.characters import CHAR_ORDER, CHARACTERS
from ..data.meta import CHEST_COST, SKINS
from ..gfx import pixelart as pa
from ..ui.widgets import Button, currency_row, draw_panel, draw_title_bar, MARGIN
from ..util import fmt_num
from .base import Dialog, Scene


class ShopScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((MARGIN, 10, 64, 64), "", self.back, icon="back", style="dark"))
        owned = [c for c in CHAR_ORDER if c in self.save["unlocked_chars"]]
        self.chars = owned
        self.ci = 0
        if self.save["last_char"] in owned:
            self.ci = owned.index(self.save["last_char"])
        self.add(Button((14, 150, 56, 80), "", lambda: self.cycle(-1), icon="back", style="dark"))
        self.add(Button((W - 70, 150, 56, 80), "", lambda: self.cycle(1), icon="forward", style="dark"))
        self.season = progression.season_for(None, "auto")     # skutečná sezóna podle data
        self.rows = []
        y = 262
        for s in SKINS:
            b = self.add(Button((W - 196, y + 8, 180, 56), "", lambda s=s: self.skin_action(s), scale=2))
            self.rows.append((s, pygame.Rect(16, y, W - 32, 72), b))
            y += 78
        self.add(Button((W - 226, y + 22, 210, 80), f"Otevřít ({CHEST_COST})", self.open_chest, icon="cur_token",
                        style="primary"))
        self.chest_y = y + 12
        self._sync()

    @property
    def char(self) -> str:
        return self.chars[self.ci]

    def cycle(self, d: int) -> None:
        self.ci = (self.ci + d) % len(self.chars)
        self._sync()

    def available(self, s) -> bool:
        return progression.skin_usable(self.save, s["id"])

    def _sync(self) -> None:
        eq = self.save["skin"].get(self.char)
        for s, r, b in self.rows:
            if self.available(s):
                if eq == s["id"]:
                    b.text, b.style, b.icon = "Sundat", "secondary", None
                else:
                    b.text, b.style, b.icon = "Nasadit", "green", None
                b.enabled = True
            elif s["season"] is not None:
                b.text, b.style, b.icon, b.enabled = "Jen v sezóně", "secondary", None, False
            else:
                b.text, b.style, b.icon = f"{s['price']}", "gold", "cur_gold"
                b.enabled = self.save["gold"] >= s["price"]

    def skin_action(self, s) -> None:
        sk = self.save["skin"]
        if self.available(s):
            if sk.get(self.char) == s["id"]:
                sk.pop(self.char, None)
            else:
                sk[self.char] = s["id"]
            self.save.save()
            self._sync()
            return
        if self.save["gold"] < s["price"]:
            return

        def do():
            self.save["gold"] -= s["price"]
            self.save["skins_owned"].append(s["id"])
            self.save["skin"][self.char] = s["id"]
            self.save.save()
            assets.audio.play("fanfare")
            self._sync()
        self.modal = Dialog("Koupit skin?", f"{s['name']} za {s['price']} zlatých vajec?",
                            [("Koupit", do, "gold"), ("Zpět", None, "secondary")])

    def open_chest(self) -> None:
        if self.save["tokens"] < CHEST_COST:
            self.toast("Nemáš žetony – zahraj si denní výzvu!", (255, 150, 120))
            return
        self.save["tokens"] -= CHEST_COST
        r = random.random()
        text = ""
        if r < 0.45:
            n = random.choice([80, 120, 150, 200, 300])
            self.save["eggs"] += n
            text = f"{fmt_num(n)} vajec!"
            icon = "cur_egg"
        elif r < 0.7:
            n = random.choice([1, 1, 2])
            self.save["gold"] += n
            text = f"{n} zlaté vejce!" if n == 1 else f"{n} zlatá vejce!"
            icon = "cur_gold"
        elif r < 0.85:
            self.save["tokens"] += 1
            self.save["eggs"] += 50
            text = "Žeton zpět + 50 vajec!"
            icon = "cur_token"
        else:
            opts = [s for s in SKINS if s["season"] is None and s["id"] not in self.save["skins_owned"]]
            if opts:
                s = random.choice(opts)
                self.save["skins_owned"].append(s["id"])
                text = f"Skin: {s['name']}!"
                icon = "star"
            else:
                self.save["gold"] += 2
                text = "2 zlatá vejce!"
                icon = "cur_gold"
        self.save.save()
        assets.audio.play("chest")
        self.modal = Dialog("Truhla!", text, [("Super!", None, "primary")], icon=icon)
        self._sync()

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((40, 30, 48))
        draw_title_bar(surf, "OBCHOD")
        currency_row(surf, W // 2, 100, self.save, center=True)
        c = CHARACTERS[self.char]
        anim = assets.sprites.players[self.char]
        img = anim.frames[0][int(self.t * 3) % 2]
        surf.blit(img, img.get_rect(midbottom=(W // 2 - 60, 228)))
        hat_id = self.save["skin"].get(self.char)
        if hat_id and hat_id in assets.sprites.hats and progression.skin_usable(self.save, hat_id):
            from ..world.render import HAT_ANCHOR
            from ..config import PX
            hx, hy = HAT_ANCHOR.get(self.char, (7, 0))
            hat = assets.sprites.hats[hat_id]
            r = img.get_rect(midbottom=(W // 2 - 60, 228))
            surf.blit(hat, (r.x + (hx + 1) * PX - hat.get_width() / 2, r.y + (hy + 1) * PX - hat.get_height() + 3))
        font.draw(surf, c.name, (W // 2 + 10, 170), (255, 240, 210), 2, "midleft", outline=C_OUTLINE)
        font.draw(surf, "Skin se nasadí vybranému zvířeti", (W // 2, 236), (200, 190, 210), 2, "midtop")
        for s, r, b in self.rows:
            draw_panel(surf, r, (58, 46, 66), shadow=False)
            hat = assets.sprites.hats[s["id"]]
            surf.blit(pa.scale(hat, 1.5), (r.x + 14, r.y + 18))
            font.draw(surf, s["name"], (r.x + 74, r.y + 10), (255, 240, 210), 2, "topleft", outline=C_OUTLINE)
            tag = "vlastníš" if self.available(s) else ("sezónní" if s["season"] else "kosmetika")
            font.draw(surf, tag, (r.x + 74, r.y + 38), (180, 200, 180) if self.available(s) else (190, 180, 200), 2,
                      "topleft")
        y = self.chest_y
        draw_panel(surf, (16, y, W - 32, 100), (70, 52, 40), shadow=False)
        ic = assets.icons.get("chest", 6)
        surf.blit(ic, (34, y + 22))
        font.draw(surf, "Truhla štěstí", (116, y + 14), (255, 230, 170), 2, "topleft", outline=C_OUTLINE)
        for j, ln in enumerate(font.wrap("Vejce, zlatá vejce nebo skin", W - 226 - 116 - 10, 2)[:2]):
            font.draw(surf, ln, (116, y + 42 + j * 22), (220, 200, 180), 2, "topleft")
        _ = C_GOLD
        self.draw_buttons(surf)
        self.draw_overlays(surf)
