"""Herní scéna – drží Run, renderer, HUD a overlaye."""
from __future__ import annotations

import random

import pygame

from .. import assets, progression
from ..config import Flags, H, W
from ..core.input import Joystick, keyboard_vector
from ..data.meta import CHALLENGE_BY_ID  # noqa: F401  (import kvůli sbírce v debug)
from ..ui import hud
from ..ui.overlays import ChestOverlay, LevelUpOverlay, PauseOverlay
from ..world.render import RunRenderer
from ..world.run import Run, RunConfig
from .base import Dialog, Scene


def build_config(app, character: str, biome: str, mode: str, difficulty: str = "normal",
                 modifiers: tuple = (), seed: int | None = None) -> RunConfig:
    save = app.save
    meta = dict(save["meta"])
    rerolls = 2 + meta.get("reroll", 0)
    bonus = 0
    if save["rubber_band"] and mode in ("quick", "full"):
        bonus = 1
    if mode == "bossrush":
        bonus = 8
    season = progression.season_for(None, save.settings.get("season", "auto"))
    skin = save["skin"].get(character)
    if not progression.skin_usable(save, skin):
        skin = None            # sezónní skin po skončení sezóny se nenosí
    return RunConfig(character=character, biome=biome, mode=mode, difficulty=difficulty,
                     seed=seed if seed is not None else random.randrange(1 << 30), modifiers=modifiers, meta=meta,
                     rerolls=rerolls, banishes=2, bonus_levels=bonus, skin=skin, season=season)


def replay_allowed(app, cfg: RunConfig) -> bool:
    """Smí se run zopakovat se stejným nastavením? Denní výzva zapůjčuje zvíře i mapu jen na jeden pokus."""
    s = app.save
    if cfg.mode == "daily":
        return False
    return (cfg.character in s["unlocked_chars"] and cfg.biome in s["unlocked_maps"]
            and cfg.difficulty in s["unlocked_diffs"])


