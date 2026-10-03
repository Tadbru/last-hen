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
        # třpytky na logu (vlastní RNG – globální random stream zůstává jako dřív)
        self._vrng = random.Random(21)
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
        a = assets.sprites.enemies["fox"]
        for i, f in enumerate(self.foxes):
            # krok podle rychlosti chůze (dřív se snímek měnil s každým posunutým pixelem)
            img = a.frames[0][int(self.t * (2.0 + f[2] * 0.04) + i * 0.37) % 2]
            surf.blit(img, (int(f[0]), int(f[1])))
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
    """Statické pozadí menu (předrenderované jednou), kreslené v art pixelech 180×320 a zvětšené ×3:
    obloha s ditherem, vzdálené kopce se smrky, kopec se stodolou, kurníkem a strašákem, louka s trsy trávy
    a kytkami až dolů (bez předělu), plot a balíky sena z herních spritů v nočních barvách."""
    if _BACKDROP:
        return _BACKDROP[0]
    rng = random.Random(1987)
    aw, ah = W // 3, H // 3
    low = pygame.Surface((aw, ah))

    def band_fill(y0, y1, c0, c1, steps, xs=None):
        """Svislý přechod po pásech; hranice pásů ditherované (šachovnice), žádné tvrdé švy."""
        hgt = max(1, y1 - y0)
        cols = [tuple(int(c0[k] + (c1[k] - c0[k]) * i / max(1, steps - 1)) for k in range(3)) for i in range(steps)]
        for y in range(y0, y1):
            f = (y - y0) / hgt * steps
            i = min(steps - 1, int(f))
            nxt = min(steps - 1, i + 1)
            edge = f - i > 0.75 and nxt != i
            for x in range(aw) if xs is None else xs:
                low.set_at((x, y), cols[nxt] if edge and (x + y) & 1 else cols[i])

    # obloha
    band_fill(0, ah, (22, 14, 46), (86, 50, 92), 9)

    def ridge(base, a1, f1, p1, a2, f2, p2):
        return [int(base + a1 * math.sin(x * f1 + p1) + a2 * math.sin(x * f2 + p2)) for x in range(aw)]

    def fill_below(ry, col, rim, dither_col=None):
        for x in range(aw):
            for y in range(ry[x], ah):
                low.set_at((x, y), col)
            low.set_at((x, ry[x]), rim)
            if dither_col is not None and ry[x] + 2 < ah and x & 1:
                low.set_at((x, ry[x] + 2), dither_col)

    far = ridge(119, 5, 0.05, 1.0, 3, 0.13, 2.0)
    fill_below(far, (42, 34, 76), (66, 56, 108))
    pine_px = []
    for x in rng.sample(range(4, aw - 4), 9):
        h = rng.randint(5, 8)
        top = far[x] - h
        for k in range(h + 1):
            half = k // 3
            for dx in range(-half, half + 1):
                if 0 <= x + dx < aw:
                    pine_px.append((x + dx, top + k))
    for px_, py_ in pine_px:
        low.set_at((px_, py_), (32, 26, 60))
    mid = ridge(139, 6, 0.028, 2.4, 3, 0.09, 0.3)
    fill_below(mid, (30, 50, 54), (56, 86, 72), (40, 64, 62))
    meadow = ridge(154, 3, 0.045, 0.7, 2, 0.12, 1.1)
    # louka: od hrany dolů tmavne po ditherovaných pásech
    for y in range(min(meadow), ah):
        for x in range(aw):
            if y < meadow[x]:
                continue
            d = y - meadow[x]
            f = min(5.0, d / 34 * 5)
            i = int(f)
            cols = [(54, 92, 60), (48, 84, 56), (42, 74, 50), (36, 64, 46), (30, 54, 40), (26, 46, 36)]
            c = cols[min(5, i + 1)] if f - i > 0.75 and (x + y) & 1 else cols[min(5, i)]
            low.set_at((x, y), c)
    for x in range(aw):
        low.set_at((x, meadow[x]), (86, 128, 84))          # měsíční světlo na hraně louky
        if rng.random() < 0.35:                              # stébla přes hranu – hrana není rovná čára
            low.set_at((x, meadow[x] - 1), (54, 92, 60))
            if rng.random() < 0.3:
                low.set_at((x, meadow[x] - 2), (54, 92, 60))
    # trsy trávy a kytky
    for _ in range(420):
        x = rng.randrange(aw)
        y = rng.randrange(meadow[x] + 3, ah)
        d = (y - meadow[x]) / (ah - meadow[x])
        if rng.random() < 0.5:
            c = (70, 112, 70) if d < 0.5 else (52, 86, 58)
            low.set_at((x, y), c)
            low.set_at((x, y - 1), c)
            if x + 1 < aw and rng.random() < 0.5:
                low.set_at((x + 1, y), c)
        else:
            low.set_at((x, y), (22, 40, 30))
    for _ in range(26):
        x = rng.randrange(1, aw - 1)
        y = rng.randrange(meadow[x] + 4, meadow[x] + 70)
        if y < ah:
            low.set_at((x, y), rng.choice(((214, 214, 240), (240, 220, 140), (190, 170, 230))))
            low.set_at((x, y + 1), (30, 56, 40))
    s = pygame.transform.scale(low, (W, H))

    night = (120, 124, 176)
    sb = assets.sprites

    def put(img, cx, bottom, tint=night):
        im = pa.tint(img, tint)
        s.blit(im, im.get_rect(midbottom=(cx, bottom)))

    # na prostředním kopci: kurník, strašák, stodola (spodek trochu zapuštěný do svahu)
    put(sb.misc["coop"], 70, mid[70 // 3] * 3 + 14, (100, 104, 150))
    put(sb.decor["scarecrow"], 160, mid[160 // 3] * 3 + 8, (100, 104, 150))
    put(sb.misc["barn"], 412, mid[412 // 3] * 3 + 22, (100, 104, 150))
    # plot na hraně louky (mezera za slepicí) a balíky sena
    fence = sb.decor["fence_h"]
    for x in list(range(-6, 190, 48)) + list(range(354, W + 30, 48)):
        put(fence, x + 24, meadow[max(0, min(aw - 1, (x + 24) // 3))] * 3 + 20)
    put(sb.decor["haybale"], 448, 520)
    put(sb.decor["haybale"], 92, 516)
    put(sb.decor["bush"], 20, 506, (110, 116, 165))
    put(sb.decor["bush"], 516, 504, (110, 116, 165))
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
