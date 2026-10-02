"""Denní výzva (seed z data, 1 pokus, lokální žebříček) a týdenní boss rush."""
from __future__ import annotations

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, W
from ..data.biomes import BIOMES
from ..data.characters import CHARACTERS
from ..data.meta import DAILY_MOD_BY_ID
from ..ui.widgets import Button, draw_panel
from ..util import fmt_num
from .base import Scene


class DailyScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((10, 10, 70, 64), "", self.back, icon="back", style="dark"))
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
        font.draw(surf, "DENNÍ VÝZVA", (W // 2, 18), (255, 220, 150), 5, "midtop", outline=C_OUTLINE)
        d = self.save["daily"]
        font.draw(surf, f"Série přihlášení: {d.get('login_streak', 0)} dní · žetony: {self.save['tokens']}",
                  (W // 2, 76), (200, 210, 230), 2, "midtop")
        sp = self.spec
        r = pygame.Rect(16, 110, W - 32, 236)
        draw_panel(surf, r, (50, 58, 80))
        font.draw(surf, sp["date"], (r.x + 16, r.y + 14), C_GOLD, 2, "topleft")
        font.draw(surf, "Stejná výzva pro všechny", (r.right - 16, r.y + 14), (190, 200, 220), 1, "topright")
        ch = CHARACTERS[sp["character"]]
        img = assets.sprites.players[ch.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, (r.x + 16, r.y + 44))
        font.draw(surf, ch.name, (r.x + 84, r.y + 50), C_TEXT, 2, "topleft")
        font.draw(surf, f"Mapa: {BIOMES[sp['biome']].name}", (r.x + 84, r.y + 76), (210, 220, 240), 2, "topleft")
        mod = DAILY_MOD_BY_ID[sp["modifier"]]
        font.draw(surf, f"Modifikátor: {mod['name']}", (r.x + 16, r.y + 116), (255, 170, 120), 2, "topleft")
        font.draw_wrapped(surf, mod["desc"], pygame.Rect(r.x + 16, r.y + 142, r.w - 230, 60), (220, 210, 220), 1)
        font.draw(surf, "Odměna: 1 žeton", (r.x + 16, r.bottom - 26), (255, 214, 120), 1, "topleft")
        if not ch.id in self.save["unlocked_chars"]:
            font.draw(surf, "(zvíře zapůjčeno na dnešek)", (r.x + 84, r.y + 98), (170, 200, 170), 1, "topleft")
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
        font.draw(surf, f"Týden {wk}", (br.x + 16, br.y + 50), (220, 200, 210), 1, "topleft")
        font.draw(surf, "Všech 5 bossů za sebou,", (br.x + 16, br.y + 70), (220, 200, 210), 1, "topleft")
        font.draw(surf, "start s 8 levelupy.", (br.x + 16, br.y + 86), (220, 200, 210), 1, "topleft")
        font.draw(surf, "Odměna vybrána ✓" if claimed else "Odměna: 3 zl. vejce + 2 žetony", (br.x + 16, br.y + 110),
                  (140, 255, 160) if claimed else C_GOLD, 1, "topleft")
        best = self.save["weekly"].get("best", 0)
        if best:
            font.draw(surf, f"Nejlepší skóre: {fmt_num(best)}", (br.x + 16, br.y + 130), (220, 200, 210), 1, "topleft")
        self.draw_buttons(surf)
        self.draw_overlays(surf)