class GameScene(Scene):
    music = None

    def __init__(self, app, cfg: RunConfig) -> None:
        super().__init__(app)
        self.cfg = cfg
        self.run = Run(cfg)
        self.run.show_damage = app.save.settings.get("damage_numbers", True)
        self.run.camera.shake_on = app.save.settings.get("screen_shake", True)
        self.run.camera.haptics = True
        self.run.flashes_on = app.save.settings.get("flashes", True)
        self.renderer = RunRenderer(self.run)
        self.joy = Joystick()
        self.overlay = None
        self.crow_pressed = False
        self.end_t = 0.0
        self.death_prompted = False
        self.finished = False
        self.hint_t = 0.0 if app.save["seen_intro"] else 7.0
        if app.save["rubber_band"] and cfg.bonus_levels:
            app.save["rubber_band"] = False
            self.run.banner("Bonus na rozjezd: +1 úroveň!", (120, 255, 140), 2.5)

    def enter(self) -> None:
        if assets.audio:
            assets.audio.play_music(self.run.biome.music, 0.2)

    # --- vstup ---------------------------------------------------------------------------------
    def handle(self, ev) -> None:
        if self.modal is not None:
            super().handle(ev)
            return
        if self.overlay is not None:
            self.overlay.handle(ev)
            return
        if ev.type == "down":
            if hud.PAUSE_RECT.collidepoint(ev.x, ev.y):
                self.pause()
                return
            if hud.crow_hit(ev.x, ev.y):
                self.crow_pressed = True
                return
            if self.joy.allowed_start(ev.x, ev.y):
                self.joy.press(ev.x, ev.y)
        elif ev.type == "move":
            if self.app.mouse_down:
                self.joy.move(ev.x, ev.y)
        elif ev.type == "up":
            self.joy.release()
        elif ev.type == "key":
            self.on_key(ev.key)

    def on_key(self, key: int) -> None:
        run = self.run
        if key == pygame.K_SPACE:
            self.crow_pressed = True
        elif key in (pygame.K_ESCAPE, pygame.K_p):
            self.pause()
        elif self.app.debug or Flags.debug:
            if key == pygame.K_F5:
                order = [b for b in ("spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster")
                         if b not in run.bosses_killed and all(c.e.state != b for c in run.bosses)]
                if order:
                    run.spawn_boss(order[0])
            elif key == pygame.K_F6:
                run.pending_levelups += 1
            elif key == pygame.K_F7:
                for e in list(run.enemies):
                    if not e.boss:
                        run.damage_enemy(e, 1e9, None, crit=False)
            elif key == pygame.K_F8:
                run.god = not run.god
                run.banner("GOD MODE" if run.god else "god mode off", (255, 255, 0), 1.0)
            elif key == pygame.K_F9:
                from ..data.weapons import WEAPONS
                for w in run.weapons:
                    if not w.evolved:
                        w.set_level(8)
                        pas = WEAPONS[w.id].evo_passive
                        if pas and pas not in run.passives:
                            run.add_passive(pas, 1)
                run.pending_chests.append("elite")
            elif key == pygame.K_F10:
                run.time += 60

    def pause(self) -> None:
        if self.overlay is None and self.run.state == "playing":
            self.overlay = PauseOverlay(self)
            self.run.state = "paused"
            self.joy.release()

    def give_up(self) -> None:
        self.run.gave_up = True
        self.run.state = "dead"
        self.run.revived = True
        self.death_prompted = True
        self._finish()

    def restart(self) -> None:
        if not replay_allowed(self.app, self.cfg):
            # denní výzva / zapůjčené zvíře či mapa → zpět na výběr (žádné obcházení odemykání)
            from .select import SelectScene
            self.app.switch(SelectScene(self.app))
            return
        cfg = build_config(self.app, self.cfg.character, self.cfg.biome, self.cfg.mode, self.cfg.difficulty,
                           self.cfg.modifiers)
        self.app.switch(GameScene(self.app, cfg))

    # --- update --------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        super().update(dt)
        run = self.run
        self.joy.update(dt)
        if self.overlay is not None:
            self.overlay.update(dt)
            if self.overlay.done:
                if isinstance(self.overlay, PauseOverlay) and run.state == "paused":
                    run.state = "playing"
                self.overlay = None
        kx, ky = keyboard_vector()
        mx, my = self.joy.vx + kx, self.joy.vy + ky
        crow = self.crow_pressed
        self.crow_pressed = False
        if self.modal is None:
            run.update(dt, mx, my, crow)
        # přechody stavů → overlaye
        if run.state == "levelup" and not isinstance(self.overlay, LevelUpOverlay):
            self.overlay = LevelUpOverlay(self)
            self.joy.release()
        elif run.state == "chest" and not isinstance(self.overlay, ChestOverlay):
            self.overlay = ChestOverlay(self)
            self.joy.release()
        elif run.state == "playing" and isinstance(self.overlay, (LevelUpOverlay, ChestOverlay)):
            self.overlay = None
        if run.state == "dead" and not self.death_prompted and self.modal is None:
            self.death_prompted = True
            self.joy.release()
            if not run.revived and self.cfg.mode != "daily":
                self.modal = Dialog("Konec?", "Slepice padla… Podívej se na reklamu a vstaň z popela!",
                                    [("Oživ se (reklama)", self._ad_revive, "green"), ("Vzdát to", self._finish, "danger")],
                                    icon="heart")
            else:
                self._finish()
        if run.state == "victory" and not self.finished:
            self.end_t += dt
            if self.end_t > 0.5:
                self._finish()
        if assets.audio:
            assets.audio.set_intensity(run.intensity, boss=bool(run.bosses))
        if self.hint_t > 0:
            self.hint_t -= dt
            if self.hint_t <= 0 and not self.app.save["seen_intro"]:
                self.app.save["seen_intro"] = True
                self.app.save.save()

    def _ad_revive(self) -> None:
        def done():
            self.run.revive()
            self.death_prompted = False
        self.modal = Dialog("Kukuřice™", "Nejkřupavější kukuřice v okrese. Teď s 0 % lišek!", timer=3.0,
                            on_done=done, ad=True)

    def _finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        from .results import ResultsScene
        self.app.switch(ResultsScene(self.app, self.run))

    # --- draw ----------------------------------------------------------------------------------
    def draw(self, surf) -> None:
        self.renderer.draw(surf, 1 / 60)
        dbg = None
        if self.app.debug:
            run = self.run
            dbg = {"nepřátelé": len(run.enemies), "projektily": len(run.projs), "částice": len(run.particles),
                   "pickupy": len(run.pickups), "spojenci": len(run.allies), "buňky": len(run.grid.cells),
                   "čas": f"{run.time:.1f}", "god": run.god}
            self._debug_grid(surf)
        if self.run.state not in ("dead", "victory") or self.modal is not None:
            hud.draw_hud(surf, self.run, self.joy, self.t, dbg)
        if self.hint_t > 0 and self.overlay is None and self.run.state == "playing":
            self._hint(surf)
        if self.overlay is not None:
            self.overlay.draw(surf)
        self.draw_overlays(surf)

    def _hint(self, surf) -> None:
        font = assets.font
        a = int(255 * min(1.0, self.hint_t / 0.6))
        box = pygame.Surface((W - 40, 150), pygame.SRCALPHA)
        box.fill((20, 12, 24, int(a * 0.8)))
        surf.blit(box, (20, H - 330))
        lines = ["Drž a táhni prstem/myší ve spodní části", "obrazovky (nebo WASD / šipky).",
                 "Slepice střílí sama!", "Mezerník / velké tlačítko = KOKRHÁNÍ"]
        for i, ln in enumerate(lines):
            col = (255, 230, 120) if i >= 2 else (240, 235, 245)
            font.draw(surf, ln, (W // 2, H - 318 + i * 32), col, 2, "midtop", alpha=a)

    def _debug_grid(self, surf) -> None:
        cam = self.run.camera
        cell = self.run.grid.cell
        ox, oy = cam.ox, cam.oy
        x0 = int(ox // cell) * cell
        y0 = int(oy // cell) * cell
        col = (60, 255, 120)
        for x in range(x0, int(ox + W) + cell, cell):
            pygame.draw.line(surf, col, (x - ox, 0), (x - ox, H), 1)
        for y in range(y0, int(oy + H) + cell, cell):
            pygame.draw.line(surf, col, (0, y - oy), (W, y - oy), 1)
