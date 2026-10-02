"""Správce zvuku: SFX s rate-limitem a dynamická vrstvená hudba.

Když chybí numpy nebo audio zařízení, všechno tiše funguje jako no-op.
"""
from __future__ import annotations

import random
import time

import pygame

try:
    import numpy as np
    from . import synth
    HAVE_NUMPY = True
except Exception:  # pragma: no cover - prostředí bez numpy
    np = None
    synth = None
    HAVE_NUMPY = False

MUSIC_CHANNELS = 4

# minimální odstup opakování (s) – ochrana proti „kulometu“ zvuků
RATE = {
    "plop": 0.045, "hit": 0.05, "pickup": 0.035, "throw": 0.08, "explode": 0.07, "water": 0.06,
    "zap": 0.06, "bite": 0.07, "cluck": 2.5, "spit": 0.15, "helmet": 0.1, "wave": 0.1, "whip": 0.08,
    "shotgun": 0.1, "cloud": 0.25, "coin": 0.06, "freeze": 0.12, "stamp": 0.15, "hop": 0.12,
}
VARIANTS = {"plop": 3, "pickup": 3, "cluck": 3}


class Audio:
    def __init__(self, enabled: bool = True) -> None:
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music_vol = 0.6
        self.sfx_vol = 0.8
        self.music_on = True
        self.sfx_on = True
        self._last: dict[str, float] = {}
        self._themes: dict[str, list] = {}
        self._layer_vol = [0.0] * MUSIC_CHANNELS
        self._layer_target = [0.0] * MUSIC_CHANNELS
        self.current_theme: str | None = None
        self._channels: list = []
        self._stereo = False
        if not enabled or not HAVE_NUMPY:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(synth.SR, -16, 2, 512)
            freq, size, ch = pygame.mixer.get_init()
            if freq != synth.SR:
                synth.SR = freq
            self._stereo = ch >= 2
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(MUSIC_CHANNELS)
            self._channels = [pygame.mixer.Channel(i) for i in range(MUSIC_CHANNELS)]
            for name, arr in synth.sfx_library().items():
                self.sounds[name] = self._make(arr)
            self.ok = True
        except Exception as e:  # zařízení chybí – hrajeme potichu
            try:
                print("[audio] vypnuto:", e)
            except Exception:  # noqa: BLE001
                pass
            self.ok = False

    def _make(self, arr) -> pygame.mixer.Sound:
        a = np.clip(arr, -1, 1)
        pcm = (a * 32000).astype(np.int16)
        if self._stereo:
            pcm = np.ascontiguousarray(np.column_stack([pcm, pcm]))
        return pygame.sndarray.make_sound(pcm)

    # --- nastavení ------------------------------------------------------------
    def apply_settings(self, music_vol: float, sfx_vol: float, music_on: bool, sfx_on: bool) -> None:
        self.music_vol, self.sfx_vol = music_vol, sfx_vol
        self.music_on, self.sfx_on = music_on, sfx_on
        self._apply_layer_volumes()

    # --- SFX -------------------------------------------------------------------
    def play(self, name: str, vol: float = 1.0) -> None:
        if not self.ok or not self.sfx_on or self.sfx_vol <= 0:
            return
        now = time.perf_counter()
        rate = RATE.get(name, 0.03)
        if now - self._last.get(name, -9) < rate:
            return
        self._last[name] = now
        key = name
        if name in VARIANTS:
            key = f"{name}{random.randrange(VARIANTS[name])}"
        snd = self.sounds.get(key)
        if snd is None:
            return
        ch = pygame.mixer.find_channel()
        if ch is None:
            return
        ch.set_volume(min(1.0, vol * self.sfx_vol))
        ch.play(snd)

    # --- hudba -----------------------------------------------------------------
    def _theme_sounds(self, theme: str):
        if theme not in self._themes:
            spec = synth.THEMES.get(theme) or synth.THEMES["farm"]
            self._themes[theme] = [self._make(x) for x in synth.make_theme(spec)]
        return self._themes[theme]

    def prepare_theme(self, theme: str) -> None:
        if self.ok:
            self._theme_sounds(theme)

    def play_music(self, theme: str, intensity: float = 0.3) -> None:
        if not self.ok:
            return
        if theme == self.current_theme:
            self.set_intensity(intensity)
            return
        layers = self._theme_sounds(theme)
        self.current_theme = theme
        self.set_intensity(intensity, instant=True)
        for ch, snd in zip(self._channels, layers):
            ch.stop()
        for i, (ch, snd) in enumerate(zip(self._channels, layers)):
            ch.set_volume(self._vol_for(i))
            ch.play(snd, loops=-1, fade_ms=300)

    def stop_music(self) -> None:
        if not self.ok:
            return
        for ch in self._channels:
            ch.fadeout(300)
        self.current_theme = None

    def set_intensity(self, x: float, instant: bool = False, boss: bool = False) -> None:
        x = max(0.0, min(1.0, x))
        t = [1.0, 1.0 if x > 0.12 else 0.0, 1.0 if x > 0.35 else 0.25, 1.0 if (x > 0.7 or boss) else 0.0]
        self._layer_target = t
        if instant:
            self._layer_vol = list(t)
            self._apply_layer_volumes()

    def _vol_for(self, i: int) -> float:
        if not self.music_on:
            return 0.0
        return self._layer_vol[i] * self.music_vol * 0.7

    def _apply_layer_volumes(self) -> None:
        if not self.ok:
            return
        for i, ch in enumerate(self._channels):
            ch.set_volume(self._vol_for(i))

    def update(self, dt: float) -> None:
        if not self.ok:
            return
        changed = False
        for i in range(MUSIC_CHANNELS):
            v, t = self._layer_vol[i], self._layer_target[i]
            if abs(v - t) > 0.001:
                step = dt * 0.8
                self._layer_vol[i] = min(t, v + step) if t > v else max(t, v - step)
                changed = True
        if changed:
            self._apply_layer_volumes()


class NullAudio(Audio):
    def __init__(self) -> None:  # noqa: D401 - jednoduchý tichý stub
        super().__init__(enabled=False)
