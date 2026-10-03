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
        self.foxes = [[random.uniform(-200, W), random.uniform(502, 540), random.uniform(30, 60)] for _ in range(5)]
        self.season = progression.season_for(None, self.save.settings.get("season", "auto"))
        self.stars = [(random.randrange(W), random.randrange(420), random.random()) for _ in range(60)]
        # třpytky na logu (vlastní RNG – globální random stream zůstává jako dřív)
        self._vrng = random.Random(21)
        # hustší hvězdné pole z vlastního RNG (globální random stream zůstává jako dřív)
        sr = random.Random(5)
        self.stars = self.stars + [(sr.randrange(W), int(sr.random() ** 1.4 * 330), sr.random() * 0.93)
                                   for _ in range(90)]
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
                f[1] = random.uniform(502, 540)
        # občasný třpyt na logu
        self._twinkle -= dt
        if self._twinkle <= 0:
            vr = self._vrng
            self._twinkle = vr.uniform(0.5, 1.3)
            x = vr.uniform(120, W - 120)
            y = vr.choice((vr.uniform(130, 190), vr.uniform(206, 272)))
            self.fx.emit(x, y, 0, 0, 0.45, STAR, (255, 250, 220), 3)
        self.fx.update(dt)

    def _draw_stars(self, surf) -> None:
        """Noční obloha: drobné tlumené tečky, jasné pixelové hvězdičky a pár větších třpytivých křížků,
        které jemně pulzují (nikdy nezhasnou). Mřížka 3 px jako pixel art hry; nic přes kopce ani měsíc."""
        t = self.t
        for x, y, ph in self.stars:
            if y > 330 or (x - 430) ** 2 + (y - 80) ** 2 < 56 ** 2 or (y < 48 and 150 < x < 390):
                continue
            gx, gy = x // 3 * 3, y // 3 * 3
            if ph < 0.6:
                surf.fill((132, 122, 170) if ph < 0.3 else (176, 168, 206), (gx, gy, 3, 3))
            elif ph < 0.9:
                col = ((236, 232, 255), (255, 240, 196), (200, 220, 255))[int(ph * 100) % 3]
                surf.fill(col, (gx, gy, 3, 3))
            else:
                # třpytivý křížek: jasný střed, ramena se pomalu prodlužují a zkracují
                arm = 2 if math.sin(t * 1.3 + ph * 60) > 0.2 else 1
                core, ray = (255, 252, 236), (196, 186, 236)
                for k in range(1, arm + 1):
                    c = ray if k == arm else (232, 226, 255)
                    surf.fill(c, (gx - 3 * k, gy, 3, 3))
                    surf.fill(c, (gx + 3 * k, gy, 3, 3))
                    surf.fill(c, (gx, gy - 3 * k, 3, 3))
                    surf.fill(c, (gx, gy + 3 * k, 3, 3))
                surf.fill(core, (gx, gy, 3, 3))

    def draw(self, surf) -> None:
        font = assets.font
        surf.blit(_menu_backdrop(), (0, 0))
        self._draw_stars(surf)
        # měsíc se září
        blit_add(surf, [(glow_sprite(16, (90, 84, 60), 0.9 + 0.1 * math.sin(self.t * 1.5)), (430 - 49, 80 - 49))])
        surf.blit(_moon(), (430 - 36, 80 - 36))
        if self.season:
            # sezónní dekorace stojí u plotu – lišky chodí před nimi, nikdy přes ně
            deco = _night_deco(SEASONS[self.season]["decor"])
            for x in (34, 150, 392, 506):
                surf.blit(deco, deco.get_rect(midbottom=(x, _MEADOW[x // 3] * 3 + 34)))
        a = assets.sprites.enemies["fox"]
        for i, f in enumerate(self.foxes):
            # krok podle rychlosti chůze (dřív se snímek měnil s každým posunutým pixelem)
            img = a.frames[0][int(self.t * (2.0 + f[2] * 0.04) + i * 0.37) % 2]
            surf.blit(img, (int(f[0]), int(f[1])))
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
_MEADOW: list = [154] * (W // 3)       # hrana louky v art px (pro umístění dekorací)


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
    _MEADOW[:] = meadow
    # louka: od osvětlené hrany plynule (ditherované pásy) do klidné tmavé barvy za tlačítky
    cols = [(54, 92, 60), (48, 84, 56), (42, 74, 52), (36, 64, 48), (31, 55, 44), (27, 47, 41), (24, 40, 38),
            (22, 35, 36)]
    for y in range(min(meadow), ah):
        for x in range(aw):
            if y < meadow[x]:
                continue
            f = min(len(cols) - 1.0, (y - meadow[x]) / 26.0)
            i = int(f)
            c = cols[min(len(cols) - 1, i + 1)] if f - i > 0.7 and (x + y) & 1 else cols[i]
            low.set_at((x, y), c)
    for x in range(aw):
        low.set_at((x, meadow[x]), (86, 128, 84))          # měsíční světlo na hraně louky
        if rng.random() < 0.35:                              # stébla přes hranu – hrana není rovná čára
            low.set_at((x, meadow[x] - 1), (54, 92, 60))
            if rng.random() < 0.3:
                low.set_at((x, meadow[x] - 2), (54, 92, 60))
    # trsy trávy jen v horní části louky (dál od hrany řídnou), pár kytek
    for _ in range(260):
        x = rng.randrange(1, aw - 1)
        d = rng.random() ** 1.8 * 60
        y = int(meadow[x] + 4 + d)
        light = cols[max(0, int(d / 26) - 1)] if d > 26 else (74, 116, 72)
        dark = cols[min(len(cols) - 1, int(d / 26) + 2)]
        low.set_at((x, y), light)
        low.set_at((x, y - 1), light)
        if rng.random() < 0.5:
            low.set_at((x + 1, y - 2) if rng.random() < 0.5 else (x - 1, y - 2), light)
        low.set_at((x, y + 1), dark)
    for _ in range(18):
        x = rng.randrange(1, aw - 1)
        y = meadow[x] + rng.randrange(5, 40)
        low.set_at((x, y), rng.choice(((214, 214, 240), (240, 220, 140), (190, 170, 230))))
        low.set_at((x, y + 1), (30, 56, 40))
    s = pygame.transform.scale(low, (W, H))

    sb = assets.sprites

    def put(img, cx, bottom, tint=(120, 124, 176), haze=(48, 58, 90), k=0.0, base=None):
        """Sprite v nočních barvách: tónování + „vzdušná perspektiva“ (míchání k barvě oparu)
        a volitelně stín a trsy trávy přes spodní hranu, aby stavba stála v krajině, ne na ní."""
        im = pa.tint(img, tint)
        if k > 0:
            m = int(255 * (1 - k))
            im.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
            im.fill((int(haze[0] * k), int(haze[1] * k), int(haze[2] * k)), special_flags=pygame.BLEND_RGB_ADD)
        r = im.get_rect(midbottom=(cx, bottom))
        if base is not None:
            sh = pa.make_shadow(int(r.w * 1.15) // 3 * 3, 12, 110)
            s.blit(sh, sh.get_rect(center=(cx, bottom - 3)))
        s.blit(im, r)
        if base is not None:
            fill, rim = base
            for x in range(r.x - 6, r.right + 6, 3):
                h = rng.choice((3, 3, 6, 6, 9))
                s.fill(fill, (x, bottom - h, 3, h + 3))
                if rng.random() < 0.6:
                    s.fill(rim, (x, bottom - h - 3, 3, 3))

    hill = ((30, 50, 54), (50, 80, 68))
    # na prostředním kopci: kurník (bez rampy), strašák, stodola – zapuštěné do svahu, s oparem
    put(sb.misc["coop"], 70, mid[70 // 3] * 3 + 12, (100, 104, 150), k=0.3, base=hill)
    put(sb.decor["scarecrow"], 160, mid[160 // 3] * 3 + 6, (100, 104, 150), k=0.3, base=hill)
    put(sb.misc["barn"], 412, mid[412 // 3] * 3 + 18, (100, 104, 150), k=0.28, base=hill)
    # plot na hraně louky (mezera za slepicí) a balíky sena
    fence = sb.decor["fence_h"]
    meadow_base = ((40, 70, 50), (60, 98, 64))
    for x in list(range(-6, 190, 48)) + list(range(354, W + 30, 48)):
        put(fence, x + 24, meadow[max(0, min(aw - 1, (x + 24) // 3))] * 3 + 20, k=0.12)
    put(sb.decor["haybale"], 448, 522, k=0.1, base=meadow_base)
    put(sb.decor["haybale"], 92, 518, k=0.1, base=meadow_base)
    put(sb.decor["bush"], 20, 508, (110, 116, 165), k=0.1)
    put(sb.decor["bush"], 516, 506, (110, 116, 165), k=0.1)
    _BACKDROP.append(s)
    return s


def _night_deco(name: str) -> pygame.Surface:
    """Sezónní dekorace ztlumená do nočních barev (jinak by svítila jako nalepená)."""
    key = "deco:" + name
    img = _DECO.get(key)
    if img is None:
        img = _DECO[key] = pa.tint(assets.sprites.decor[name], (190, 186, 220))
    return img


_DECO: dict = {}


_MOON: list = []


def _moon() -> pygame.Surface:
    # vlastní cache – výsledky (noc) dřív kvůli měsíci stavěly celé pozadí menu (B-79)
    if _MOON:
        return _MOON[0]
    low = pygame.Surface((25, 25), pygame.SRCALPHA)
    pygame.draw.circle(low, (250, 240, 200), (12, 12), 11)
    pygame.draw.circle(low, (230, 220, 180), (15, 9), 3)
    pygame.draw.circle(low, (236, 226, 186), (8, 15), 2)
    pygame.draw.arc(low, (214, 202, 168), (1, 1, 23, 23), 3.6, 5.8, 1)
    m = pygame.transform.scale(low, (75, 75))
    _MOON.append(m)
    return m
