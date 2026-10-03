"""App – okno, letterbox škálování, fixní logický krok 60 Hz, přechody scén, crash handling."""
from __future__ import annotations

import os
import time
import traceback

import pygame

from . import assets, device
from .config import CRASH_LOG, DT, MAX_FRAME_SKIP, TITLE, H, W, Flags
from .save import SaveData
from .scenes.base import Ev


def safe_print(text: str) -> None:
    """Výpis, který nespadne na konzoli s omezeným kódováním (např. cp1250)."""
    try:
        print(text)
    except Exception:  # noqa: BLE001
        try:
            import sys
            enc = getattr(sys.stdout, "encoding", None) or "ascii"
            print(text.encode(enc, "replace").decode(enc, "replace"))
        except Exception:  # noqa: BLE001
            pass


def log_crash(exc: BaseException) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n{tb}")
    except OSError:
        pass
    return tb


_WINDOWSIZECHANGED = getattr(pygame, "WINDOWSIZECHANGED", -100)
_BACKGROUND_EVENTS = {getattr(pygame, n) for n in ("APP_WILLENTERBACKGROUND", "APP_DIDENTERBACKGROUND")
                      if hasattr(pygame, n)}
_FOREGROUND_EVENTS = {getattr(pygame, n) for n in ("APP_DIDENTERFOREGROUND",) if hasattr(pygame, n)}
_FOCUS_LOST_EVENTS = {getattr(pygame, n) for n in ("WINDOWFOCUSLOST", "WINDOWMINIMIZED") if hasattr(pygame, n)}


