"""HUD během runu: XP bar, časovač do svítání, zabití, mince, zbraně, boss bar, ultimátka, joystick, bannery."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..data.passives import PASSIVES
from ..util import clamp, fmt_num, fmt_time, lerp_color, mul_color
from ..gfx.particles import blit_add, glow_sprite
from .widgets import Ghost, draw_bar

CROW_POS = (W - 74, H - 84)
CROW_R = 50
PAUSE_RECT = pygame.Rect(W - 70, 22, 62, 58)
SLOTS_BOTTOM = 162          # spodní okraj řádků zbraní a pasivek
BOSS_BAR_Y = 182            # první ukazatel bosse; další po BOSS_BAR_STEP
BOSS_BAR_STEP = 42
_ghosts: dict = {}          # id(boss ctrl) -> Ghost (bílá stopa ztraceného HP)
_clock = [0.0]


def world_top(run) -> int:
    """Nejvyšší y, od kterého je svět vidět – nad ním leží HUD (sloty, ukazatele bossů a „Fáze“)."""
    n = sum(1 for c in run.bosses if c.e.alive)
    return SLOTS_BOTTOM if n == 0 else BOSS_BAR_Y + BOSS_BAR_STEP * (n - 1) + 36


def draw_hud(surf, run, joy, t: float, debug: dict | None = None) -> None:
    font = assets.font
    icons = assets.icons
    dt = min(0.1, max(0.0, t - _clock[0]))
    _clock[0] = t
    # XP bar
    ratio = run.xp / run.xp_next if run.xp_next else 0
    draw_bar(surf, (4, 4, W - 8, 12), ratio, (80, 200, 255), back=(20, 30, 50))
    lv = f"Úr. {run.level}"
    font.draw(surf, lv, (8, 22), C_TEXT, 2, "topleft", outline=C_OUTLINE)
    px = 16 + font.width(lv, 2)
    if run.pending_levelups > 0 and run.state == "playing":
        # level-up čeká na další pauzu – ukázat, že karta nepropadla
        a = int(170 + 85 * math.sin(t * 8))
        txt = f"+{run.pending_levelups}"
        font.draw(surf, txt, (px, 22), C_GOLD, 2, "topleft", outline=C_OUTLINE, alpha=a)
        px += font.width(txt, 2) + 10
    if run.pending_chests and run.state == "playing":
        # sebraná bedna čeká na další pauzu (až 8 s) – dřív o ní hráč nevěděl (B-75)
        ci = icons.get("chest", 2)
        surf.blit(ci, (px, 20 - int(abs(math.sin(t * 5)) * 3)))
        if len(run.pending_chests) > 1:
            font.draw(surf, f"×{len(run.pending_chests)}", (px + ci.get_width() + 3, 22), C_GOLD, 2, "topleft",
                      outline=C_OUTLINE)
    # časovač
    if run.endless:
        # Nekonečná noc: čas, noc a rekord i během Kohouta – dřív je přepsalo „BOSS!“ a runy končí právě tam (B-83)
        font.draw(surf, fmt_time(run.time), (W // 2, 22), C_TEXT, 4, "midtop", outline=C_OUTLINE)
        rec = run.cfg.record
        boss = "BOSS! · " if run.final_boss is not None else ""
        if rec and run.time > rec:
            a = int(190 + 65 * math.sin(t * 6))
            font.draw(surf, f"{boss}NOVÝ REKORD!", (W // 2, 60), C_GOLD, 2, "midtop", outline=C_OUTLINE, alpha=a)
        else:
            # první run na mapě a obtížnosti: rekord teprve vzniká (B-85)
            info = f"{boss}Noc {run.director.night} · " + (f"rekord {fmt_time(rec)}" if rec else "první rekord")
            col = (255, 110, 100) if boss else (200, 180, 240)
            font.draw(surf, info, (W // 2, 60), col, 2, "midtop", outline=C_OUTLINE)
    elif run.final_boss is not None:
        font.draw(surf, "BOSS!", (W // 2, 22), (255, 90, 80), 4, "midtop", outline=C_OUTLINE)
    elif run.cfg.mode == "bossrush":
        font.draw(surf, fmt_time(run.time), (W // 2, 22), C_TEXT, 4, "midtop", outline=C_OUTLINE)
    else:
        remain = max(0.0, run.final_time - run.time)
        col = C_TEXT if remain > 20 else (255, 200, 90)
        font.draw(surf, fmt_time(remain), (W // 2, 22), col, 4, "midtop", outline=C_OUTLINE)
        # slunce – postup k úsvitu
        k = clamp(run.time / max(1, run.final_time), 0, 1)
        bx, bw = W // 2 - 70, 140
        pygame.draw.rect(surf, (30, 20, 40), (bx, 66, bw, 6))
        pygame.draw.rect(surf, (255, 170, 60), (bx, 66, int(bw * k), 6))
        sx = bx + int(bw * k)
        pygame.draw.circle(surf, (255, 220, 90), (sx, 69), 6)
        pygame.draw.circle(surf, C_OUTLINE, (sx, 69), 6, 1)
    # zabití a mince
    sk = icons.get("skull", 2)
    kx = W - 82
    font.draw(surf, fmt_num(run.kills), (kx, 30), C_TEXT, 2, "topright", outline=C_OUTLINE)
    surf.blit(sk, (kx - font.width(fmt_num(run.kills), 2) - sk.get_width() - 8, 30))
    ci = icons.get("coin", 2)
    surf.blit(ci, (8, 52))
    font.draw(surf, str(run.coins), (8 + ci.get_width() + 4, 50), C_GOLD, 2, "topleft", outline=C_OUTLINE)
    # pauza
    pr = PAUSE_RECT
    pygame.draw.rect(surf, (20, 12, 24), pr.move(0, 3))
    pygame.draw.rect(surf, (60, 44, 68), pr)
    pygame.draw.rect(surf, C_OUTLINE, pr, 3)
    pi = icons.get("pause", 4)
    surf.blit(pi, pi.get_rect(center=pr.center))
    # zbraně a pasivky
    x0, y0 = 8, 82
    for i, w in enumerate(run.weapons):
        _slot(surf, x0 + i * 38, y0, w.d.icon, w.level, w.evolved)
    for i, (pid, lv) in enumerate(run.passives.items()):
        _slot(surf, x0 + i * 38, y0 + 40, PASSIVES[pid].icon, lv, False, maxlv=5)
    # boss bar
    yb = BOSS_BAR_Y
    for ctrl in run.bosses:
        e = ctrl.e
        if not e.alive:
            continue
        bw = W - 60
        g = _ghosts.get(id(ctrl))
        if g is None:
            if len(_ghosts) > 16:
                _ghosts.clear()
            g = _ghosts[id(ctrl)] = Ghost(e.hp / e.max_hp)
        draw_bar(surf, (30, yb, bw, 14), e.hp / e.max_hp, (220, 50, 60), back=(50, 20, 30),
                 ghost=g.update(e.hp / e.max_hp, dt))
        if ctrl.enraged:
            pygame.draw.rect(surf, (255, 80, 60), (28, yb - 2, bw + 4, 18), 2)
        font.draw(surf, ctrl.name, (W // 2, yb - 4), (255, 220, 200), 2, "midbottom", outline=C_OUTLINE)
        if getattr(ctrl, "phase", 0):
            font.draw(surf, f"Fáze {ctrl.phase}/3", (W - 32, yb + 18), (255, 200, 180), 2, "topright", outline=C_OUTLINE)
        yb += BOSS_BAR_STEP
    # bannery
    by = H * 0.3
    for text, col, life, maxl in run.banners[-3:]:
        k = 1 - life / maxl
        sc = 4 if len(text) < 16 else 3
        a = 255 if life > 0.3 else int(255 * life / 0.3)
        pop = 1.0 + max(0.0, 0.25 - k) * 2
        font.draw(surf, text, (W // 2, by - (pop - 1) * 20), col, sc, "center", outline=C_OUTLINE, alpha=a)
        by += 46
    # ukazatele bossů mimo obrazovku
    _boss_arrows(surf, run, t)
    # ultimátka
    _crow_button(surf, run, t)
    # joystick
    if joy.alpha > 0.02:
        a = int(joy.alpha * 90)
        base = pygame.Surface((joy.RADIUS * 2 + 8, joy.RADIUS * 2 + 8), pygame.SRCALPHA)
        c = joy.RADIUS + 4
        pygame.draw.circle(base, (255, 255, 255, a), (c, c), joy.RADIUS, 3)
        pygame.draw.circle(base, (255, 255, 255, a // 3), (c, c), joy.RADIUS)
        surf.blit(base, (joy.ox - c, joy.oy - c))
        kx = joy.ox + joy.vx * joy.RADIUS
        ky = joy.oy + joy.vy * joy.RADIUS
        knob = pygame.Surface((56, 56), pygame.SRCALPHA)
        pygame.draw.circle(knob, (255, 255, 255, int(joy.alpha * 170)), (28, 28), 24)
        pygame.draw.circle(knob, (40, 30, 50, int(joy.alpha * 170)), (28, 28), 24, 3)
        surf.blit(knob, (kx - 28, ky - 28))
    if debug:
        y = 210
        for k, v in debug.items():
            font.draw(surf, f"{k}: {v}", (8, y), (180, 255, 180), 1, "topleft", outline=C_OUTLINE)
            y += 14


def _boss_arrows(surf, run, t: float) -> None:
    cam = run.camera
    for ctrl in run.bosses:
        e = ctrl.e
        if not e.alive or e.alpha < 128:
            continue
        sx, sy = e.x - cam.ox, e.y - cam.oy - 20
        if -10 < sx < W + 10 and -10 < sy < H + 10:
            continue
        cx, cy = W / 2, H / 2
        dx, dy = sx - cx, sy - cy
        m = 34
        k = min((W / 2 - m) / abs(dx) if dx else 1e9, (H / 2 - m - 60) / abs(dy) if dy else 1e9)
        ax, ay = cx + dx * k, cy + dy * k
        ang = math.atan2(dy, dx)
        pulse = 4 + 3 * math.sin(t * 8)
        tip = (ax + math.cos(ang) * (18 + pulse), ay + math.sin(ang) * (18 + pulse))
        l = (ax + math.cos(ang + 2.5) * 16, ay + math.sin(ang + 2.5) * 16)
        r = (ax + math.cos(ang - 2.5) * 16, ay + math.sin(ang - 2.5) * 16)
        pygame.draw.polygon(surf, C_OUTLINE, [tip, l, r])
        pygame.draw.polygon(surf, (255, 70, 60), [tip, l, r], 0)
        pygame.draw.polygon(surf, C_OUTLINE, [tip, l, r], 2)
        sk = assets.icons.get("skull", 3)
        surf.blit(sk, sk.get_rect(center=(ax - math.cos(ang) * 12, ay - math.sin(ang) * 12)))


def _slot(surf, x, y, icon, lv, evo, maxlv=8) -> None:
    pygame.draw.rect(surf, C_OUTLINE, (x, y, 36, 36))
    pygame.draw.rect(surf, (255, 200, 60) if evo else (60, 46, 66), (x + 2, y + 2, 32, 32))
    img = assets.icons.get(icon, 2, evo=False)
    surf.blit(img, img.get_rect(center=(x + 15, y + 15)))
    if not evo:
        assets.font.draw(surf, str(lv), (x + 37, y + 39), (255, 255, 255), 2, "bottomright", outline=C_OUTLINE)


def _crow_button(surf, run, t: float) -> None:
    """Tlačítko ultimátky: ikona a název ultimátky zvířete, oblouk nabití v její barvě, při plném nabití pulzuje."""
    cx, cy = CROW_POS
    r = CROW_R
    ult = run.ult
    ready = run.crow_ready
    col = ult.color
    if _btn["run"] != id(run):
        _btn["run"], _btn["used"] = id(run), run.crows_used
    elif _btn["used"] != run.crows_used:
        _btn["used"] = run.crows_used
        _btn["pop"] = t                       # právě použito → krátký „výstřel“ z tlačítka
    pop = t - _btn["pop"]
    pygame.draw.circle(surf, (14, 8, 18), (cx, cy + 5), r + 3)
    if ready:
        k = 0.5 + 0.5 * math.sin(t * 7)
        gl = glow_sprite(22, mul_color(col, 0.6), 0.6 + 0.4 * k)
        blit_add(surf, [(gl, (cx - gl.get_width() // 2, cy - gl.get_height() // 2))])
        pygame.draw.circle(surf, lerp_color(col, (255, 255, 255), 0.45), (cx, cy), int(r + 6 + 4 * k), 3)
    pygame.draw.circle(surf, C_OUTLINE, (cx, cy), r + 3)
    # připraveno: tmavší výplň v barvě ultimátky, ať ikona nesplývá (B-89); barva hlavně v záři, kroužku a nápisu
    pygame.draw.circle(surf, mul_color(col, 0.5) if ready else (70, 52, 76), (cx, cy), r)
    if ready:
        pygame.draw.circle(surf, col, (cx, cy), r - 2, 4)
        pygame.draw.circle(surf, lerp_color(col, (255, 255, 255), 0.5), (cx, cy), r - 6, 2)   # odlesk
    # nabití
    ch = run.crow_charge
    if ch > 0 and not ready:
        rect = pygame.Rect(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2)
        pygame.draw.arc(surf, col, rect, math.pi / 2, math.pi / 2 + math.tau * ch, 6)
    if 0 <= pop < 0.35:
        q = pop / 0.35
        pygame.draw.circle(surf, lerp_color((255, 255, 255), col, q), (cx, cy), int(r + 4 + 40 * q), max(1, int(6 * (1 - q))))
    icon = assets.icons.get(ult.icon, 5 if ready else 4)     # barevná i během nabíjení
    surf.blit(icon, icon.get_rect(center=(cx, cy - 2)))
    # jméno zvířete nad tlačítkem – čí ultimátka to je (zadání: „ikona a název zvířete“, B-98)
    assets.font.draw(surf, _short_name(run.char.name), (cx, cy - r - 8), run.char.color, 2, "midbottom",
                     outline=C_OUTLINE, alpha=255 if ready else 190)
    if ready:
        a = int(200 + 55 * math.sin(t * 7))
        assets.font.draw(surf, ult.short + "!", (cx, cy + r + 2), lerp_color(col, (255, 255, 255), 0.35), 2, "midtop",
                         outline=C_OUTLINE, alpha=a)
    else:
        assets.font.draw(surf, ult.short, (cx, cy + r + 2), (170, 160, 175), 2, "midtop", outline=C_OUTLINE)


_btn = {"run": 0, "used": 0, "pop": -9.0}


def _short_name(name: str) -> str:
    """„Slepice Božena“ → „Božena“, „Tajný tučňák“ → „Tučňák“."""
    w = name.split()[-1]
    return w[:1].upper() + w[1:]


def crow_hit(x: float, y: float) -> bool:
    return (x - CROW_POS[0]) ** 2 + (y - CROW_POS[1]) ** 2 <= (CROW_R + 10) ** 2
