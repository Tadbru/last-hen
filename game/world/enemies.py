"""Aktualizace nepřátel – jediná rychlá smyčka (pohyb, AI, separace, překážky, kontakt)."""
from __future__ import annotations

import math

from .. import assets
from ..data.enemies import AI_BAT, AI_BERSERK, AI_CHASE, AI_NECRO, AI_SPIT
from .entities import EProj
from .mapgen import push_out

RECYCLE_D2 = 1150.0 * 1150.0


def update_enemies(run, dt: float) -> None:
    p = run.player
    px, py = p.x, p.y
    pr = p.r
    cells = run.grid.cells
    ogrid = run.map.ogrid
    tick = run.tick
    sqrt = math.sqrt
    sin = math.sin
    kdecay = math.exp(-dt * 9.0)
    arena = run.arena
    player_alive = not p.dead and run.state == "playing"
    slide_hit = p.char.special == "slide" and p.slide > 0.9
    for e in run.enemies:
        if not e.alive:
            continue
        e.t += dt
        if e.flash > 0:
            e.flash -= dt
        if e.flash_cd > 0:
            e.flash_cd -= dt
        if e.ctrl is not None:
            e.ctrl.update(dt)
            continue
        dx = px - e.x
        dy = py - e.y
        d2 = dx * dx + dy * dy
        if d2 > RECYCLE_D2 and not e.elite:
            run.recycle_enemy(e)
            continue
        d = sqrt(d2) or 0.001
        nx = dx / d
        ny = dy / d
        speed = e.speed
        if e.slow_t > 0:
            e.slow_t -= dt
            speed *= 1.0 - e.slow_f
            if e.slow_t <= 0:
                e.slow_f = 0.0
        vx = vy = 0.0
        frozen = False
        if e.freeze_t > 0:
            e.freeze_t -= dt
            frozen = True
        elif e.stun_t > 0:
            e.stun_t -= dt
            frozen = True
        elif e.hyp_t > 0:
            e.hyp_t -= dt
            a = e.t * 1.7 + e.id
            vx = math.cos(a) * speed * 0.5 - nx * speed * 0.3
            vy = sin(a) * speed * 0.5 - ny * speed * 0.3
        else:
            ai = e.ai
            if ai == AI_CHASE:
                vx = nx * speed
                vy = ny * speed
            elif ai == AI_BAT:
                w = sin(e.t * 5.0 + e.id) * 0.8
                vx = (nx - ny * w) * speed
                vy = (ny + nx * w) * speed
            elif ai == AI_SPIT:
                e.cd -= dt
                if d > 240:
                    vx, vy = nx * speed, ny * speed
                elif d < 150:
                    vx, vy = -nx * speed * 0.8, -ny * speed * 0.8
                else:
                    s = 1 if e.id & 1 else -1
                    vx, vy = -ny * speed * 0.6 * s, nx * speed * 0.6 * s
                if e.cd <= 0 and d < 340:
                    e.cd = run.rng.uniform(2.4, 3.4)
                    sp = 190.0
                    run.eprojs.append(EProj(e.x, e.y - 8, nx * sp, ny * sp, 9, e.dmg * 1.2, 2.5,
                                            assets.sprites.small["slime"], 0))
                    run.sfx("spit", 0.5)
                elif e.cd < 0.45:
                    e.flash = 0.05
            elif ai == AI_NECRO:
                e.cd -= dt
                if d > 260:
                    vx, vy = nx * speed, ny * speed
                elif d < 190:
                    vx, vy = -nx * speed, -ny * speed
                else:
                    vx, vy = -ny * speed * 0.5, nx * speed * 0.5
                if e.cd <= 0:
                    e.cd = 6.0
                    run.necro_raise(e)
            elif ai == AI_BERSERK:
                if not e.rage and e.hp < e.max_hp * 0.5:
                    e.rage = True
                    e.speed *= 1.8
                    e.dmg *= 1.3
                    e.spr = assets.sprites.enemies.get("bear_rage", e.spr)
                    run.sfx("roar", 0.7)
                    run.add_text(e.x, e.y - 50, "ZUŘÍ!", (255, 80, 60), 3, 1.0)
                    run.shake(0.2)
                vx, vy = nx * speed, ny * speed
        if e.kx != 0.0 or e.ky != 0.0:
            vx += e.kx
            vy += e.ky
            e.kx *= kdecay
            e.ky *= kdecay
            if -2 < e.kx < 2 and -2 < e.ky < 2:
                e.kx = e.ky = 0.0
        e.x += vx * dt
        e.y += vy * dt
        if not frozen:
            if vx > 4:
                e.face = 0
            elif vx < -4:
                e.face = 1
            e.anim += dt * (3.0 + speed * 0.06)
        # separace (rozloženo do 2 ticků)
        if (e.id + tick) & 1:
            lst = cells.get(e.cell)
            if lst is not None and len(lst) > 1:
                n = 0
                er = e.r
                for o in lst:
                    if o is e or o.ctrl is not None:
                        continue
                    ox = e.x - o.x
                    oy = e.y - o.y
                    rr = (er + o.r) * 0.75
                    dd = ox * ox + oy * oy
                    if 0.01 < dd < rr * rr:
                        dist = sqrt(dd)
                        push = (rr - dist) * 0.6
                        e.x += ox / dist * push
                        e.y += oy / dist * push
                    n += 1
                    if n >= 4:
                        break
        if not e.flyer:
            obs = ogrid.get(e.cell)
            if obs is not None:
                push_out(e, e.r * 0.8, obs)
        if arena is not None:
            ax, ay, ar = arena
            adx, ady = e.x - ax, e.y - ay
            ad2 = adx * adx + ady * ady
            lim = ar - e.r
            if ad2 > lim * lim:
                ad = sqrt(ad2)
                e.x = ax + adx / ad * lim
                e.y = ay + ady / ad * lim
        # kontakt s hráčem
        if player_alive:
            rr = e.r + pr
            if d2 < rr * rr and not frozen and e.hyp_t <= 0:
                p.take_damage(e.dmg, e.x, e.y, "kontakt")
            if slide_hit and d2 < (rr + 6) * (rr + 6) and e.touch_cd <= 0:
                e.touch_cd = 0.35
                # škáluje s HP nepřítele (jako kokrhání), jinak by pasivka od 3. minuty nic nedělala
                run.damage_enemy(e, 18 * p.stats.might + e.max_hp * (0.04 if e.elite else 0.15), None,
                                 -nx, -ny, 260)
        if e.touch_cd > 0:
            e.touch_cd -= dt