class App:
    def __init__(self, headless: bool = False, save_path: str | None = None, persist: bool = True) -> None:
        self.headless = headless
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.window = None
        self.win_size = (W, H)
        self._fullscreen = False
        self._open_window()
        self.screen = pygame.Surface((W, H))
        self.save = SaveData(save_path, persist) if save_path else SaveData(persist=persist)
        assets.init(headless_sim=False, audio_enabled=True)
        self.apply_settings()
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = None
        self._next = None
        self._fade = 0.0          # 0 = žádný, kladné = zatmívání ven, záporné = rozsvěcení
        self._fade_dir = 0
        self.fps = 0.0
        self.debug = Flags.debug
        self.frame_ms = 0.0
        self.mouse_down = False
        device.keep_screen_on()
        from .scenes.menu import MenuScene
        if Flags.quick:
            from .scenes.game import GameScene
            from .world.run import RunConfig
            self.set_scene(GameScene(self, RunConfig(character="hen", biome="farm", mode="quick")))
        else:
            self.set_scene(MenuScene(self))

    # --- okno -----------------------------------------------------------------------------------
    def _open_window(self) -> None:
        if self.headless:
            self.window = pygame.display.set_mode((W, H))
            self.win_size = (W, H)
            return
        if device.MOBILE:
            # Telefon: okno přes celý displej ve skutečném rozlišení, 540×960 škálujeme sami
            # (pygame.SCALED v pygame 2.1 na Androidu nefunguje – byl vidět jen roh obrazu).
            size = (0, 0)
            try:
                info = pygame.display.Info()
                if info.current_w > 0 and info.current_h > 0:
                    size = (info.current_w, info.current_h)
            except pygame.error:
                pass
            try:
                self.window = pygame.display.set_mode(size, pygame.FULLSCREEN)
            except pygame.error:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self._refresh_window()
            return
        try:
            info = pygame.display.Info()
            avail_h = max(480, info.current_h - 90)
            avail_w = max(270, info.current_w - 40)
        except pygame.error:
            avail_h, avail_w = H, W
        s = min(avail_h / H, avail_w / W, 1.25)
        size = (int(W * s), int(H * s))
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self._refresh_window()

    def toggle_fullscreen(self, on: bool | None = None) -> None:
        if self.headless or device.MOBILE:
            return
        self._fullscreen = (not self._fullscreen) if on is None else on
        try:
            if self._fullscreen:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self._open_window()
            self._refresh_window()
        except pygame.error:
            self._fullscreen = False

    def _refresh_window(self) -> None:
        """Po změně velikosti okna znovu načíst plochu displeje a rozměry."""
        surf = pygame.display.get_surface()
        if surf is not None:
            self.window = surf
        self.win_size = self.window.get_size()
        self._vp = None
        self._bars_dirty = True

    def viewport(self) -> tuple[int, int, int, int]:
        vp = getattr(self, "_vp", None)
        if vp is not None and vp[0] == self.win_size:
            return vp[1]
        ww, wh = self.win_size
        s = min(ww / W, wh / H)
        if device.MOBILE and s >= 1:
            # celočíselné zvětšení = ostrý pixel art (pokud nezmenší obraz o víc než 15 %)
            si = int(s)
            if si / s >= 0.85:
                s = si
        vw, vh = max(1, int(W * s)), max(1, int(H * s))
        res = ((ww - vw) // 2, (wh - vh) // 2, vw, vh)
        self._vp = (self.win_size, res)
        return res

    def to_logical(self, pos) -> tuple[float, float]:
        vx, vy, vw, vh = self.viewport()
        return (pos[0] - vx) * W / vw, (pos[1] - vy) * H / vh

    def apply_settings(self) -> None:
        st = self.save.settings
        if assets.audio:
            assets.audio.apply_settings(st["music_vol"], st["sfx_vol"], st["music_on"], st["sfx_on"])
        device.HAPTICS = bool(st.get("vibration", True))
        if st.get("fullscreen") and not self._fullscreen:
            self.toggle_fullscreen(True)

    # --- scény ----------------------------------------------------------------------------------
    def set_scene(self, scene) -> None:
        if self.scene is not None:
            try:
                self.scene.exit()
            except Exception:
                pass
        self.scene = scene
        scene.enter()

    def switch(self, scene, fade: bool = True) -> None:
        if not fade or self.headless:
            self.set_scene(scene)
            return
        self._next = scene
        self._fade_dir = 1

    # --- smyčka ---------------------------------------------------------------------------------
    def translate(self, e) -> Ev | None:
        t = e.type
        if t == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_down = True
            x, y = self.to_logical(e.pos)
            return Ev("down", x, y)
        if t == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_down = False
            x, y = self.to_logical(e.pos)
            return Ev("up", x, y)
        if t == pygame.MOUSEMOTION:
            x, y = self.to_logical(e.pos)
            return Ev("move", x, y)
        if t == pygame.MOUSEWHEEL:
            return Ev("wheel", dy=e.y)
        if t == pygame.KEYDOWN:
            key = e.key
            if key == getattr(pygame, "K_AC_BACK", -1):
                key = pygame.K_ESCAPE        # systémové tlačítko Zpět na Androidu
            return Ev("key", key=key)
        return None

    # --- životní cyklus na mobilu ------------------------------------------------------------------
    def on_background(self) -> None:
        """Aplikace jde do pozadí – uložit, pozastavit hru a zvuk."""
        try:
            self.save.save()
        except Exception:  # noqa: BLE001
            pass
        pause = getattr(self.scene, "pause", None)
        if callable(pause):
            pause()
        self.mouse_down = False
        try:
            pygame.mixer.pause()
        except pygame.error:
            pass

    def on_foreground(self) -> None:
        try:
            pygame.mixer.unpause()
        except pygame.error:
            pass

    def process_events(self) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
                continue
            if e.type in (pygame.VIDEORESIZE, _WINDOWSIZECHANGED):
                self._refresh_window()
                continue
            if e.type in _BACKGROUND_EVENTS:
                self.on_background()
                continue
            if e.type in _FOREGROUND_EVENTS:
                self.on_foreground()
                continue
            if e.type in _FOCUS_LOST_EVENTS and not self.headless:
                # PC: přepnutí do jiného okna / minimalizace → pauza (hudba hraje dál)
                pause = getattr(self.scene, "pause", None)
                if callable(pause):
                    pause()
                self.mouse_down = False
                continue
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F3:
                    self.debug = not self.debug
                    continue
                if e.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
            ev = self.translate(e)
            if ev is not None and self._fade_dir == 0:
                self.scene.handle(ev)

    def step(self, dt: float) -> None:
        self.scene.update(dt)
        if assets.audio:
            assets.audio.update(dt)
        if self._fade_dir == 1:
            self._fade += dt / 0.16
            if self._fade >= 1:
                self._fade = 1
                if self._next is not None:
                    self.set_scene(self._next)
                    self._next = None
                self._fade_dir = -1
        elif self._fade_dir == -1:
            self._fade -= dt / 0.16
            if self._fade <= 0:
                self._fade = 0
                self._fade_dir = 0

    def render(self) -> None:
        self.scene.draw(self.screen)
        if self._fade > 0:
            # wipe – černý pruh shora
            h = int(H * self._fade)
            pygame.draw.rect(self.screen, (14, 8, 18), (0, 0, W, h))
            pygame.draw.rect(self.screen, (234, 150, 40), (0, h - 6, W, 6))
        if self.debug:
            from .gfx import font as _f  # noqa: F401
            assets.font.draw(self.screen, f"FPS {self.fps:.0f}  {self.frame_ms:.1f} ms", (W - 6, H - 6),
                             (180, 255, 180), 1, "bottomright", outline=(0, 0, 0))
        elif self.save.settings.get("show_fps"):
            assets.font.draw(self.screen, f"{self.fps:.0f}", (W - 6, H - 6), (180, 255, 180), 1, "bottomright",
                             outline=(0, 0, 0))
        if self.headless:
            return
        vx, vy, vw, vh = self.viewport()
        if (vw, vh) == (W, H):
            self.window.blit(self.screen, (vx, vy))
        else:
            if (vx or vy) and getattr(self, "_bars_dirty", True):
                self.window.fill((0, 0, 0))
                self._bars_dirty = False
            try:
                # škálovat rovnou do výřezu displeje (bez alokace mezisurface každý frame)
                pygame.transform.scale(self.screen, (vw, vh), self.window.subsurface((vx, vy, vw, vh)))
            except (pygame.error, ValueError, TypeError):
                self.window.blit(pygame.transform.scale(self.screen, (vw, vh)), (vx, vy))
        pygame.display.flip()

    def safe(self, fn, *a) -> bool:
        try:
            fn(*a)
            return True
        except Exception as exc:  # noqa: BLE001 – vše logujeme a ukážeme přátelskou obrazovku
            tb = log_crash(exc)
            safe_print(tb)
            from .scenes.error import ErrorScene
            if isinstance(self.scene, ErrorScene):
                self.running = False
                return False
            self._fade = 0
            self._fade_dir = 0
            self._next = None
            self.scene = ErrorScene(self, tb)
            return False

    def run(self) -> None:
        acc = 0.0
        last = time.perf_counter()
        fps_t, fps_n = 0.0, 0
        while self.running:
            now = time.perf_counter()
            real = min(0.25, now - last)
            last = now
            self.safe(self.process_events)
            acc += real
            steps = 0
            while acc >= DT and steps < MAX_FRAME_SKIP:
                if not self.safe(self.step, DT):
                    break
                acc -= DT
                steps += 1
            if steps >= MAX_FRAME_SKIP:
                acc = 0.0
            t0 = time.perf_counter()
            self.safe(self.render)
            self.frame_ms = (time.perf_counter() - t0) * 1000 + 0.0
            fps_n += 1
            fps_t += real
            if fps_t >= 0.5:
                self.fps = fps_n / fps_t
                fps_t, fps_n = 0.0, 0
            self.clock.tick(60)
        try:
            self.save.save()
        except Exception:
            pass
        pygame.quit()
