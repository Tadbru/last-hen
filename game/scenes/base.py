"""Základ scén, modální dialogy (vč. falešné reklamy) a jednoduché události vstupu."""
from __future__ import annotations

import math

import pygame

from .. import assets, device
from ..config import C_OUTLINE, C_TEXT, H, W
from ..ui.widgets import Button, draw_panel


class Ev:
    """Událost v logických souřadnicích: down / up / move / key / wheel."""
    __slots__ = ("type", "x", "y", "key", "dy")

    def __init__(self, type_: str, x: float = 0.0, y: float = 0.0, key: int = 0, dy: float = 0.0) -> None:
        self.type = type_
        self.x, self.y = x, y
        self.key = key
        self.dy = dy


class Dialog:
    """Modální okno s tlačítky. timer > 0 → odpočet (falešná reklama), pak se zavolá on_done."""

    def __init__(self, title: str, text: str, buttons: list[tuple] | None = None, timer: float = 0.0,
                 on_done=None, ad: bool = False, icon: str | None = None) -> None:
        self.title = title
        self.text = text
        self.timer = timer
        self.on_done = on_done
        self.ad = ad
        self.icon = icon
        self.t = 0.0
        self.closed = False
        self.buttons: list[Button] = []
        if ad:
            h = 440
        else:
            # výška podle obsahu (B-45) – žádné poloprázdné dialogy
            font = assets.font
            lines = len(font.wrap(text, W - 80 - 48, 2)) if text else 0
            ih = assets.icons.get(icon, 5).get_height() + 12 if icon else 0
            h = max(220, 24 + ih + 46 + lines * font.line_h(2) + 24 + (90 if buttons else 0))
        self.rect = pygame.Rect(40, H // 2 - h // 2, W - 80, h)
        bs = buttons or []
        n = len(bs)
        bw = (self.rect.w - 40 - (n - 1) * 12) // max(1, n)
        for i, b in enumerate(bs):
            label, cb = b[0], b[1]
            style = b[2] if len(b) > 2 else "secondary"

            def make(cb=cb):
                def f():
                    self.closed = True
                    if cb:
                        cb()
                return f
            self.buttons.append(Button((self.rect.x + 20 + i * (bw + 12), self.rect.bottom - 90, bw, 70), label,
                                       make(), style=style))
        self._pressed = None

    def handle(self, ev: Ev) -> None:
        if self.timer > 0:
            return
        if ev.type == "down":
            for b in self.buttons:
                if b.contains(ev.x, ev.y) and b.enabled:
                    b.pressed = True
                    self._pressed = b
        elif ev.type == "up":
            b = self._pressed
            self._pressed = None
            if b is not None:
                b.pressed = False
                if b.contains(ev.x, ev.y):
                    b.click()
        elif ev.type == "key" and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE) and self.buttons:
            # klávesy (i Android Zpět) nikdy nespustí nevratnou („danger“) akci
            safe = [i for i, b in enumerate(self.buttons) if b.style != "danger"]
            if not safe:
                return
            if ev.key == pygame.K_ESCAPE:
                i = safe[-1]
                if i == safe[0] and len(safe) < len(self.buttons) and i == 0:
                    return       # jediná bezpečná volba je hlavní akce (např. reklama) – Zpět nic nespustí
            else:
                i = safe[0]
            self.buttons[i].click()

    def update(self, dt: float) -> None:
        self.t += dt
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.closed = True
                if self.on_done:
                    self.on_done()

    def draw(self, surf) -> None:
        font = assets.font
        surf.blit(dim_layer(170), (0, 0))
        k = min(1.0, self.t * 6)
        r = self.rect.inflate(-(1 - k) * 60, -(1 - k) * 60)
        if self.ad:
            draw_panel(surf, r, (250, 236, 200))
            font.draw(surf, "REKLAMA", (r.right - 14, r.y + 12), (140, 100, 60), 2, "topright", shadow=False)
            font.draw(surf, self.title, (r.centerx, r.y + 40), (120, 60, 20), 3, "midtop", shadow=False)
            # „produkt“
            cx, cy = r.centerx, r.centery - 10
            bounce = math.sin(self.t * 8) * 6
            pygame.draw.rect(surf, (230, 190, 40), (cx - 50, cy - 60 + bounce, 100, 120))
            pygame.draw.rect(surf, (140, 90, 20), (cx - 50, cy - 60 + bounce, 100, 120), 4)
            font.draw(surf, "KUKUŘICE", (cx, cy - 10 + bounce), (120, 60, 20), 2, "center", shadow=False)
            font.draw_wrapped(surf, self.text, pygame.Rect(r.x + 30, cy + 80, r.w - 60, 80), (90, 60, 40), 2,
                              "center", shadow=False)
            font.draw(surf, f"Reklama skončí za {max(0, math.ceil(self.timer))} s", (r.centerx, r.bottom - 30),
                      (160, 110, 60), 2, "midbottom", shadow=False)
            return
        draw_panel(surf, r, (62, 46, 70))
        y = r.y + 24
        if self.icon:
            img = assets.icons.get(self.icon, 5)
            surf.blit(img, img.get_rect(midtop=(r.centerx, y)))
            y += img.get_height() + 12
        font.draw(surf, self.title, (r.centerx, y), (255, 220, 140), 3, "midtop", outline=C_OUTLINE)
        y += 46
        font.draw_wrapped(surf, self.text, pygame.Rect(r.x + 24, y, r.w - 48, max(24, r.bottom - 100 - y)), C_TEXT, 2,
                          "center")
        if k >= 1:
            for b in self.buttons:
                b.draw(surf, self.t)


