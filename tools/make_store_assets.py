"""Grafika pro Google Play do složky store/: ikona 512×512, feature graphic 1024×500 a 5 screenshotů
1080×1920 s popisky. Vše se generuje z hry (headless) – žádné externí assety.

    python tools/make_store_assets.py
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

OUT = os.path.join(ROOT, "store")

CAPTIONS = [
    ("menu", "Poslední slepice", "proti armádě zombie lišek"),
    ("busy", "Stovky lišek", "a výbuchy vajec"),
    ("levelup", "16 zbraní a evoluce", "každý run jiný build"),
    ("boss", "5 bossů", "a Zombie Kohout na konci noci"),
    ("victory", "Přežij do svítání!", "7 zvířat · 5 map · denní výzvy"),
]


def _steps(app, n: int) -> None:
    from game.config import DT
    for _ in range(n):
        app.step(DT)


def capture_states(app) -> dict[str, pygame.Surface]:
    """Projde hru a vrátí logické snímky 540×960 pro jednotlivé screenshoty."""
    from game import progression
    from game.scenes import menu
    from game.scenes.game import GameScene, build_config
    from game.scenes.results import ResultsScene

    shots: dict[str, pygame.Surface] = {}

    def grab(name: str) -> None:
        app.render()
        shots[name] = app.screen.copy()

    menu.MenuScene.suppress_login = True
    app.set_scene(menu.MenuScene(app))
    _steps(app, 50)
    grab("menu")

    gs = GameScene(app, build_config(app, "hen", "farm", "full", seed=2024))
    app.set_scene(gs)
    run = gs.run
    rng = random.Random(8)
    while run.time < 90:
        gs.joy.vx, gs.joy.vy = rng.uniform(-1, 1), rng.uniform(-1, 1)
        for _ in range(30):
            app.step(1 / 60)
            if run.state == "levelup":
                progression.apply_card(run, run.offer[0])
            elif run.state == "chest":
                run.resume()
            run.player.hp = run.player.stats.max_hp
    gs.joy.vx = gs.joy.vy = 0.0
    p = run.player
    for _ in range(140):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(140, 440)
        run.spawn_enemy(rng.choice(["fox", "fast_fox", "bat", "wolf", "armored_fox"]),
                        p.x + math.cos(a) * d, p.y + math.sin(a) * d * 1.4)
    _steps(app, 30)
    run.explosion(p.x + 110, p.y - 120, 90, 0, None, (255, 160, 60), big=True)
    run.explosion(p.x - 120, p.y + 90, 70, 0, None, (255, 214, 70))
    run.show_damage = False                 # skriptovaná zabití bez obřích čísel
    for e in list(run.enemies)[:20]:
        run.damage_enemy(e, e.hp + 1, None, crit=False)
    _steps(app, 11)
    run.show_damage = True
    run.player.hp = run.player.stats.max_hp
    grab("busy")

    run.pause_cd = 0
    run.pending_levelups += 1
    _steps(app, 40)
    grab("levelup")
    if run.offer:
        progression.apply_card(run, run.offer[0])
    _steps(app, 2)
    run.spawn_boss("zombie_rooster")
    _steps(app, 150)
    run.player.hp = run.player.stats.max_hp
    grab("boss")

    run.victory = True
    run.bosses_killed = ["spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster"]
    app.set_scene(ResultsScene(app, run))
    _steps(app, 150)
    grab("victory")
    return shots


def _backdrop(size: tuple[int, int]) -> pygame.Surface:
    """Noční pozadí s jemným vzorem vajíček (stejný styl jako menu hry)."""
    w, h = size
    s = pygame.Surface(size)
    for y in range(0, h, 6):
        k = y / h
        s.fill((int(30 + 30 * k), int(20 + 14 * k), int(56 + 10 * k)), (0, y, w, 6))
    for ty in range(0, h // 96 + 1):
        for tx in range(0, w // 96 + 1):
            ox = tx * 96 + (48 if ty & 1 else 0) + 36
            oy = ty * 96 + 30
            for yy, row in enumerate((".##.", "####", "####", ".##.")):
                for xx, ch in enumerate(row):
                    if ch == "#":
                        s.fill((60, 44, 84) if yy < 2 else (44, 32, 64), (ox + xx * 6, oy + yy * 6, 6, 6))
    return s


def make_screenshots(shots: dict[str, pygame.Surface], font) -> None:
    from game.config import C_GOLD, C_OUTLINE
    for i, (key, title, sub) in enumerate(CAPTIONS, 1):
        canvas = _backdrop((1080, 1920))
        font.draw(canvas, title, (540, 70), C_GOLD, 10, "midtop", outline=C_OUTLINE)
        font.draw(canvas, sub, (540, 200), (245, 236, 250), 5, "midtop", outline=C_OUTLINE)
        shot = pygame.transform.scale(shots[key], (864, 1536))       # 1,6× (bez vyhlazení = ostrý pixel art)
        frame = pygame.Rect(0, 0, 864 + 24, 1536 + 24)
        frame.midtop = (540, 320)
        pygame.draw.rect(canvas, (12, 8, 16), frame.move(0, 10))
        pygame.draw.rect(canvas, (24, 16, 28), frame)
        pygame.draw.rect(canvas, (255, 214, 70), frame, 4)
        canvas.blit(shot, (frame.x + 12, frame.y + 12))
        pygame.image.save(canvas, os.path.join(OUT, f"screenshot_{i}_{key}.png"))


def make_feature(bank, font) -> None:
    """Feature graphic 1024×500 – výřez 512×250 z noční krajiny menu (stejný styl jako hra), zvětšený 2×."""
    from game.config import C_GOLD, C_OUTLINE
    from game.gfx import pixelart as pa
    from game.scenes.menu import _menu_backdrop, _moon
    s = pygame.Surface((512, 250))
    s.blit(_menu_backdrop(), (0, 0), pygame.Rect(14, 236, 512, 250))
    rng = random.Random(3)
    for _ in range(30):
        s.fill((255, 250, 220), (rng.randrange(512) // 2 * 2, rng.randrange(90) // 2 * 2, 2, 2))
    moon = pygame.transform.scale(_moon(), (51, 51))
    s.blit(moon, (440, 14))
    font.draw(s, "LAST CHICKEN", (256, 16), C_GOLD, 5, "midtop", outline=C_OUTLINE)
    font.draw(s, "poslední slepice proti zombie liškám", (256, 76), (240, 230, 250), 1, "midtop", outline=C_OUTLINE)
    hen = pa.scale(bank.players["hen"].frames[0][0], 1.5)
    s.blit(pa.make_shadow(56, 12, 110), (228, 238))
    s.blit(hen, hen.get_rect(midbottom=(256, 246)))
    fox = bank.enemies["fox"].frames[1][0]
    for x, y in ((392, 249), (440, 247), (120, 249)):
        img = fox if x > 256 else pa.flip(fox)
        s.blit(img, img.get_rect(midbottom=(x, y)))
    pygame.image.save(pygame.transform.scale(s, (1024, 500)), os.path.join(OUT, "feature_graphic_1024x500.png"))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    from game import assets
    from game.app import App
    app = App(headless=True, persist=False)
    app.save["eggs"] = 3200
    app.save["gold"] = 6
    app.save["tokens"] = 2
    shots = capture_states(app)
    make_screenshots(shots, assets.font)
    make_feature(assets.sprites, assets.font)
    icon = os.path.join(ROOT, "app_assets", "icon.png")
    if os.path.exists(icon):
        img = pygame.image.load(icon)
        pygame.image.save(pygame.transform.scale(img, (512, 512)), os.path.join(OUT, "icon_512.png"))
    print("store/ hotovo:", ", ".join(sorted(os.listdir(OUT))))


if __name__ == "__main__":
    main()
