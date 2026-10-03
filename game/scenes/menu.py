"""Hlavní menu."""
from __future__ import annotations

import math
import random

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, VERSION, W
from ..data.meta import SEASONS
from ..gfx import pixelart as pa
from ..gfx.particles import STAR, ParticleSystem, blit_add, glow_sprite
from ..ui.widgets import Button, currency_row
from .base import Dialog, Scene

LOGO_RECT = pygame.Rect(40, 110, W - 80, 150)


class MenuScene(Scene):
    music = "menu"
    suppress_login = False      # testy/nástroje: nezobrazovat denní odměnu
    _load_error_shown = False

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
        # světlušky nad trávou a třpytky na logu (vlastní RNG – globální random stream zůstává jako dřív)
        vr = self._vrng = random.Random(21)
        self.flies = [[vr.uniform(0, W), vr.uniform(380, 560), vr.uniform(0, 6.3), vr.uniform(0.6, 1.3)]
                      for _ in range(12)]
        self.fx = ParticleSystem(80)
        self._twinkle = 0.6

    def enter(self) -> None:
        super().enter()
        # denní odměna se kontroluje při každém návratu do menu (relace přes půlnoc dostane i nový den);
        # daily_login sám hlídá, aby se v jednom dni nevyplatila dvakrát
        if not MenuScene.suppress_login:
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
            elif self.save.load_error and not MenuScene._load_error_shown:
                MenuScene._load_error_shown = True
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
        for fl in self.flies:
            fl[0] = (fl[0] + math.cos(self.t * 0.6 * fl[3] + fl[2]) * 16 * dt) % W
            fl[1] += math.sin(self.t * 0.8 * fl[3] + fl[2] * 1.7) * 10 * dt
        # občasný třpyt na logu
        self._twinkle -= dt
        if self._twinkle <= 0:
            vr = self._vrng
            self._twinkle = vr.uniform(0.5, 1.3)
            x = vr.uniform(120, W - 120)
            y = vr.choice((vr.uniform(130, 190), vr.uniform(206, 272)))
            self.fx.emit(x, y, 0, 0, 0.45, STAR, (255, 250, 220), 3)
        self.fx.update(dt)

    def draw(self, surf) -> None:
        font = assets.font
        surf.blit(_menu_backdrop(), (0, 0))
        for x, y, ph in self.stars:
            tw = math.sin(self.t * 2 + ph * 10)
            if tw > -0.3:
                surf.fill((255, 250, 220) if tw > 0.6 else (190, 180, 200), (x, y, 2, 2))
        # měsíc se září
        blit_add(surf, [(glow_sprite(16, (90, 84, 60), 0.9 + 0.1 * math.sin(self.t * 1.5)), (430 - 49, 80 - 49))])
        surf.blit(_moon(), (430 - 36, 80 - 36))
        flies = []
        for x, y, ph, sp in self.flies:
            k = 0.5 + 0.5 * math.sin(self.t * 2.2 * sp + ph * 3)
            if k > 0.2:
                flies.append((glow_sprite(2, (170, 240, 90), k), (x - 7, y - 7)))
        blit_add(surf, flies)
        for x, y, ph, sp in self.flies:
            if math.sin(self.t * 2.2 * sp + ph * 3) > -0.1:
                surf.fill((235, 255, 170), (int(x) // 3 * 3, int(y) // 3 * 3, 3, 3))
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
        self.fx.draw(surf, 0, -bounce)
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
        currency_row(surf, W // 2, 30, self.save, center=True)
        font.draw(surf, f"v{VERSION}", (W - 8, H - 4), (200, 215, 190), 2, "bottomright", outline=C_OUTLINE)
        self.draw_buttons(surf)
        self.draw_overlays(surf)


_BACKDROP: list = []


def _menu_backdrop() -> pygame.Surface:
    """Statické pozadí menu (předrenderované jednou): noční obloha v pixelových pásech, kopec, stodola,
    tráva z dlaždice Farmy ztmavená do noci."""
    if _BACKDROP:
        return _BACKDROP[0]
    from ..data.biomes import BIOMES
    from ..gfx.tiles import TILE, ground_tiles
    s = pygame.Surface((W, H))
    for i in range(0, H, 6):
        k = i / H
        col = (int(30 + 40 * k), int(20 + 18 * k), int(60 + 10 * k))
        s.fill(col, (0, i, W, 6))
    # kopec – pixelová elipsa (kreslená v art pixelech a zvětšená ×3)
    low = pygame.Surface((W // 3 + 2, 110), pygame.SRCALPHA)
    pygame.draw.ellipse(low, (40, 70, 44), (-66, 0, W // 3 + 134, 100))
    pygame.draw.ellipse(low, (52, 86, 52), (-66, 0, W // 3 + 134, 100), 1)
    s.blit(pygame.transform.scale(low, (low.get_width() * 3, low.get_height() * 3)), (0, 420))
    barn = assets.sprites.misc["barn"]
    s.blit(pa.silhouette(barn, (26, 40, 30)), (300, 330))
    # tráva = dlaždice herní mapy, ztmavená do noci
    grass = pygame.Surface((W, H - 500))
    tiles = ground_tiles(BIOMES["farm"])
    for ty in range(0, grass.get_height(), TILE):
        for tx in range(0, W, TILE):
            grass.blit(tiles[(tx // TILE + ty // TILE) % len(tiles)], (tx, ty))
    grass.fill((120, 128, 170), special_flags=pygame.BLEND_MULT)
    s.blit(grass, (0, 500))
    s.fill((30, 52, 34), (0, 500, W, 3))
    _BACKDROP.append(s)
    return s


def _moon() -> pygame.Surface:
    if len(_BACKDROP) > 1:
        return _BACKDROP[1]
    _menu_backdrop()
    low = pygame.Surface((25, 25), pygame.SRCALPHA)
    pygame.draw.circle(low, (250, 240, 200), (12, 12), 11)
    pygame.draw.circle(low, (230, 220, 180), (15, 9), 3)
    pygame.draw.circle(low, (236, 226, 186), (8, 15), 2)
    pygame.draw.arc(low, (214, 202, 168), (1, 1, 23, 23), 3.6, 5.8, 1)
    m = pygame.transform.scale(low, (75, 75))
    _BACKDROP.append(m)
    return m
