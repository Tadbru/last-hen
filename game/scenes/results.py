"""Výsledky runu – statistiky, build, vejce, odemčení, rychlý restart, sdílení, mock reklama."""
from __future__ import annotations

import os

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..ui.widgets import Button, draw_icon_frame, draw_panel
from ..gfx.particles import FEATHER, ParticleSystem
from ..util import ease_out_back, ease_out_cubic, fmt_num, fmt_time
from .base import Dialog, Scene, draw_bg


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
        self.rewards = progression.compute_rewards(run)
        self.msgs = progression.apply_results(app.save, run, self.rewards)
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
                app.save["gold"] += 3
                app.save["tokens"] += 2
                self.msgs.insert(0, "Týdenní boss rush: +3 zlatá vejce, +2 žetony")
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
            path = make_share_image(self.run, self.victory)
            msg = device.share_image(path, share_text(self.run) + " #LastChicken")
            self.toast(msg, (150, 220, 255), 3.5)
            self.b_share.sub = "hotovo ✓"
            _ = os
        except Exception as e:  # noqa: BLE001
            self.toast(f"Sdílení selhalo: {e}", (255, 120, 120))

    def draw(self, surf) -> None:
        font = assets.font
        run = self.run
        draw_bg(surf, self.t, (50, 34, 40) if not self.victory else (60, 46, 30),
                (60, 40, 48) if not self.victory else (74, 58, 36), rays=self.victory)
        k = ease_out_back(min(1.0, self.t * 2.5))
        if self.victory:
            title, col = "VÍTĚZSTVÍ!", (255, 220, 90)
            sub = VICTORY_SUB.get("bossrush" if run.cfg.mode == "bossrush" else run.biome.id,
                                  "Slunce vyšlo. Lišky jsou poražené!")
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
            for ln in page:
                font.draw(surf, ln, (W // 2, y), (140, 255, 160), 2, "midtop", outline=C_OUTLINE)
                y += font.line_h(2)
            if len(pages) > 1:
                font.draw(surf, f"klepni pro další · {self._page % len(pages) + 1}/{len(pages)}",
                          (W // 2, self._msg_area.bottom + 4), (200, 190, 210), 2, "midbottom")
        self.draw_buttons(surf)
        self.draw_overlays(surf)
