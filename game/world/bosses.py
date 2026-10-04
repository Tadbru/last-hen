"""Bossové – stavové automaty s telegrafovanými útoky a hláškami."""
from __future__ import annotations

import math

from .. import assets
from ..config import MAX_ENEMIES
from ..data.bosses import BOSSES, FINAL_VARIANTS
from ..data.waves import ENDLESS_ENRAGE
from ..gfx import pixelart as pa
from ..gfx.sprites import Anim
from .entities import EProj, Telegraph

TAU = math.tau


class BossCtrl:
    solid = False               # vytlačovat z překážek?
    def __init__(self, run, e, bdef) -> None:
        self.run = run
        self.e = e
        self.b = bdef
        self.name = bdef.name
        self.state = "intro"
        self.st = 1.2           # časovač stavu
        self.cd = 2.0
        self.vx = self.vy = 0.0
        self.invuln = 0.0
        self.quote_t = 6.0
        self.fight_t = 0.0
        self.enraged = False
        self.quotes = bdef.lines
        run.say(e, bdef.intro, 3.0)

    # --- pomocníci ----------------------------------------------------------------------
    @property
    def p(self):
        return self.run.player

    def to_player(self):
        e, p = self.e, self.p
        dx, dy = p.x - e.x, p.y - e.y
        d = math.hypot(dx, dy) or 1
        return dx / d, dy / d, d

    def move(self, vx: float, vy: float, dt: float) -> None:
        e = self.e
        if e.freeze_t > 0:
            vx *= 0.3
            vy *= 0.3
        if e.slow_t > 0:
            vx *= 1 - e.slow_f * 0.5
            vy *= 1 - e.slow_f * 0.5
        e.x += vx * dt
        e.y += vy * dt
        if self.solid:
            # menší bossové se o kulisy zastaví jako lišky (B-61); velcí je drtí schválně
            self.run.map.collide_circle(e, e.r * 0.8)
        if vx > 3:
            e.face = 0
        elif vx < -3:
            e.face = 1
        e.anim += dt * (2 + math.hypot(vx, vy) * 0.04)
        arena = self.run.arena
        if arena is not None:
            ax, ay, ar = arena
            dx, dy = e.x - ax, e.y - ay
            d = math.hypot(dx, dy)
            lim = ar - e.r
            if d > lim:
                e.x = ax + dx / d * lim
                e.y = ay + dy / d * lim

    def contact(self, mult: float = 1.0) -> None:
        e, p = self.e, self.p
        if (p.x - e.x) ** 2 + (p.y - e.y) ** 2 < (e.r + p.r) ** 2:
            p.take_damage(e.dmg * mult, e.x, e.y, "boss")

    def quote_pool(self) -> tuple:
        return self.quotes

    def maybe_quote(self, dt: float) -> None:
        self.quote_t -= dt
        pool = self.quote_pool()
        if self.quote_t <= 0 and pool:
            self.quote_t = self.run.rng.uniform(9, 15)
            self.run.say(self.e, self.run.rng.choice(pool), 2.4)

    def modify_damage(self, dmg: float) -> float:
        if self.invuln > 0 or self.state == "intro":
            return 0.0
        return dmg

    def update(self, dt: float) -> None:
        e = self.e
        if e.freeze_t > 0:
            e.freeze_t -= dt            # časovače zpomalení běží i když boss stojí (B-62)
        if e.slow_t > 0:
            e.slow_t -= dt
        self.fight_t += dt
        self.invuln = max(0.0, self.invuln - dt)
        if self.state == "intro":
            self.st -= dt
            if self.st <= 0:
                self.state = "fight"
            return
        self.maybe_quote(dt)
        self.tick(dt)

    def tick(self, dt: float) -> None:
        pass

    def on_death(self) -> None:
        run = self.run
        e = self.e
        run.say(e, self.b.death, 3.0, dead=True)
        run.boss_killed(self)


