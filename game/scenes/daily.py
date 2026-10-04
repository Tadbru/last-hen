"""Denní výzva (seed z data, 1 pokus, lokální žebříček) a týdenní boss rush."""
from __future__ import annotations

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, W
from ..data.biomes import BIOMES
from ..data.characters import CHAR_ORDER, CHARACTERS
from ..data.meta import DAILY_MOD_BY_ID
from ..ui.widgets import Button, draw_panel, draw_title_bar, MARGIN
from ..util import fmt_num
from .base import Scene, draw_scene_bg


RUSH_DESC = "5 bossů za sebou. Start s 10 level-upy, bossové sypou XP, elity bedny."


class DailyScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((MARGIN, 10, 64, 64), "", self.back, icon="back", style="dark"))
        self.spec = progression.daily_spec()
        played = self.save["daily"].get("last_played") == self.spec["date"]
        self.b_daily = self.add(Button((W - 210, 258, 190, 70), "Hrát", self.play_daily, icon="play", style="primary",
                                       sub="1 pokus denně"))
        if played:
            self.b_daily.enabled = False
            self.b_daily.text = "Hotovo"
            self.b_daily.sub = "zítra znovu"
        # výběr zvířete: všechna odemčená + dnešní zvíře výzvy (zapůjčené); mapa a modifikátor jsou pro všechny stejné
        un = self.save["unlocked_chars"]
        self.chars = [c for c in CHAR_ORDER if c in un or c == self.spec["character"]]
        self.ci = self.chars.index(self.spec["character"])
        self.b_prev = self.add(Button((MARGIN + 6, 152, 44, 60), "", lambda: self.pick(-1), icon="back", style="dark",
                                      key=pygame.K_LEFT))
        self.b_next = self.add(Button((W - MARGIN - 50, 152, 44, 60), "", lambda: self.pick(1), icon="forward",
                                      style="dark", key=pygame.K_RIGHT))
        for b in (self.b_prev, self.b_next):
            b.enabled = len(self.chars) > 1 and not played
        self.b_rush = self.add(Button((W - 210, 818, 190, 70), "Hrát", self.play_rush, icon="play", style="danger",
                                      sub="všichni bossové"))

    @property
    def char_id(self) -> str:
        return self.chars[self.ci]

    def pick(self, d: int) -> None:
        self.ci = (self.ci + d) % len(self.chars)

    def play_daily(self) -> None:
        from .game import GameScene, build_config
        sp = self.spec
        cfg = build_config(self.app, self.char_id, sp["biome"], "daily", "normal", (sp["modifier"],), sp["seed"])
        cfg.bonus_levels = 0
        self.save["daily"]["last_played"] = sp["date"]
        self.save.save()
        self.app.switch(GameScene(self.app, cfg))

    def play_rush(self) -> None:
        from .game import GameScene, build_config
        ch = self.save["last_char"] if self.save["last_char"] in self.save["unlocked_chars"] else "hen"
        cfg = build_config(self.app, ch, "farm", "bossrush", "normal")
        self.app.switch(GameScene(self.app, cfg))

    def draw(self, surf) -> None:
        font = assets.font
        draw_scene_bg(surf, self.t, (30, 36, 50))
        draw_title_bar(surf, "DENNÍ VÝZVA")
        d = self.save["daily"]
        font.draw(surf, f"Série přihlášení: {d.get('login_streak', 0)} dní · žetony: {self.save['tokens']}",
                  (W // 2, 76), (200, 210, 230), 2, "midtop")
        sp = self.spec
        r = pygame.Rect(16, 110, W - 32, 236)
        draw_panel(surf, r, (50, 58, 80))
        font.draw(surf, sp["date"], (r.x + 16, r.y + 14), C_GOLD, 2, "topleft")
        font.draw(surf, "Mapa a modifikátor pro všechny", (r.right - 16, r.y + 14), (190, 200, 220), 2, "topright")
        ch = CHARACTERS[self.char_id]
        img = assets.sprites.players[ch.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, (r.x + 64, r.y + 44))
        name_w = self.b_next.rect.x - (r.x + 132) - 8
        font.draw(surf, font.fit(ch.name, name_w, 2), (r.x + 132, r.y + 46), ch.color, 2, "topleft", outline=C_OUTLINE)
        if ch.id == sp["character"]:
            tag = "dnešní zvíře" + ("" if ch.id in self.save["unlocked_chars"] else " · zapůjčeno")
            font.draw(surf, font.fit(tag, name_w, 2), (r.x + 132, r.y + 70), (170, 220, 170), 2, "topleft")
        font.draw(surf, font.fit(f"Mapa: {BIOMES[sp['biome']].name}", name_w, 2), (r.x + 132, r.y + 94),
                  (210, 220, 240), 2, "topleft")
        mod = DAILY_MOD_BY_ID[sp["modifier"]]
        font.draw(surf, f"Modifikátor: {mod['name']}", (r.x + 16, r.y + 116), (255, 170, 120), 2, "topleft")
        yy = r.y + 142
        for ln in font.wrap(mod["desc"], r.w - 232, 2)[:3]:
            font.draw(surf, ln, (r.x + 16, yy), (220, 210, 220), 2, "topleft")
            yy += 22
        font.draw(surf, "Odměna: 1 žeton", (r.x + 16, r.bottom - 28), (255, 214, 120), 2, "topleft",
                  outline=C_OUTLINE)
        # žebříček
        board = progression.daily_leaderboard(self.save, sp)
        lr = pygame.Rect(16, 362, W - 32, 380)
        draw_panel(surf, lr, (40, 46, 64))
        font.draw(surf, "Žebříček vesnice – top 10", (lr.centerx, lr.y + 12), (255, 230, 170), 2, "midtop",
                  outline=C_OUTLINE)
        y = lr.y + 46
        for i, (name, score, me) in enumerate(board):
            col = (140, 255, 160) if me else (220, 220, 235)
            font.draw(surf, f"{i + 1}.", (lr.x + 20, y), col, 2, "topleft")
            font.draw(surf, name, (lr.x + 64, y), col, 2, "topleft")
            font.draw(surf, fmt_num(score), (lr.right - 20, y), col, 2, "topright")
            y += 32
        # boss rush
        br = pygame.Rect(16, 758, W - 32, 190)
        draw_panel(surf, br, (70, 40, 46))
        font.draw(surf, "Týdenní boss rush", (br.x + 16, br.y + 14), (255, 190, 170), 3, "topleft", outline=C_OUTLINE)
        wk = progression.iso_week()
        claimed = self.save["weekly"].get("last_claim_week") == wk
        font.draw(surf, f"Týden {wk}", (br.x + 16, br.y + 52), (220, 200, 210), 2, "topleft")
        yy = br.y + 74
        for ln in font.wrap(RUSH_DESC, self.b_rush.rect.x - br.x - 28, 2)[:3]:
            font.draw(surf, ln, (br.x + 16, yy), (220, 200, 210), 2, "topleft")
            yy += 21
        font.draw(surf, "Odměna vybrána ✓" if claimed else "Odměna: 3 zl. + 2 žetony", (br.x + 16, br.y + 140),
                  (140, 255, 160) if claimed else C_GOLD, 2, "topleft", outline=C_OUTLINE)
        best = self.save["weekly"].get("best", 0)
        if best:
            font.draw(surf, f"Rekord: {fmt_num(best)}", (br.x + 16, br.y + 164), (220, 200, 210), 2, "topleft")
        self.draw_buttons(surf)
        self.draw_overlays(surf)
