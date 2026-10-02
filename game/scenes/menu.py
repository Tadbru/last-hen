"""Hlavní menu."""
from __future__ import annotations

import math
import random

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, VERSION, W
from ..data.meta import SEASONS
from ..gfx import pixelart as pa
from ..ui.widgets import Button, currency_row
from .base import Dialog, Scene

LOGO_RECT = pygame.Rect(40, 110, W - 80, 150)


class MenuScene(Scene):
    music = "menu"
    _login_checked = False

    def __init__(self, app) -> None:
        super().__init__(app)
        self.taps = 0
        self.tap_t = 0.0
        cx = W // 2
        y = 560
        self.add(Button((cx - 200, y, 400, 96), "HRÁT", self.play, icon="play", style="primary", scale=5,
                        key=pygame.K_RETURN))
        y += 116
        bw, bh, gap = 192, 74, 16
        items = [("Hnízdo", "nest", self.nest), ("Sbírka", "book", self.collection), ("Výzvy", "trophy", self.challenges),
                 ("Denní", "calendar", self.daily), ("Obchod", "shop", self.shop), ("Nastavení", "gear", self.settings)]
        for i, (label, icon, cb) in enumerate(items):
            col, row = i % 2, i // 2
            b = self.add(Button((cx - bw - gap // 2 + col * (bw + gap), y + row * (bh + 12), bw, bh), label, cb,
                                icon=icon, style="secondary"))
            if label == "Denní" and self.save["daily"].get("last_played") != progression.today().isoformat():
                b.badge = "!"
        self.foxes = [[random.uniform(-200, W), random.uniform(470, 540), random.uniform(30, 60)] for _ in range(5)]
        self.season = progression.season_for(None, self.save.settings.get("season", "auto"))
        self.stars = [(random.randrange(W), random.randrange(420), random.random()) for _ in range(60)]

    def enter(self) -> None:
        super().enter()
        if not MenuScene._login_checked:
            MenuScene._login_checked = True
            rw = progression.daily_login(self.save)
            if rw:
                parts = []
                if rw.get("eggs"):
                    parts.append(f"{rw['eggs']} vajec")
                if rw.get("tokens"):
                    parts.append(f"{rw['tokens']} žeton" + ("y" if rw["tokens"] > 1 else ""))
                if rw.get("gold"):
                    parts.append(f"{rw['gold']} zlaté vejce")
                self.modal = Dialog(f"Den {rw['streak']} v řadě!",
                                    "Denní odměna za návštěvu farmy: " + ", ".join(parts) + ". Vrať se zítra pro další!",
                                    [("Díky!", None, "primary")], icon="calendar")
            elif self.save.load_error:
                self.modal = Dialog("Uložená hra poškozena", "Soubor save.json byl poškozený, začínáš nanovo. "
                                    "Původní soubor jsme zálohovali.", [("OK", None, "primary")])

    # --- akce ------------------------------------------------------------------------------------
    def play(self) -> None:
        from .select import SelectScene
        self.app.switch(SelectScene(self.app))

    def nest(self) -> None:
        from .nest import NestScene
        self.app.switch(NestScene(self.app))

    def collection(self) -> None:
        from .collection import CollectionScene
        self.app.switch(CollectionScene(self.app))

    def challenges(self) -> None:
        from .challenges import ChallengesScene
        self.app.switch(ChallengesScene(self.app))

    def daily(self) -> None:
        from .daily import DailyScene
        self.app.switch(DailyScene(self.app))

    def shop(self) -> None:
        from .shop import ShopScene
        self.app.switch(ShopScene(self.app))

    def settings(self) -> None:
        from .settings import SettingsScene
        self.app.switch(SettingsScene(self.app))

    def back(self) -> None:
        self.modal = Dialog("Odejít?", "Opravdu chceš opustit farmu? Lišky budou čekat.",
                            [("Odejít", self._quit, "danger"), ("Zůstat", None, "primary")])

    def _quit(self) -> None:
        self.app.running = False

    def on_down(self, ev) -> None:
        if LOGO_RECT.collidepoint(ev.x, ev.y):
            self.taps += 1
            self.tap_t = 1.5
            assets.audio.play("cluck")
            if self.taps >= 10:
                self.taps = 0
                self._penguin()

    def _penguin(self) -> None:
        d = self.save.data
        if "penguin" in d["unlocked_chars"]:
            self.toast("Tučňák už je tvůj. Pst!", (150, 210, 255))
            return
        d["unlocked_chars"].append("penguin")
        msgs = progression.complete_challenge(self.save, "penguin")
        self.save.save()
        assets.audio.play("fanfare")
        self.modal = Dialog("Tajný tučňák!", "Z ledničky vylezl tučňák v šále. Prý tu chvíli zůstane. "
                            + (msgs[0] if msgs else ""), [("Vítej!", None, "primary")], icon="fish")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.tap_t > 0:
            self.tap_t -= dt
            if self.tap_t <= 0:
                self.taps = 0
        for f in self.foxes:
            f[0] += f[2] * dt
            if f[0] > W + 60:
                f[0] = -80
                f[1] = random.uniform(470, 540)

    def draw(self, surf) -> None:
        font = assets.font
        # obloha
        for i in range(0, H, 8):
            k = i / H
            col = (int(30 + 40 * k), int(20 + 18 * k), int(60 + 10 * k))
            pygame.draw.rect(surf, col, (0, i, W, 8))
        for x, y, ph in self.stars:
            if math.sin(self.t * 2 + ph * 10) > -0.3:
                surf.fill((255, 250, 220), (x, y, 2, 2))
        pygame.draw.circle(surf, (250, 240, 200), (430, 80), 34)
        pygame.draw.circle(surf, (230, 220, 180), (440, 72), 8)
        # kopec + stodola
        pygame.draw.ellipse(surf, (40, 70, 44), (-200, 420, W + 400, 300))
        barn = assets.sprites.misc["barn"]
        surf.blit(pa.silhouette(barn, (26, 40, 30)), (300, 330))
        pygame.draw.rect(surf, (52, 90, 52), (0, 500, W, H - 500))
        for f in self.foxes:
            a = assets.sprites.enemies["fox"]
            img = a.frames[0][int(self.t * 6 + f[0]) % 2]
            surf.blit(img, (f[0], f[1]))
        if self.season:
            deco = assets.sprites.decor[SEASONS[self.season]["decor"]]
            for i, x in enumerate((30, 120, 420, 480)):
                surf.blit(deco, (x, 520 + (i % 2) * 14))
        # logo
        bounce = math.sin(self.t * 2.2) * 6
        wob = 1 if self.tap_t > 0 and int(self.t * 30) % 2 else 0
        font.draw(surf, "LAST", (W // 2 + wob, 120 + bounce), (255, 240, 220), 8, "midtop", outline=C_OUTLINE)
        font.draw(surf, "CHICKEN", (W // 2 - wob, 196 + bounce), C_GOLD, 8, "midtop", outline=C_OUTLINE)
        font.draw(surf, "poslední slepice proti zombie liškám", (W // 2, 290), (230, 210, 240), 2, "midtop",
                  outline=C_OUTLINE)
        # slepice
        hen = assets.sprites.players["hen"]
        img = pa.scale(hen.frames[0][int(self.t * 4) % 2], 2)
        hop = abs(math.sin(self.t * 4)) * 14
        surf.blit(pa.make_shadow(70, 18, 90), (W // 2 - 35, 470))
        surf.blit(img, img.get_rect(midbottom=(W // 2, 480 - hop)))
        if self.season:
            font.draw(surf, SEASONS[self.season]["name"] + "!", (W // 2, 326), (255, 170, 80), 2, "midtop",
                      outline=C_OUTLINE)
        currency_row(surf, 14, 30, self.save)
        font.draw(surf, f"v{VERSION}", (W - 8, H - 8), (120, 110, 130), 1, "bottomright")
        self.draw_buttons(surf)
        self.draw_overlays(surf)
