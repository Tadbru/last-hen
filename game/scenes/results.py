"""Výsledky runu – statistiky, build, vejce, odemčení, rychlý restart, sdílení, mock reklama."""
from __future__ import annotations

import math
import os
import random

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..data.meta import WEEKLY_RUSH_TOKENS
from ..ui.widgets import Button, draw_icon_frame, draw_panel
from ..gfx.particles import FEATHER, ParticleSystem
from ..util import ease_out_back, ease_out_cubic, fmt_num, fmt_time
from .base import Dialog, Scene


# Podtitul výhry podle mapy (B-64)
VICTORY_SUB = {
    "farm": "Slunce vyšlo. Farma je zachráněna!",
    "forest": "Slunce vyšlo. Les je zase v klidu!",
    "city": "Slunce vyšlo. Město je zachráněno!",
    "mountain": "Slunce vyšlo. Hory jsou zase klidné!",
    "factory": "Slunce vyšlo. Továrna je zavřená!",
    "bossrush": "Všech 5 bossů poraženo!",
}


class ResultsScene(Scene):
    music = "menu"

    def __init__(self, app, run) -> None:
        super().__init__(app)
        self.run = run
        self.victory = run.victory
        run._settle_chests()            # nevyzvednuté/neotevřené bedny → mince (B-50)
        self.rewards = progression.compute_rewards(run, app.save)
        # rekord Nekonečné noci se vede pro mapu a obtížnost (B-85)
        prev_best = progression.endless_record(app.save, run.biome.id, run.cfg.difficulty)
        self.msgs = progression.apply_results(app.save, run, self.rewards)
        self.new_record = run.cfg.mode == "endless" and int(run.time) > prev_best
        self.endless_best = max(prev_best, int(run.time))
        if self.new_record:
            where = f"{run.biome.short or run.biome.name}, {run.diff.name}"
            self.msgs.insert(0, f"Nový rekord Nekonečné noci ({where}): {fmt_time(run.time)}!")
        if run.chest_coins[0]:
            n, c = run.chest_coins
            self.msgs.insert(0, f"Neotevřené bedny ({n}): +{c} mincí")
        self.doubled = False
        self._page = 0
        self._page_t = 0.0
        self._pages_cache = None
        self.score = progression.score(run)
        if run.cfg.mode == "daily":
            d = app.save["daily"]
            # datum výzvy podle seedu runu – výsledek dohraný po půlnoci patří ke dni, kdy výzva začala,
            # a nezablokuje výzvu nového dne (last_played se nastavuje už při startu)
            day = progression.daily_date(run.cfg.seed)
            d["scores"].append({"date": day, "score": self.score, "char": run.char.id})
            d["scores"] = d["scores"][-40:]
            app.save["tokens"] += 1
            self.msgs.insert(0, "Denní výzva: +1 žeton")
            app.save.save()
        if run.cfg.mode == "bossrush" and run.victory:
            wk = progression.iso_week()
            w = app.save["weekly"]
            if w.get("last_claim_week") != wk:
                w["last_claim_week"] = wk
                app.save["tokens"] += WEEKLY_RUSH_TOKENS          # zlatá vejce jen za bosse a výzvy
                self.msgs.insert(0, f"Týdenní boss rush: +{WEEKLY_RUSH_TOKENS} žetony")
            w["best"] = max(w.get("best", 0), self.score)
            app.save.save()
        y = H - 250
        self.b_again = self.add(Button((30, y, W - 60, 84), "ZNOVU", self.again, icon="reroll", style="primary",
                                       scale=3, key=pygame.K_RETURN))
        self.b_ad = self.add(Button((30, y + 96, (W - 72) // 2, 70), "2× vejce", self.ad_double, icon="cur_egg",
                                    style="green", sub="reklama"))
        self.b_share = self.add(Button((42 + (W - 72) // 2, y + 96, (W - 72) // 2, 70), "Sdílet", self.share,
                                       icon="star", style="blue", sub="obrázek PNG"))
        self.add(Button((30, H - 72, W - 60, 60), "Menu", self.back, icon="back", style="secondary"))
        if run.cfg.mode == "daily":
            self.b_again.text = "VÝBĚR"
        self.fx = ParticleSystem(160)
        self._emit_t = 0.0
        assets.audio.play("victory" if self.victory else "coin")

    def _msg_pages(self, font, w: int, h: int) -> list[list[str]]:
        if getattr(self, "_pages_cache", None) is not None:
            return self._pages_cache
        per = max(1, h // font.line_h(2))
        pages: list[list[str]] = []
        cur: list[str] = []
        for m in self.msgs:
            lines = font.wrap(m, w, 2)
            if cur and len(cur) + len(lines) > per:
                pages.append(cur)
                cur = []
            cur.extend(lines[:per])
        if cur:
            pages.append(cur)
        self._pages_cache = pages
        return pages

    def on_up(self, ev) -> None:
        area = getattr(self, "_msg_area", None)
        if area is not None and area.collidepoint(ev.x, ev.y):
            self._page += 1
            self._page_t = 0.0

    def update(self, dt: float) -> None:
        super().update(dt)
        self._page_t += dt
        if self._page_t > 4.0:
            self._page_t = 0.0
            self._page += 1
        # konfety při výhře, pomalu padající peří při prohře
        self._emit_t -= dt
        if self._emit_t <= 0 and self.t < 12:
            rng = self.fx.rng
            if self.victory:
                self._emit_t = 0.05
                col = rng.choice(((255, 214, 70), (255, 120, 90), (120, 220, 255), (150, 255, 140), (255, 250, 240)))
                self.fx.emit(rng.uniform(0, W), -10, rng.uniform(-30, 30), rng.uniform(60, 140), 4.0, FEATHER, col)
            else:
                self._emit_t = 0.35
                self.fx.emit(rng.uniform(0, W), -10, rng.uniform(-20, 20), rng.uniform(20, 50), 6.0, FEATHER,
                             (240, 236, 228))
        self.fx.update(dt)

    def _count(self, delay: float, dur: float = 0.7) -> float:
        """Postup „napočítávání“ čísla (0 → 1) s prodlevou."""
        return ease_out_cubic(max(0.0, min(1.0, (self.t - delay) / dur)))

    def again(self) -> None:
        from .game import GameScene, build_config, replay_allowed
        c = self.run.cfg
        if not replay_allowed(self.app, c):
            from .select import SelectScene
            self.app.switch(SelectScene(self.app))
            return
        self.app.switch(GameScene(self.app, build_config(self.app, c.character, c.biome, c.mode, c.difficulty,
                                                         c.modifiers)))

    def ad_double(self) -> None:
        if self.doubled:
            return

        def done():
            self.doubled = True
            self.app.save["eggs"] += self.rewards["eggs"]
            self.app.save["records"]["total_eggs"] += self.rewards["eggs"]
            self.app.save.save()
            self.b_ad.enabled = False
            self.b_ad.sub = "zdvojeno!"
            assets.audio.play("gold")
            self.toast(f"+{fmt_num(self.rewards['eggs'])} vajec navíc!", C_GOLD)
        self.modal = Dialog("Kukuřice™", "Kukuřice, kterou milují i lišky. Ale nedostanou ji.", timer=3.0,
                            on_done=done, ad=True)

    def share(self) -> None:
        try:
            from .. import device
            from ..share import make_share_image, share_text
            path = make_share_image(self.run, self.victory, record=self.new_record)
            msg = device.share_image(path, share_text(self.run) + " #LastChicken")
            self.toast(msg, (150, 220, 255), 3.5)
            self.b_share.sub = "hotovo ✓"
            _ = os
        except Exception as e:  # noqa: BLE001
            self.toast(f"Sdílení selhalo: {e}", (255, 120, 120))

    def draw(self, surf) -> None:
        font = assets.font
        run = self.run
        _draw_backdrop(surf, self.t, self.victory)
        k = ease_out_back(min(1.0, self.t * 2.5))
        if self.victory:
            title, col = "VÍTĚZSTVÍ!", (255, 220, 90)
            sub = VICTORY_SUB.get("bossrush" if run.cfg.mode == "bossrush" else run.biome.id,
                                  "Slunce vyšlo. Lišky jsou poražené!")
        elif run.endless:
            if self.new_record:
                title, col = "REKORD!", C_GOLD
            else:
                title, col = ("PADLA!" if run.char.female else "PADL!"), (255, 110, 100)
            sub = f"Nekonečná noc: {run.director.night}. noc · rekord {fmt_time(self.endless_best)}"
        else:
            title, col = ("PADLA!" if run.char.female else "PADL!"), (255, 110, 100)
            sub = "Lišky tentokrát vyhrály. Příště!"
        self.fx.draw(surf, 0, 0)
        font.draw(surf, title, (W // 2, 20 + (1 - k) * -60), col, 7, "midtop", outline=C_OUTLINE)
        font.draw(surf, sub, (W // 2, 102), C_TEXT, 2, "midtop", outline=C_OUTLINE)
        # statistiky
        r = pygame.Rect(24, 138, W - 48, 172)
        draw_panel(surf, r, (52, 38, 60))
        img = assets.sprites.players[run.char.id].frames[0][int(self.t * 3) % 2]
        surf.blit(img, (r.x + 16, r.y + 18))
        c = [self._count(0.25 + i * 0.12) for i in range(5)]
        stats = [("Čas", fmt_time(run.time * c[0])), ("Zabití", fmt_num(run.kills * c[1])),
                 ("Úroveň", str(round(run.level * c[2]))), ("Bossové", str(round(len(run.bosses_killed) * c[3]))),
                 ("Skóre", fmt_num(self.score * c[4]))]
        x0 = r.x + 90
        for i, (a, b) in enumerate(stats):
            y = r.y + 14 + i * 30
            font.draw(surf, a, (x0, y), (200, 190, 210), 2, "topleft")
            font.draw(surf, b, (r.right - 18, y), (255, 245, 220), 2, "topright")
        # build
        y = r.bottom + 12
        n = len(run.weapons)
        for i, w in enumerate(run.weapons):
            draw_icon_frame(surf, (24 + i * 82, y, 72, 72), w.d.icon, evo=w.evolved, scale=4)
            font.draw(surf, "EVO" if w.evolved else f"{w.level}", (24 + i * 82 + 68, y + 70), C_GOLD, 2, "bottomright",
                      outline=C_OUTLINE)
        _ = n
        # vejce
        y += 86
        rr = pygame.Rect(24, y, W - 48, 176)
        draw_panel(surf, rr, (66, 50, 40))
        yy = rr.y + 12
        for name, val in self.rewards["lines"]:
            font.draw(surf, name, (rr.x + 16, yy), (220, 210, 200), 2, "topleft")
            font.draw(surf, f"+{fmt_num(val)}", (rr.x + 250, yy), (255, 245, 220), 2, "topright")
            yy += 22
        mult = self.rewards["mult"]
        egg = assets.icons.get("cur_egg", 4)
        total = int(self.rewards["eggs"] * (2 if self.doubled else 1) * self._count(0.9, 0.9))
        tx = rr.right - 16
        font.draw(surf, "Celkem", (tx, rr.y + 14), (220, 210, 200), 2, "topright")
        font.draw(surf, f"{fmt_num(total)}", (tx, rr.y + 40), C_GOLD, 4, "topright", outline=C_OUTLINE)
        surf.blit(egg, (tx - font.width(fmt_num(total), 4) - egg.get_width() - 10, rr.y + 46))
        if mult != 1:
            font.draw(surf, f"×{mult:.2f} bonus", (tx, rr.y + 92), (255, 200, 120), 2, "topright")
        if self.rewards["gold"]:
            g = assets.icons.get("cur_gold", 3)
            gx = tx - 70
            surf.blit(g, (gx, rr.bottom - 40))
            font.draw(surf, f"+{self.rewards['gold']}", (gx + g.get_width() + 6, rr.bottom - 38), C_GOLD, 2, "topleft")
        # zprávy (odemčení, výzvy) – po stránkách, ať se žádná neztratí
        self._msg_area = pygame.Rect(16, rr.bottom + 8, W - 32, self.b_again.rect.y - rr.bottom - 14)
        pages = self._msg_pages(font, self._msg_area.w, self._msg_area.h - 22)
        if pages:
            page = pages[self._page % len(pages)]
            y = self._msg_area.y
            # jemný tmavý podklad – zprávy čitelné i přes vycházející slunce
            bh = len(page) * font.line_h(2) + 10
            surf.blit(_msg_band(self._msg_area.w, bh), (self._msg_area.x, y - 5))
            for ln in page:
                font.draw(surf, ln, (W // 2, y), (140, 255, 160), 2, "midtop", outline=C_OUTLINE)
                y += font.line_h(2)
            if len(pages) > 1:
                font.draw(surf, f"klepni pro další · {self._page % len(pages) + 1}/{len(pages)}",
                          (W // 2, self._msg_area.bottom + 4), (200, 190, 210), 2, "midbottom")
        self.draw_buttons(surf)
        self.draw_overlays(surf)


# --- pozadí: klidná pixelová scéna (výhra = svítání, prohra = noc) -------------------------------------
_BD: dict = {}


def _mix(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _backdrop(victory: bool) -> pygame.Surface:
    """Statická scéna v art pixelech (180×320, zvětšeno ×3): obloha s ditherovaným přechodem, slunce/měsíc,
    hvězdy a tmavý kopec, na kterém leží tlačítka (kontrast)."""
    key = "v" if victory else "d"
    s = _BD.get(key)
    if s is not None:
        return s
    aw, ah = W // 3, H // 3
    low = pygame.Surface((aw, ah))
    horizon = 214
    if victory:
        stops = [(0, (34, 30, 74)), (90, (86, 56, 108)), (160, (190, 98, 102)), (horizon, (248, 166, 96))]
    else:
        stops = [(0, (12, 9, 26)), (120, (30, 20, 50)), (horizon, (62, 34, 62))]
    # řádek přechodu = jedna barva, nebo šachovnice dvou barev → fill + PixelArray místo set_at po pixelech
    # (dřív ~70 ms zadrhnutí při prvním zobrazení výsledků, B-79)
    pxa = pygame.PixelArray(low)
    for y in range(ah):
        for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
            if y0 <= y < y1 or (y >= y1 and (y1, c1) == stops[-1]):
                k = min(1.0, (y - y0) / max(1, y1 - y0))
                break
        steps = 6
        f = k * steps
        i = int(f)
        pxa[:, y] = low.map_rgb(_mix(c0, c1, min(1.0, i / steps)))
        if f - i > 0.5:
            pxa[(y + 1) & 1::2, y] = low.map_rgb(_mix(c0, c1, min(1.0, (i + 1) / steps)))
    del pxa
    rng = random.Random(7 if victory else 8)
    if victory:
        # napůl vyšlé slunce za kopcem
        cx, cy, r = aw // 2, horizon + 6, 26
        for yy in range(cy - r - 6, cy + 1):
            for xx in range(cx - r - 6, cx + r + 7):
                d = math.hypot(xx - cx, yy - cy)
                if 0 <= xx < aw and 0 <= yy < ah:
                    if d <= r:
                        low.set_at((xx, yy), (255, 236, 160) if d < r - 2 else (255, 214, 120))
                    elif d <= r + 5 and (xx + yy) & 1:
                        low.set_at((xx, yy), _mix(low.get_at((xx, yy))[:3], (255, 214, 140), 0.45))
    else:
        for _ in range(70):
            x, y = rng.randrange(aw), rng.randrange(150)
            low.set_at((x, y), (230, 224, 240) if rng.random() < 0.4 else (150, 140, 180))
    # tmavý kopec s nasvícenou hranou
    rim = (120, 70, 80) if victory else (70, 52, 84)
    body = [(52, 30, 50), (40, 24, 42), (30, 18, 34)] if victory else [(30, 22, 44), (24, 18, 36), (18, 13, 28)]
    for x in range(aw):
        top = int(horizon + 4 + 4 * math.sin(x * 0.045 + 0.6) + 2 * math.sin(x * 0.13))
        # sloupec kopce = 3 pásy po 30 px, na spodních 2 řádcích pásu šachovnicový přechod do dalšího
        low.fill(body[0], (x, top, 1, 30))
        low.fill(body[1], (x, top + 30, 1, 30))
        low.fill(body[2], (x, top + 60, 1, ah - top - 60))
        for band, dy in ((0, 28), (0, 29), (1, 58), (1, 59)):
            y = top + dy
            if y < ah and (x + y) & 1:
                low.set_at((x, y), body[band + 1])
        low.set_at((x, top), rim)
    s = pygame.transform.scale(low, (W, H))
    if not victory:
        from .menu import _moon
        s.blit(_moon(), (430, 40))
    _BD[key] = s
    return s


def _cloud(seed: int, victory: bool) -> pygame.Surface:
    key = ("c", seed, victory)
    s = _BD.get(key)
    if s is not None:
        return s
    rng = random.Random(seed)
    w, h = rng.randint(24, 38), rng.randint(7, 10)
    grid = [[False] * w for _ in range(h)]
    for _ in range(5):
        bx, by = rng.uniform(w * 0.2, w * 0.8), rng.uniform(h * 0.45, h * 0.7)
        rx, ry = rng.uniform(w * 0.18, w * 0.32), rng.uniform(h * 0.3, h * 0.5)
        for y in range(h):
            for x in range(w):
                if ((x + 0.5 - bx) / rx) ** 2 + ((y + 0.5 - by) / ry) ** 2 <= 1:
                    grid[y][x] = True
    for x in range(w):
        grid[h - 1][x] = grid[h - 2][x]        # plochý spodek mraku
    hi, mid, lo = ((255, 214, 196), (236, 160, 162), (176, 104, 124)) if victory else         ((84, 70, 112), (60, 48, 86), (42, 32, 64))
    low = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            if grid[y][x]:
                above = y == 0 or not grid[y - 1][x]
                below = y == h - 1 or not grid[y + 1][x]
                low.set_at((x, y), (*(hi if above else lo if below else mid), 255))
    s = _BD[key] = pygame.transform.scale(low, (w * 3, h * 3))
    return s


# (seed, y, rychlost px/s, počáteční x)
_CLOUDS = [(11, 96, 6.0, 40), (23, 210, 4.0, 300), (37, 470, 7.5, 120), (41, 610, 5.0, 420)]


def _draw_backdrop(surf, t: float, victory: bool) -> None:
    surf.blit(_backdrop(victory), (0, 0))
    for seed, y, sp, x0 in _CLOUDS:
        c = _cloud(seed, victory)
        span = W + c.get_width()
        x = int((x0 + t * sp) % span) - c.get_width()
        surf.blit(c, (x // 3 * 3, y))


def _msg_band(w: int, h: int) -> pygame.Surface:
    key = ("band", w, h)
    s = _BD.get(key)
    if s is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((16, 10, 26, 140), (3, 0, w - 6, h))
        s.fill((16, 10, 26, 140), (0, 3, 3, h - 6))
        s.fill((16, 10, 26, 140), (w - 3, 3, 3, h - 6))
        _BD[key] = s
    return s