# ---------------------------------------------------------------------------------------
class SpyFox(BossCtrl):
    solid = True

    def _blink_target(self) -> tuple[float, float]:
        """Místo za hráčem, které není v překážce ani za plotem arény (B-61)."""
        run, p = self.run, self.p
        base = math.atan2(-p.dir_y, -p.dir_x)
        for da in (0.0, 0.6, -0.6, 1.2, -1.2, 1.9, -1.9, math.pi):
            a = base + da
            bx, by = p.x + math.cos(a) * 95, p.y + math.sin(a) * 95
            if run.map.blocked(bx, by, self.e.r * 0.8):
                continue
            if run.arena is not None:
                ax, ay, ar = run.arena
                if (bx - ax) ** 2 + (by - ay) ** 2 > (ar - self.e.r) ** 2:
                    continue
            return bx, by
        return self.e.x, self.e.y

    def tick(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        e.alpha = 255
        if self.state == "fight":
            self.move(nx * e.speed, ny * e.speed, dt)
            self.contact()
            self.cd -= dt
            if self.cd <= 0:
                self.state = "vanish"
                self.st = 0.35
                run.particles.puff(e.x, e.y, 14, (60, 60, 70), 80, 12)
                run.sfx("teleport", 0.6)
        elif self.state == "vanish":
            self.st -= dt
            e.alpha = 60
            self.invuln = 0.1
            if self.st <= 0:
                bx, by = self._blink_target()
                self.target = (bx, by)
                self.state = "warn"
                self.st = 0.65
                run.telegraphs.append(Telegraph("circle", bx, by, 34, 0.65, color=(255, 80, 80)))
                if run.rng.random() < 0.5:
                    run.say(e, "Za tebou!", 1.2)
        elif self.state == "warn":
            self.st -= dt
            e.alpha = 0
            self.invuln = 0.1
            if self.st <= 0:
                e.x, e.y = self.target
                run.particles.puff(e.x, e.y, 14, (60, 60, 70), 80, 12)
                self.state = "lunge"
                self.st = 0.42
                nx, ny, _ = self.to_player()
                self.vx, self.vy = nx * 430, ny * 430
        elif self.state == "lunge":
            self.st -= dt
            self.move(self.vx, self.vy, dt)
            self.contact(1.0)
            if self.st <= 0:
                self.state = "recover"
                self.st = 0.9
                # vějíř šipek – nejdřív varovné čáry, pak výstřel
                base = math.atan2(ny, nx)
                for i in range(-1, 2):
                    a = base + i * 0.25
                    run.telegraphs.append(Telegraph("line", e.x, e.y - 20, 0, 0.45, _fire_line(run, 260, 7, e.dmg * 0.7,
                                                    "feather", 1), x2=e.x + math.cos(a) * 360,
                                                    y2=e.y - 20 + math.sin(a) * 360, w=10, color=(255, 120, 80)))
        elif self.state == "recover":
            self.st -= dt
            self.move(nx * e.speed * 0.3, ny * e.speed * 0.3, dt)
            if self.st <= 0:
                self.state = "fight"
                self.cd = run.rng.uniform(2.8, 4.0) * (0.75 if e.hp < e.max_hp * 0.5 else 1.0)


class Rabbit(BossCtrl):
    solid = True

    def __init__(self, *a) -> None:
        super().__init__(*a)
        self.hop = 0.0

    def tick(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        frenzy = e.hp < e.max_hp * 0.5
        if self.state == "fight":
            self.hop -= dt
            if self.hop <= 0:
                self.hop = 0.55 if not frenzy else 0.4
                ang = math.atan2(ny, nx) + run.rng.uniform(-0.6, 0.6)
                sp = e.speed * (1.4 if frenzy else 1.0)
                self.vx, self.vy = math.cos(ang) * sp * 2.2, math.sin(ang) * sp * 2.2
                run.sfx("hop", 0.4)
            k = max(0.0, (self.hop - 0.2) / 0.35)
            self.move(self.vx * k, self.vy * k, dt)
            e.bob = math.sin(min(1.0, k) * math.pi) * 14
            self.contact()
            self.cd -= dt
            if self.cd <= 0:
                self.state = "aim"
                self.st = 0.7
                n = 7 if frenzy else 5
                base = math.atan2(ny, nx)
                self.lines = [base + (i - (n - 1) / 2) * 0.2 for i in range(n)]
                for a in self.lines:
                    run.telegraphs.append(Telegraph("line", e.x, e.y, 0, 0.7, x2=e.x + math.cos(a) * 520,
                                                    y2=e.y + math.sin(a) * 520, w=14, color=(255, 140, 40)))
                if run.rng.random() < 0.6:
                    run.say(e, "Mrkev do oka!", 1.4)
        elif self.state == "aim":
            self.st -= dt
            e.bob = 0
            if self.st <= 0:
                for a in self.lines:
                    run.eprojs.append(EProj(e.x, e.y, math.cos(a) * 420, math.sin(a) * 420, 9, e.dmg * 0.7, 1.6,
                                            assets.sprites.small["carrot"], 2))
                run.sfx("throw", 0.7)
                self.state = "fight"
                self.cd = 2.6 if frenzy else 3.6


class ZombieBear(BossCtrl):
    def tick(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        if self.state == "fight":
            self.move(nx * e.speed, ny * e.speed, dt)
            self.contact()
            self.cd -= dt
            if self.cd <= 0:
                self.state = "slam"
                self.st = 1.05
                r = 165
                run.telegraphs.append(Telegraph("circle", e.x, e.y, r, 1.05, self._slam, color=(255, 70, 50)))
                n = 6 if e.hp < e.max_hp * 0.5 else 4
                base = run.rng.uniform(0, TAU)
                for i in range(n):
                    a = base + i * TAU / n
                    run.telegraphs.append(Telegraph("line", e.x, e.y, 0, 1.25, self._crack,
                                                    x2=e.x + math.cos(a) * 480, y2=e.y + math.sin(a) * 480, w=30,
                                                    color=(200, 120, 60)))
                if run.rng.random() < 0.5:
                    run.say(e, "Zem se třese, kuře se klepe!", 1.6)
        elif self.state == "slam":
            self.st -= dt
            e.bob = -abs(math.sin(self.st * 6)) * 10
            if self.st <= 0:
                e.bob = 0
                self.state = "fight"
                self.cd = run.rng.uniform(4.0, 5.5)

    def _slam(self, tel) -> None:
        run = self.run
        run.sfx("stomp")
        run.shake(0.6)
        run.camera.vibrate(12)
        run.camera.haptic(60)
        p = run.player
        if (p.x - tel.x) ** 2 + (p.y - tel.y) ** 2 < (tel.r + p.r) ** 2:
            p.take_damage(self.e.dmg * 1.3, tel.x, tel.y, "boss-útok")
        run.add_ring(tel.x, tel.y, 20, tel.r * 1.15, 0.4, (255, 140, 90), 10)
        run.particles.puff(tel.x, tel.y, 18, (150, 120, 90), 160, 12)

    def _crack(self, tel) -> None:
        run = self.run
        p = run.player
        if _seg_dist(p.x, p.y, tel.x, tel.y, tel.x2, tel.y2) < tel.w / 2 + p.r:
            p.take_damage(self.e.dmg, tel.x, tel.y, "boss-útok")
        for i in range(8):
            t = i / 7
            run.particles.puff(tel.x + (tel.x2 - tel.x) * t, tel.y + (tel.y2 - tel.y) * t, 1, (120, 90, 60), 60, 10)
        run.add_beam([(tel.x, tel.y), (tel.x2, tel.y2)], tel.w * 0.6, 0.5, (90, 60, 40), "crack")


class WolfAlpha(BossCtrl):
    def __init__(self, *a) -> None:
        super().__init__(*a)
        self.howl = 3.0

    def tick(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        if self.state == "fight":
            self.move(nx * e.speed, ny * e.speed, dt)
            self.contact()
            self.howl -= dt
            if self.howl <= 0:
                self.howl = run.rng.uniform(6.5, 8.5)
                run.sfx("howl", 0.9)
                run.say(e, run.rng.choice(["Au-uuuuu!", "Smečko, k noze!", "Obklíčit kuře!"]), 1.6)
                p = self.p
                n = 6 if e.hp > e.max_hp * 0.5 else 9
                for i in range(n):
                    if len(run.enemies) >= MAX_ENEMIES:
                        break
                    a = i * TAU / n
                    # smečka přibíhá zpoza okraje obrazovky (elipsa kolem viditelné plochy)
                    run.spawn_enemy("wolf", p.x + math.cos(a) * 330, p.y + math.sin(a) * 540, summoned=True)
            self.cd -= dt
            if self.cd <= 0:
                self.state = "aim"
                self.st = 0.8
                self.dx, self.dy = nx, ny
                run.telegraphs.append(Telegraph("line", e.x, e.y, 0, 0.8, x2=e.x + nx * 440, y2=e.y + ny * 440,
                                                w=e.r * 2, color=(255, 60, 60)))
        elif self.state == "aim":
            self.st -= dt
            if self.st <= 0:
                self.state = "charge"
                self.st = 0.75
                run.sfx("roar", 0.5)
        elif self.state == "charge":
            self.st -= dt
            self.move(self.dx * 600, self.dy * 600, dt)
            self.contact(1.3)
            if run.tick % 3 == 0:
                run.particles.puff(e.x, e.y + 20, 1, (120, 120, 140), 30, 10)
            if self.st <= 0:
                self.state = "fight"
                self.cd = run.rng.uniform(3.2, 4.4)


class ZombieRooster(BossCtrl):
    """Finální boss – 3 fáze: (1) kokrhání odhání ke kraji arény, (2) déšť zombie slepic, (3) obří rychlá forma."""

    def __init__(self, run, e, bdef, variant: dict, hp_scale: float) -> None:
        super().__init__(run, e, bdef)
        self.variant = variant
        self.name = variant["name"]
        self.phase = 1
        total = e.max_hp
        ph = bdef.phase_hp
        self.thresholds = [total * (1 - ph[0]), total * (1 - ph[0] - ph[1])]
        self.wind = 0.0
        self.inhale = 0.0
        self.rain_t = 0.0
        self.small = e.spr
        self.big = run.boss_sprite("zombie_rooster_big", variant.get("tint"))
        self.base_r = e.r
        self.enrage_t = ENDLESS_ENRAGE if run.endless and run.director.night > 1 else 180.0     # (B-81)
        rl = variant.get("rain_line")
        if rl and len(bdef.lines) > 1:
            self.quotes = (bdef.lines[0], rl) + tuple(bdef.lines[2:])
        run.say(e, variant["quote"], 3.0)

    def quote_pool(self) -> tuple:
        # quotes = (kokrhání, hláška fáze 2, hláška fáze 3, obecná…) – fázové hlášky jen ve své fázi (B-76)
        q = self.quotes
        if len(q) < 3:
            return q
        return (q[0], q[self.phase - 1]) + tuple(q[3:]) if self.phase > 1 else (q[0],) + tuple(q[3:])

    def modify_damage(self, dmg: float) -> float:
        d = super().modify_damage(dmg)
        if self.state == "transition":
            return 0.0
        e = self.e
        # nepropadnout fází naráz
        if self.phase <= 2 and e.hp - d < self.thresholds[self.phase - 1]:
            d = max(0.0, e.hp - self.thresholds[self.phase - 1] + 1)
        return d

    def tick(self, dt: float) -> None:
        run, e = self.run, self.e
        if not self.enraged and self.fight_t > self.enrage_t:
            self.enraged = True
            e.dmg *= 1.5
            e.speed *= 1.3
            run.banner("KOHOUT ZUŘÍ!", (255, 60, 60), 2.0)
        if self.state == "transition":
            self.st -= dt
            e.bob = math.sin(self.st * 20) * 4
            self.invuln = 0.1
            if self.st <= 0:
                e.bob = 0
                self.state = "fight"
                self.cd = 1.5
            return
        # přechod fází
        if self.phase == 1 and e.hp <= self.thresholds[0] + 1:
            self._enter_phase(2)
            return
        if self.phase == 2 and e.hp <= self.thresholds[1] + 1:
            self._enter_phase(3)
            return
        if self.phase == 1:
            self._phase1(dt)
        elif self.phase == 2:
            self._phase2(dt)
        else:
            self._phase3(dt)

    def _enter_phase(self, ph: int) -> None:
        run, e = self.run, self.e
        self.phase = ph
        self.state = "transition"
        self.st = 1.6
        self.wind = 0.0
        self.inhale = 0.0
        self.e.bob = 0
        run.sfx("roar")
        run.shake(0.5)
        run.camera.vibrate(14)
        run.camera.haptic(70)
        line = self.quotes[1] if ph == 2 else self.quotes[2]
        run.say(e, line, 2.5)
        run.banner(f"FÁZE {ph}", (255, 120, 60), 1.5)
        if ph == 3:
            e.spr = self.big
            e.r = self.base_r * 1.5
            e.speed *= 1.9
            run.particles.feathers(e.x, e.y, 30, (170, 130, 150), 260)

    # fáze 1: kokrhání – vítr tlačí hráče ke kraji arény
    def _phase1(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        p = self.p
        if self.inhale > 0:
            # nádech před kokrháním – stojí, kruh varuje
            self.inhale -= dt
            e.bob = -abs(math.sin(self.inhale * 14)) * 4
            if self.inhale <= 0:
                e.bob = 0
                self.wind = WIND_TIME
                run.sfx("crow", 1.0)
                run.say(e, "KIKIRIKÍÍÍ!", 1.6)
                run.add_wave(e.x, e.y, 20, 210, 0.5, 0, None, color=(255, 120, 90), hurt_player=e.dmg * 0.6)
                run.shake(0.3)
            return
        if self.wind > 0:
            self.wind -= dt
            # vítr je pomalejší než nejpomalejší zvíře → proti němu se dá ujít; plynulý náběh
            push = (WIND_PUSH if not self.enraged else WIND_PUSH * 1.15) * (0.85 if run.director.quick else 1.0)
            push *= min(1.0, (WIND_TIME - self.wind) / 0.5)
            p.x += nx * push * dt
            p.y += ny * push * dt
            if run.tick % 2 == 0:
                run.particles.emit(e.x + run.rng.uniform(-30, 30), e.y - 30, nx * 420 + run.rng.uniform(-60, 60),
                                   ny * 420 + run.rng.uniform(-60, 60), 0.6, 0, (240, 240, 255), 3)
            if run.tick % 20 == 0:
                run.add_ring(e.x, e.y - 30, 20, 160, 0.4, (255, 220, 160), 5)
            self.move(nx * e.speed * 0.2, ny * e.speed * 0.2, dt)
            return
        self.move(nx * e.speed, ny * e.speed, dt)
        self.contact()
        self.cd -= dt
        if self.cd <= 0:
            self.cd = run.rng.uniform(5.5, 7.0)
            self.inhale = 0.8
            run.telegraphs.append(Telegraph("circle", e.x, e.y, 210, 0.8, color=(255, 150, 90)))

    # fáze 2: déšť zombie slepic
    def _phase2(self, dt: float) -> None:
        run, e = self.run, self.e
        p = self.p
        ax, ay, ar = run.arena or (p.x, p.y, 400)
        # krouží kolem středu arény
        t = self.fight_t * 0.6
        tx, ty = ax + math.cos(t) * ar * 0.55, ay + math.sin(t) * ar * 0.45
        dx, dy = tx - e.x, ty - e.y
        dd = math.hypot(dx, dy) or 1
        self.move(dx / dd * e.speed, dy / dd * e.speed, dt)
        e.bob = -18 + math.sin(self.fight_t * 3) * 6
        self.contact()
        self.rain_t -= dt
        if self.rain_t <= 0:
            self.rain_t = 0.45 if not self.enraged else 0.3
            for _ in range(2):
                a = run.rng.uniform(0, TAU)
                rr = run.rng.uniform(0, 170)
                x, y = p.x + math.cos(a) * rr, p.y + math.sin(a) * rr
                rain = self.variant.get("rain", "zchick")

                def fall(tel, rain=rain):
                    pp = run.player
                    if (pp.x - tel.x) ** 2 + (pp.y - tel.y) ** 2 < (tel.r + pp.r) ** 2:
                        pp.take_damage(e.dmg * 0.6, tel.x, tel.y, "déšť")
                    run.particles.puff(tel.x, tel.y, 5, (200, 220, 190), 80)
                    if len(run.enemies) < MAX_ENEMIES:
                        run.spawn_enemy(rain, tel.x, tel.y, summoned=True)
                run.telegraphs.append(Telegraph("drop", x, y, 24, 0.9, fall, color=(170, 255, 120), data=rain))
        self.cd -= dt
        if self.cd <= 0:
            self.cd = 3.0
            nx, ny, _ = self.to_player()
            base = math.atan2(ny, nx)
            for i in range(-3, 4):
                a = base + i * 0.18
                run.telegraphs.append(Telegraph("line", e.x, e.y - 30, 0, 0.55, _fire_line(run, 240, 9, e.dmg * 0.6,
                                                "egg", 3), x2=e.x + math.cos(a) * 420,
                                                y2=e.y - 30 + math.sin(a) * 420, w=12, color=(255, 200, 120)))
            run.sfx("throw", 0.6)

    # fáze 3: obří rychlá forma – nájezdy
    def _phase3(self, dt: float) -> None:
        run, e = self.run, self.e
        nx, ny, d = self.to_player()
        if self.state == "fight":
            self.move(nx * e.speed * 0.6, ny * e.speed * 0.6, dt)
            self.contact(1.2)
            self.cd -= dt
            if self.cd <= 0:
                self.state = "aim"
                self.st = 0.55 if not self.enraged else 0.4
                self.dx, self.dy = nx, ny
                run.telegraphs.append(Telegraph("line", e.x, e.y, 0, self.st, x2=e.x + nx * 520, y2=e.y + ny * 520,
                                                w=e.r * 2, color=(255, 50, 50)))
        elif self.state == "aim":
            self.st -= dt
            e.bob = math.sin(self.st * 40) * 3
            if self.st <= 0:
                e.bob = 0
                self.state = "charge"
                self.st = 0.7
                run.sfx("roar", 0.5)
        elif self.state == "charge":
            self.st -= dt
            self.move(self.dx * 640, self.dy * 640, dt)
            self.contact(1.4)
            if self.st <= 0:
                self.state = "fight"
                self.cd = run.rng.uniform(1.0, 1.6)
                run.add_wave(e.x, e.y, 20, 150, 0.35, 0, None, color=(255, 90, 90), hurt_player=e.dmg * 0.6)
                run.sfx("stomp", 0.8)
                run.shake(0.35)

    def on_death(self) -> None:
        if self.run.endless:
            # Nekonečná noc: slunce nevyjde ani po jeho pádu
            self.run.say(self.e, ENDLESS_DEATH, 3.0, dead=True)
            self.run.boss_killed(self)
            return
        super().on_death()


ENDLESS_DEATH = "Kikiri… kí… (a slunce pořád nikde)"
WIND_PUSH = 115.0     # px/s – pod rychlostí nejpomalejšího zvířete (husa ~132)
WIND_TIME = 2.6


def _fire_line(run, speed: float, r: float, dmg: float, sprite: str, kind: int):
    """Callback telegrafu „line“: vystřelí projektil z počátku čáry jejím směrem."""
    def cb(tel):
        dx, dy = tel.x2 - tel.x, tel.y2 - tel.y
        d = math.hypot(dx, dy) or 1.0
        run.eprojs.append(EProj(tel.x, tel.y, dx / d * speed, dy / d * speed, r, dmg, 2.4,
                                assets.sprites.small[sprite], kind))
    return cb


def _seg_dist(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + dx * t), py - (y1 + dy * t))


CTRLS = {"spy_fox": SpyFox, "rabbit": Rabbit, "zombie_bear": ZombieBear, "wolf_alpha": WolfAlpha}


def make_boss_ctrl(run, e, boss_id: str, hp_scale: float = 1.0):
    bdef = BOSSES[boss_id]
    if boss_id == "zombie_rooster":
        variant = FINAL_VARIANTS.get(run.biome.id, FINAL_VARIANTS["farm"])
        return ZombieRooster(run, e, bdef, variant, hp_scale)
    return CTRLS[boss_id](run, e, bdef)


def tinted_anim(base: Anim, tint) -> Anim:
    frames = [pa.tint(f, tint, 0.55) for f in base.frames[0]]
    return Anim(frames)
