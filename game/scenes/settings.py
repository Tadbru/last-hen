"""Nastavení – hlasitost, přepínače, sezónní téma, reset postupu."""
from __future__ import annotations

import pygame

from .. import assets, device
from ..config import C_OUTLINE, C_TEXT, W
from ..ui.widgets import Button, draw_bar, draw_panel
from .base import Dialog, Scene

SEASON_OPTS = [("auto", "Podle data"), ("off", "Vypnuto"), ("halloween", "Halloween"), ("christmas", "Vánoce"),
               ("easter", "Velikonoce")]


class SettingsScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.add(Button((10, 10, 70, 64), "", self.back, icon="back", style="dark"))
        st = self.save.settings
        y = 130
        self.vol_rows = []
        for key, label in (("music_vol", "Hudba"), ("sfx_vol", "Efekty")):
            self.add(Button((W - 170, y, 70, 64), "−", lambda k=key: self.vol(k, -0.1), scale=3))
            self.add(Button((W - 90, y, 70, 64), "+", lambda k=key: self.vol(k, 0.1), scale=3))
            self.vol_rows.append((key, label, y))
            y += 80
        self.toggles = []
        for key, label in (("music_on", "Hudba zapnutá"), ("sfx_on", "Zvuky zapnuté"),
                           ("damage_numbers", "Čísla poškození"), ("screen_shake", "Otřesy obrazovky"),
                           ("show_fps", "Ukazovat FPS"),
                           ("vibration", "Vibrace") if device.MOBILE else ("fullscreen", "Celá obrazovka")):
            b = self.add(Button((W - 190, y, 170, 64), "", lambda k=key: self.toggle(k), scale=2))
            self.toggles.append((key, label, y, b))
            y += 74
        self.b_season = self.add(Button((W - 250, y, 230, 64), "", self.cycle_season, scale=2))
        self.season_y = y
        y += 90
        self.add(Button((30, y, W - 60, 70), "Smazat postup", self.reset, icon="skull", style="danger"))
        self._sync()
        _ = st

    def _sync(self) -> None:
        st = self.save.settings
        for key, label, y, b in self.toggles:
            on = bool(st.get(key))
            b.text = "ZAP" if on else "VYP"
            b.style = "green" if on else "secondary"
        cur = st.get("season", "auto")
        self.b_season.text = dict(SEASON_OPTS).get(cur, "Podle data")

    def vol(self, key: str, d: float) -> None:
        st = self.save.settings
        st[key] = round(max(0.0, min(1.0, st[key] + d)), 2)
        self.app.apply_settings()
        self.save.save()
        if key == "sfx_vol":
            assets.audio.play("cluck")

    def toggle(self, key: str) -> None:
        st = self.save.settings
        st[key] = not st.get(key)
        if key == "fullscreen":
            self.app.toggle_fullscreen(st[key])
        if key == "vibration" and st[key]:
            device.vibrate(60)
        self.app.apply_settings()
        self.save.save()
        self._sync()

    def cycle_season(self) -> None:
        st = self.save.settings
        ids = [s[0] for s in SEASON_OPTS]
        cur = st.get("season", "auto")
        st["season"] = ids[(ids.index(cur) + 1) % len(ids)] if cur in ids else "auto"
        self.save.save()
        self._sync()

    def reset(self) -> None:
        def stage2():
            self.modal = Dialog("Opravdu?", "Poslední šance. Slepice zapomene úplně všechno.",
                                [("SMAZAT", self._do_reset, "danger"), ("Ne!", None, "primary")])
        self.modal = Dialog("Smazat postup?", "Přijdeš o vejce, odemčená zvířata, mapy i sbírku.",
                            [("Smazat", stage2, "danger"), ("Zpět", None, "secondary")])

    def _do_reset(self) -> None:
        self.save.reset()
        self.toast("Postup smazán. Nový začátek!", (255, 160, 140))
        self._sync()

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((34, 32, 42))
        font.draw(surf, "NASTAVENÍ", (W // 2, 18), (255, 220, 150), 5, "midtop", outline=C_OUTLINE)
        st = self.save.settings
        for key, label, y in self.vol_rows:
            draw_panel(surf, (16, y - 6, W - 32, 76), (52, 46, 62), shadow=False)
            font.draw(surf, label, (34, y + 8), C_TEXT, 2, "topleft")
            draw_bar(surf, (34, y + 40, W - 240, 12), st[key], (234, 150, 40))
            font.draw(surf, f"{int(st[key] * 100)} %", (W - 196, y + 8), (220, 210, 230), 2, "topright")
        for key, label, y, b in self.toggles:
            font.draw(surf, label, (34, y + 32), C_TEXT, 2, "midleft")
        font.draw(surf, "Sezónní téma", (34, self.season_y + 32), C_TEXT, 2, "midleft")
        tip = ("Tlačítko Zpět = pauza / návrat" if device.MOBILE
               else "F3 debug · F11 celá obrazovka · mezerník = kokrhání")
        font.draw(surf, tip, (W // 2, 930), (150, 140, 160), 1, "midtop")
        _ = pygame
        self.draw_buttons(surf)
        self.draw_overlays(surf)
