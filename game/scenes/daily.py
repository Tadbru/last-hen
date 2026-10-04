"""Denní výzva (seed z data, 1 pokus, lokální žebříček) a týdenní boss rush."""
from __future__ import annotations

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, W
from ..data.biomes import BIOMES
from ..data.characters import CHAR_ORDER, CHARACTERS
from ..data.meta import DAILY_MOD_BY_ID, WEEKLY_RUSH_TOKENS
from ..ui.widgets import Button, draw_panel, draw_title_bar, MARGIN
from ..util import fmt_num
from .base import Scene, draw_scene_bg


RUSH_DESC = "5 bossů za sebou. Start s 10 level-upy, bossové sypou XP, elity bedny."
RUSH_Y = 724        # horní okraj panelu boss rushe (pod zkráceným žebříčkem)


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
        # boss rush: zvíře si hráč vybere ze všech odemčených (denní výzva má pevné zvíře dne)
        un = self.save["unlocked_chars"]
        self.chars = [c for c in CHAR_ORDER if c in un] or ["hen"]
        # výchozí je zvíře z posledního boss rushe, jinak naposledy hrané (B-106)
        last = self.save["weekly"].get("char") or self.save["last_char"]
        if last not in self.chars:
            last = self.save["last_char"]
        self.ci = self.chars.index(last) if last in self.chars else 0
        x0 = W - 210
        self.b_prev = self.add(Button((x0, RUSH_Y + 46, 40, 56), "", lambda: self.pick(-1), icon="back", style="dark",
                                      key=pygame.K_LEFT))
        self.b_next = self.add(Button((x0 + 150, RUSH_Y + 46, 40, 56), "", lambda: self.pick(1), icon="forward",
                                      style="dark", key=pygame.K_RIGHT))
        for b in (self.b_prev, self.b_next):
            b.enabled = len(self.chars) > 1
        self.b_rush = self.add(Button((x0, RUSH_Y + 136, 190, 70), "Hrát", self.play_rush, icon="play", style="danger",
                                      sub="všichni bossové"))

    @property
    def rush_char(self) -> str:
        return self.chars[self.ci]

    def pick(self, d: int) -> None:
        self.ci = (self.ci + d) % len(self.chars)

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
        self.save["weekly"]["char"] = self.rush_char        # zapamatovat volbu pro příští rush (B-106)
        self.save.save()
        cfg = build_config(self.app, self.rush_char, "farm", "bossrush", "normal")
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
        font.draw(surf, "Pro všechny stejná", (r.right - 16, r.y + 14), (190, 200, 220), 2, "topright")
        ch = CHARACTERS[sp["character"]]
        img = assets.sprites.players[ch.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, (r.x + 16, r.y + 44))
        name_w = r.right - 16 - (r.x + 84)
        font.draw(surf, font.fit(ch.name, name_w, 2), (r.x + 84, r.y + 46), ch.color, 2, "topleft", outline=C_OUTLINE)
        tag = "zvíře dne" + ("" if ch.id in self.save["unlocked_chars"] else " · zapůjčeno na dnešek")
        font.draw(surf, font.fit(tag, name_w, 2), (r.x + 84, r.y + 70), (170, 220, 170), 2, "topleft")
        font.draw(surf, font.fit(f"Mapa: {BIOMES[sp['biome']].name}", name_w, 2), (r.x + 84, r.y + 94),
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
        lr = pygame.Rect(16, 362, W - 32, 348)
        draw_panel(surf, lr, (40, 46, 64))
        font.draw(surf, "Žebříček vesnice – top 10", (lr.centerx, lr.y + 12), (255, 230, 170), 2, "midtop",
                  outline=C_OUTLINE)
        y = lr.y + 46
        for i, (name, score, me) in enumerate(board):
            col = (140, 255, 160) if me else (220, 220, 235)
            font.draw(surf, f"{i + 1}.", (lr.x + 20, y), col, 2, "topleft")
            font.draw(surf, name, (lr.x + 64, y), col, 2, "topleft")
            font.draw(surf, fmt_num(score), (lr.right - 20, y), col, 2, "topright")
            y += 30
        # boss rush
        br = pygame.Rect(16, RUSH_Y, W - 32, 948 - RUSH_Y)
        draw_panel(surf, br, (70, 40, 46))
        font.draw(surf, "Týdenní boss rush", (br.x + 16, br.y + 14), (255, 190, 170), 3, "topleft", outline=C_OUTLINE)
        wk = progression.iso_week()
        claimed = self.save["weekly"].get("last_claim_week") == wk
        font.draw(surf, f"Týden {wk}", (br.x + 16, br.y + 52), (220, 200, 210), 2, "topleft")
        yy = br.y + 76
        for ln in font.wrap(RUSH_DESC, self.b_rush.rect.x - br.x - 28, 2)[:3]:
            font.draw(surf, ln, (br.x + 16, yy), (220, 200, 210), 2, "topleft")
            yy += 21
        font.draw(surf, "Odměna vybrána ✓" if claimed else f"Odměna: {WEEKLY_RUSH_TOKENS} žetony", (br.x + 16, br.y + 156),
                  (140, 255, 160) if claimed else C_GOLD, 2, "topleft", outline=C_OUTLINE)
        best = self.save["weekly"].get("best", 0)
        if best:
            font.draw(surf, f"Rekord: {fmt_num(best)}", (br.x + 16, br.y + 182), (220, 200, 210), 2, "topleft")
        # vybrané zvíře pro boss rush (mezi šipkami nad tlačítkem Hrát)
        rc = CHARACTERS[self.rush_char]
        cx = self.b_rush.rect.centerx
        img = assets.sprites.players[rc.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, img.get_rect(center=(cx, self.b_prev.rect.centery)))
        # světlý odstín barvy zvířete – červená/modrá na vínovém panelu by splývala (B-107)
        light = tuple(int(v + (255 - v) * 0.55) for v in rc.color)
        font.draw(surf, font.fit(rc.name, self.b_rush.rect.w, 2), (cx, br.y + 108), light, 2, "midtop",
                  outline=C_OUTLINE)
        self.draw_buttons(surf)
        self.draw_overlays(surf)