class Scene:
    music = "menu"
    toast_y = 112        # pod nadpisem; scény s akcemi nahoře si to přepíšou (B-47)

    def __init__(self, app) -> None:
        self.app = app
        self.buttons: list[Button] = []
        self.t = 0.0
        self._pressed: Button | None = None
        self.modal: Dialog | None = None
        self.toasts: list[list] = []

    @property
    def save(self):
        return self.app.save

    def enter(self) -> None:
        if self.music and assets.audio:
            assets.audio.play_music(self.music, 0.3)

    def exit(self) -> None:
        pass

    def add(self, b: Button) -> Button:
        self.buttons.append(b)
        return b

    def toast(self, text: str, color=(255, 230, 150), dur: float = 2.5) -> None:
        self.toasts.append([text, color, dur])

    # --- vstup ---------------------------------------------------------------------------------
    def handle(self, ev: Ev) -> None:
        if self.modal is not None:
            self.modal.handle(ev)
            if self.modal is not None and self.modal.closed:
                self.modal = None
            return
        if ev.type == "down":
            for b in reversed(self.buttons):
                if b.contains(ev.x, ev.y) and b.enabled:
                    b.pressed = True
                    self._pressed = b
                    return
            self.on_down(ev)
        elif ev.type == "up":
            b = self._pressed
            self._pressed = None
            if device.MOBILE:
                for bb in self.buttons:
                    bb.hover = False      # na dotyku žádný „hover“ po zvednutí prstu
            if b is not None:
                b.pressed = False
                if b.contains(ev.x, ev.y):
                    b.click()
                return
            self.on_up(ev)
        elif ev.type == "move":
            for b in self.buttons:
                b.hover = b.contains(ev.x, ev.y)
            self.on_move(ev)
        elif ev.type == "key":
            for b in self.buttons:
                if b.key is not None and ev.key == b.key and b.enabled and b.visible:
                    b.click()
                    return
            self.on_key(ev.key)
        elif ev.type == "wheel":
            self.on_wheel(ev)

    def on_down(self, ev: Ev) -> None:
        pass

    def on_up(self, ev: Ev) -> None:
        pass

    def on_move(self, ev: Ev) -> None:
        pass

    def on_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.back()

    def on_wheel(self, ev: Ev) -> None:
        pass

    def back(self) -> None:
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    # --- update/draw --------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.t += dt
        if self.modal is not None:
            self.modal.update(dt)
            if self.modal.closed:
                self.modal = None
        for tt in self.toasts:
            tt[2] -= dt
        self.toasts = [tt for tt in self.toasts if tt[2] > 0]

    def draw(self, surf) -> None:
        pass

    def draw_buttons(self, surf) -> None:
        for b in self.buttons:
            b.draw(surf, self.t)

    def draw_overlays(self, surf) -> None:
        font = assets.font
        y = self.toast_y
        down = y < H // 2          # nahoře se další toasty skládají dolů, dole nahoru
        for text, col, life in self.toasts[-4:]:
            a = 255 if life > 0.4 else int(255 * life / 0.4)
            w = min(W - 30, font.width(text, 2) + 30)
            r = pygame.Rect(0, 0, w, 40)
            r.center = (W // 2, y)
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            s.fill((20, 12, 24, int(a * 0.85)))
            surf.blit(s, r)
            font.draw(surf, text, r.center, col, 2, "center", alpha=a)
            y += 46 if down else -46
        if self.modal is not None:
            self.modal.draw(surf)


def draw_bg(surf, t: float, color=(40, 28, 48), stripes=(48, 34, 58), rays: bool = False) -> None:
    """Animované pozadí (výsledky) s hloubkou: dvě vrstvy pruhů v různé rychlosti (parallax), při výhře
    pomalé sluneční paprsky shora, vinětace. Kreslí se v art pixelech (1/3) a zvětšuje ×3."""
    from ..util import lerp_color
    aw, ah = W // 3, H // 3
    low = _BG_CACHE.get("low")
    if low is None:
        low = _BG_CACHE["low"] = pygame.Surface((aw, ah))
    low.fill(color)
    far = lerp_color(color, stripes, 0.5)
    off = (t * 2.5) % 48
    for i in range(-2, ah // 48 + 4):
        y = i * 48 + off
        pygame.draw.polygon(low, far, [(0, y), (aw, y - 40), (aw, y - 16), (0, y + 24)])
    if rays:
        cx, cy = aw // 2, 10
        ray = lerp_color(color, (255, 226, 140), 0.2)
        for i in range(10):
            a = t * 0.12 + i * math.tau / 10
            pygame.draw.polygon(low, ray, [(cx, cy), (cx + math.cos(a) * 400, cy + math.sin(a) * 400),
                                           (cx + math.cos(a + 0.2) * 400, cy + math.sin(a + 0.2) * 400)])
    off = (t * 7) % 22
    for i in range(-2, ah // 22 + 4):
        y = i * 22 + off
        pygame.draw.polygon(low, stripes, [(0, y), (aw, y - 40), (aw, y - 30), (0, y + 10)])
    pygame.transform.scale(low, (W, H), surf)
    vig = _BG_CACHE.get("vig")
    if vig is None:
        vig = _BG_CACHE["vig"] = _bg_vignette()
    for img, pos in vig:
        surf.blit(img, pos)


# --- sdílené pozadí obrazovek menu ------------------------------------------------------------
_BG_CACHE: dict = {}
_DIM_CACHE: dict = {}
BG_TILE = 48


def dim_layer(alpha: int, col=(10, 6, 14)) -> pygame.Surface:
    """Celoplošné ztmavení – jedna sdílená plocha místo alokace každý snímek."""
    key = (alpha, col)
    s = _DIM_CACHE.get(key)
    if s is None:
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((*col, alpha))
        _DIM_CACHE[key] = s
    return s


def _egg_pattern(color) -> pygame.Surface:
    """Pozadí o rozměru obrazovky + jedna dlaždice navíc: jemný vzor vajíček (pixel art 3 px) a pixelová vinětace."""
    from ..util import mul_color
    w, h = W + BG_TILE, H + BG_TILE
    s = pygame.Surface((w, h))
    s.fill(color)
    egg = [".##.", "####", "####", ".##."]
    light = mul_color(color, 1.16)
    dark = mul_color(color, 0.86)
    for ty in range(0, h // BG_TILE + 1):
        for tx in range(0, w // BG_TILE + 1):
            ox = tx * BG_TILE + (BG_TILE // 2 if ty & 1 else 0)
            oy = ty * BG_TILE
            for yy, row in enumerate(egg):
                for xx, ch in enumerate(row):
                    if ch == "#":
                        s.fill(light if yy < 2 else dark, (ox + 18 + xx * 3, oy + 16 + yy * 3, 3, 3))
    return s


def _bg_vignette() -> list:
    out = []
    col = (8, 4, 12)
    top = pygame.Surface((W, 120), pygame.SRCALPHA)
    for y in range(0, 120, 3):
        top.fill((*col, int(150 * (1 - y / 120) ** 2)), (0, y, W, 3))
    out.append((top, (0, 0)))
    out.append((pygame.transform.flip(top, False, True), (0, H - 120)))
    side = pygame.Surface((60, H), pygame.SRCALPHA)
    for x in range(0, 60, 3):
        side.fill((*col, int(110 * (1 - x / 60) ** 2)), (x, 0, 3, H))
    out.append((side, (0, 0)))
    out.append((pygame.transform.flip(side, True, False), (W - 60, 0)))
    return out


def draw_scene_bg(surf, t: float, color=(36, 26, 44)) -> None:
    """Pozadí obrazovek menu: pomalu ujíždějící vzor vajíček + vinětace. Jedna velká blit, žádné alokace."""
    bg = _BG_CACHE.get(color)
    if bg is None:
        bg = _BG_CACHE[color] = _egg_pattern(color)
    off = int(t * 9) % BG_TILE
    surf.blit(bg, (-off, -off))
    vig = _BG_CACHE.get("vig")
    if vig is None:
        vig = _BG_CACHE["vig"] = _bg_vignette()
    for img, pos in vig:
        surf.blit(img, pos)
