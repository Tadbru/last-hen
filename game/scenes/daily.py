"""Denní výzva (seed z data, 1 pokus, lokální žebříček) a týdenní boss rush."""
from __future__ import annotations

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, W
from ..data.biomes import BIOMES
from ..data.characters import CHARACTERS
from ..data.meta import DAILY_MOD_BY_ID
from ..ui.widgets import Button, draw_panel, draw_title_bar, MARGIN
from ..util import fmt_num
from .base import Scene


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
        self.b_rush = self.add(Button((W - 210, 818, 190, 70), "Hrát", self.play_rush, icon="play", style="danger",
                                      sub="všichni bossové"))

    def play_daily(self) -> None:
        from .game import GameScene, build_config
        sp = self.spec
        cfg = build_config(self.app, sp["character"], sp["biome"], "daily", "normal", (sp["modifier"],), sp["seed"])
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
        surf.fill((30, 36, 50))
        draw_title_bar(surf, "DENNÍ VÝZVA")
        d = self.save["daily"]
        font.draw(surf, f"Série přihlášení: {d.get('login_streak', 0)} dní · žetony: {self.save['tokens']}",
                  (W // 2, 76), (200, 210, 230), 2, "midtop")
        sp = self.spec
        r = pygame.Rect(16, 110, W - 32, 236)
        draw_panel(surf, r, (50, 58, 80))
        font.draw(surf, sp["date"], (r.x + 16, r.y + 14), C_GOLD, 2, "topleft")
        font.draw(surf, "Pro všechny stejná", (r.right - 16, r.y + 14), (190, 200, 220), 2, "topright")
        ch = CHARACTERS[sp["character"]]
        img = assets.sprites.players[ch.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, (r.x + 16, r.y + 44))
        font.draw(surf, ch.name, (r.x + 84, r.y + 50), C_TEXT, 2, "topleft")
        font.draw(surf, f"Mapa: {BIOMES[sp['biome']].name}", (r.x + 84, r.y + 76), (210, 220, 240), 2, "topleft")
        mod = DAILY_MOD_BY_ID[sp["modifier"]]
        font.draw(surf, f"Modifikátor: {mod['name']}", (r.x + 16, r.y + 116), (255, 170, 120), 2, "topleft")
        yy = r.y + 142
        for ln in font.wrap(mod["desc"], r.w - 232, 2)[:3]:
            font.draw(surf, ln, (r.x + 16, yy), (220, 210, 220), 2, "topleft")
            yy += 22
        font.draw(surf, "Odměna: 1 žeton", (r.x + 16, r.bottom - 28), (255, 214, 120), 2, "topleft",
                  outline=C_OUTLINE)
        if not ch.id in self.save["unlocked_chars"]:
            font.draw(surf, "zapůjčeno na dnešek", (r.right - 16, r.y + 50), (170, 220, 170), 2, "topright")
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
