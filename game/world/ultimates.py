"""Ultimátky – aktivace, zdroj poškození jedné aktivace a běžící efekty (čistá logika, bez renderu).

Přidání ultimátky: řádek v `data/ultimates.py` + funkce `@effect("id")` tady. Funkce dostane run, zdroj
poškození (`UltSource`) a parametry (už s bonusem evoluce). Dlouhé efekty jsou objekty v `run.ult_fx`
s metodou `update(run, dt) -> bool` (False = konec); kreslí je `world/ult_render.py` podle `kind`.
Herní náhoda jen z `run.rng`, vizuál z `run.particles` (vlastní RNG).
"""
from __future__ import annotations

import math

from .. import assets
from ..data import waves as WV
from ..data.enemies import ENEMIES
from ..data.ultimates import ULT_BOSS_CAP, ULT_NAME_GAP, UltDef
from .entities import M_LOB, P_COIN, P_GOLDEGG, P_XP, Pickup

TAU = math.tau
EFFECTS: dict = {}
LOG_MAX = 120               # kolik posledních aktivací si run pamatuje (měření, ladění)


def effect(uid: str):
    """Registr funkcí efektů: @effect("egg_rain") def egg_rain(run, src, s): …"""
    def deco(fn):
        EFFECTS[uid] = fn
        return fn
    return deco


class UltSource:
    """Zdroj poškození jedné aktivace. Chová se jako zbraň pro damage pipeline (`d.color`, `s`, `damage_dealt`,
    `kills`), hlídá strop poškození bossů a slouží k měření."""
    __slots__ = ("d", "run", "s", "damage_dealt", "kills", "boss_dmg", "boss_cap", "t0")

    def __init__(self, run, ud: UltDef, params: dict) -> None:
        self.d = ud
        self.run = run
        self.s = params
        self.damage_dealt = 0.0
        self.kills = 0
        self.boss_dmg: dict = {}
        self.boss_cap = ULT_BOSS_CAP
        self.t0 = run.time

    def cap_boss(self, e, dmg: float) -> float:
        """Bossovi ubere jedna aktivace nejvýš boss_cap jeho max. HP."""
        done = self.boss_dmg.get(e.id, 0.0)
        lim = e.max_hp * self.boss_cap - done
        if dmg > lim:
            dmg = max(0.0, lim)
        self.boss_dmg[e.id] = done + dmg
        return dmg

    def on_land(self, pr) -> None:
        """Dopad vajíčka slepice (projektil M_LOB nese callback v `data`)."""
        cb = pr.data
        pr.data = None
        if cb is not None:
            cb(pr)


def ult_params(run, ud: UltDef) -> dict:
    s = dict(ud.params)
    if ud.evo and run.weapon(ud.evo) is not None:
        s.update(ud.evo_params)
        s["evolved"] = True
    return s


def activate(run, ud: UltDef) -> UltSource:
    """Spustí ultimátku (nabití už odečetl Run.crow). Společná zpětná vazba + funkce efektu."""
    p = run.player
    s = ult_params(run, ud)
    src = UltSource(run, ud, s)
    run.ult_log.append(src)
    if len(run.ult_log) > LOG_MAX:
        del run.ult_log[0]
    EFFECTS[ud.id](run, src, s)
    if run.time - run.ult_name_t >= ULT_NAME_GAP:
        # název: poprvé velký banner, potom jen malý nápis u zvířete a nejvýš jednou za ULT_NAME_GAP – dřív měl
        # Elvis v pozdní hře banner na obrazovce třetinu času (B-94); výkřik zůstává u každého použití
        run.ult_name_t = run.time
        if not run.ult_named:
            run.ult_named = True
            run.banner(ud.name, ud.color, 1.5)
        else:
            run.add_text(p.x, p.y - 92, ud.name, ud.color, 2, 1.0)
    run.add_text(p.x, p.y - 60, ud.shout, ud.color, 4 if len(ud.shout) <= 10 else 3, 1.2)
    run.sfx(ud.sound, 1.0)
    run.shake(ud.shake, 0.6)
    run.camera.vibrate(12)
    if ud.slowmo and run.slowmo_t <= 0:
        run.slowmo_t = ud.slowmo           # krátké zpomalení přes stávající systém (MASAKR ho klidně přebije)
    fb = run.final_boss
    if fb is not None and isinstance(getattr(fb, "wind", None), float):
        # každá ultimátka přebije kokrhání Zombie Kohouta (dřív jen kokrhání)
        fb.wind = 0.0
        fb.inhale = 0.0
    return src


def update(run, dt: float) -> None:
    if run.ult_fx:
        run.ult_fx = [f for f in run.ult_fx if f.update(run, dt)]


def stop_all(run) -> None:
    """Smrt / vítězství: běžící efekty skončí (okouzlení a stavy nepřátel doběhnou samy)."""
    for f in run.ult_fx:
        f.stop(run)
    run.ult_fx = []


# --- pomocné ---------------------------------------------------------------------------------
def blast(run, src, x: float, y: float, r: float, flat: float, pct: float = 0.0, kb: float = 0.0, stun: float = 0.0,
          freeze: float = 0.0, slow: float = 0.0, slow_t: float = 1.2, crit: bool = False, exclude: set | None = None,
          flash: bool = True, elite_pct: float = 1.0) -> int:
    """Plošný zásah: pevné poškození + podíl max. HP (jen běžní nepřátelé a elity, ne bossové a sudy)."""
    n = 0
    for e in run.grid.query(x, y, r + 40):     # vlastní seznam – výbuch sudu uvnitř používá sdílený buffer
        if not e.alive:
            continue
        dx, dy = e.x - x, e.y - y
        rr = r + e.r
        if dx * dx + dy * dy >= rr * rr:
            continue
        if exclude is not None:
            if e.id in exclude:
                continue
            exclude.add(e.id)
        dmg = flat
        if pct and not e.boss and not e.prop:
            dmg += pct * e.max_hp * (elite_pct if e.elite else 1.0)
        run.damage_enemy(e, dmg, src, dx, dy, kb, crit, slow, slow_t, freeze, stun, flash=flash)
        n += 1
    return n


def fox_hp(run) -> float:
    """HP běžné lišky v tuto chvíli (měřítko pro poškození, které má stárnout s runem)."""
    em = run.director.eff_min()
    curve = WV.endless_hp_mult(em, run.director.night) if run.endless else WV.hp_mult(em)
    return ENEMIES["fox"].hp * curve * run.diff.hp * run.biome.hp_mult * run.mod_enemy_hp


def wipe_eprojs(run, x: float, y: float, r: float, col) -> None:
    for ep in run.eprojs:
        if ep.alive and (ep.x - x) ** 2 + (ep.y - y) ** 2 < r * r:
            ep.alive = False
            run.particles.sparks(ep.x, ep.y, 3, col, 100)


class Fx:
    kind = ""

    def update(self, run, dt: float) -> bool:
        return False

    def stop(self, run) -> None:
        pass


class Delayed(Fx):
    """Zavolá funkci po zpoždění (ozvěna KIKIRIKÍ)."""

    def __init__(self, delay: float, fn) -> None:
        self.t = delay
        self.fn = fn

    def update(self, run, dt: float) -> bool:
        self.t -= dt
        if self.t <= 0:
            self.fn(run)
            return False
        return True


# =============================================================================================
# Slepice Božena – Zlatá nadílka: cílený déšť zlatých vajec, zabité lišky dávají 2× XP
# =============================================================================================
class EggRain(Fx):
    kind = "egg_rain"

    def __init__(self, run, src, s) -> None:
        n = int(s["eggs"])
        self.src = src
        self.s = s
        self.times = [i * s["spread"] / n for i in range(n)]
        self.t = 0.0
        self.eggs: list = []            # letící vejce (pro značky dopadu v renderu)
        p = run.player
        # první vejce míří na nejbližší lišky (úleva hned), zbytek náhodně po okolí
        self.near = run.random_enemies(p.x, p.y, s["range"] * p.stats.area, int(s["near"]), nearest=True)

    def update(self, run, dt: float) -> bool:
        self.t += dt
        while self.times and self.times[0] <= self.t:
            self.times.pop(0)
            self._launch(run)
        self.eggs = [pr for pr in self.eggs if pr.alive and pr.src is self.src]
        return bool(self.times or self.eggs)

    def _launch(self, run) -> None:
        p = run.player
        s = self.s
        rng = run.rng
        reach = s["range"] * p.stats.area
        tgt = None
        while self.near and tgt is None:
            e = self.near.pop(0)
            if e.alive:
                tgt = [e]
        if tgt is None:
            tgt = run.random_enemies(p.x, p.y, reach, 1)
        if tgt:
            tx, ty = tgt[0].x + rng.uniform(-14, 14), tgt[0].y + rng.uniform(-14, 14)
        else:
            a = rng.uniform(0, TAU)
            d = rng.uniform(80, reach * 0.6)
            tx, ty = p.x + math.cos(a) * d, p.y + math.sin(a) * d
        pr = run.add_proj(p.x, p.y - 14, 0, 0, 8, 0.0, self.src, life=99, spr=assets.sprites.small["egg_gold"])
        if not pr.alive:
            return                      # strop projektilů – vejce propadne
        pr.motion = M_LOB
        pr.sx, pr.sy = p.x, p.y - 14
        pr.tx, pr.ty = tx, ty
        d = math.hypot(tx - p.x, ty - p.y)
        pr.dur = 0.55 + d / 900
        pr.height = 230 + d * 0.2       # vysoký oblouk – vejce „prší z nebe“
        pr.size = 1.4
        pr.data = self._land
        self.eggs.append(pr)
        run.particles.sparkle(p.x, p.y - 20, (255, 220, 90), 2)
        run.sfx("throw", 0.4)

    def _land(self, pr) -> None:
        run = self.src.run
        s = self.s
        st = run.player.stats
        r = s["radius"] * st.area
        x, y = pr.x, pr.y
        blast(run, self.src, x, y, r, s["dmg"] * st.might, s["hp_pct"], kb=s["kb"], stun=s["stun"])
        run.add_ring(x, y, r * 0.3, r, 0.3, (255, 214, 70), 6)
        run.particles.explosion(x, y, r, (255, 206, 64))
        run.particles.stars(x, y - 8, 4, (255, 230, 120), 150)
        run.particles.glow(x, y - 6, r * 0.8, (255, 200, 80), 0.16)
        run.sfx("explode", 0.6)
        run.shake(0.04, 0.3)


@effect("egg_rain")
def egg_rain(run, src, s) -> None:
    p = run.player
    run.ult_fx.append(EggRain(run, src, s))
    run.particles.burst_ring(p.x, p.y - 16, 14, (255, 214, 70), 230)
    run.particles.glow(p.x, p.y - 14, 60, (255, 200, 80), 0.25)
    run.add_ring(p.x, p.y, 10, 120, 0.4, (255, 230, 140), 6)


# =============================================================================================
# Kachna Kvak – Velká voda: směrová vlna unáší lišky, promočené zpomalí, na konci náraz
# =============================================================================================
class Flood(Fx):
    kind = "flood"

    def __init__(self, run, src, s) -> None:
        p = run.player
        dx, dy = p.dir_x, p.dir_y
        d = math.hypot(dx, dy) or 1.0
        self.dx, self.dy = dx / d, dy / d
        self.src = src
        self.s = s
        area = p.stats.area
        self.ox = p.x - self.dx * 40
        self.oy = p.y - self.dy * 40
        self.dist = 0.0
        self.len = s["length"] * area
        self.hw = s["half_w"] * area
        self.hit: set = set()
        self.carried: dict = {}
        self.t = 0.0

    @property
    def front(self) -> tuple[float, float]:
        return self.ox + self.dx * self.dist, self.oy + self.dy * self.dist

    def update(self, run, dt: float) -> bool:
        s = self.s
        st = run.player.stats
        self.t += dt
        prev = self.dist
        self.dist = min(self.len, self.dist + s["speed"] * dt)
        adv = self.dist - prev
        fx, fy = self.front
        dx, dy = self.dx, self.dy
        hw = self.hw
        flat = s["dmg"] * st.might
        for e in run.grid.query(fx, fy, hw + 70):
            if not e.alive or e.prop:
                continue
            rx, ry = e.x - self.ox, e.y - self.oy
            along = rx * dx + ry * dy
            perp = ry * dx - rx * dy
            if perp > hw + e.r or perp < -hw - e.r or along > self.dist + e.r or along < self.dist - 80:
                continue
            if e.id not in self.hit:
                self.hit.add(e.id)
                pct = 0.0 if e.boss else s["hp_pct"]
                run.damage_enemy(e, flat + pct * e.max_hp, self.src, dx, dy, 0.0, False, s["slow"], s["slow_t"])
                if run.particles.rng.random() < 0.5:
                    run.particles.drops(e.x, e.y - 8, 2)
            if e.boss or not e.alive:
                continue
            # unést s vlnou: lišku posunout k čelu vlny (elity jen zčásti)
            k = s["elite_carry"] if e.elite else 1.0
            gap = (self.dist - 22) - along
            if gap > 0:
                mv = min(gap, adv + 6) * k
                e.x += dx * mv
                e.y += dy * mv
            e.kx = e.ky = 0.0
            self.carried[e.id] = e
        # sliz v cestě vlny zhasne
        for ep in run.eprojs:
            if ep.alive:
                rx, ry = ep.x - self.ox, ep.y - self.oy
                along = rx * dx + ry * dy
                if self.dist - 80 < along < self.dist + 10 and abs(ry * dx - rx * dy) < hw:
                    ep.alive = False
                    run.particles.drops(ep.x, ep.y, 2, speed=80)
        if self.dist >= self.len:
            self._crash(run)
            return False
        return True

    def _crash(self, run) -> None:
        s = self.s
        st = run.player.stats
        fx, fy = self.front
        flat = s["crash"] * st.might
        for e in self.carried.values():
            if e.alive:
                run.damage_enemy(e, flat + s["crash_pct"] * e.max_hp, self.src, self.dx, self.dy, 120, False,
                                 stun=s["crash_stun"])
        run.add_ring(fx, fy, 20, self.hw * 0.8, 0.45, (150, 220, 255), 8)
        run.particles.drops(fx, fy, 16, speed=260, up=160)
        run.particles.glow(fx, fy, 60, (90, 170, 255), 0.2)
        run.sfx("water", 1.0)
        run.shake(0.12, 0.4)


@effect("flood")
def flood(run, src, s) -> None:
    p = run.player
    st = p.stats
    # rozstřik kolem kachny (místo kolem sebe) + vlna ve směru pohybu
    r = s["splash"] * st.area
    blast(run, src, p.x, p.y, r, s["splash_dmg"] * st.might, s["splash_pct"], kb=s["splash_kb"], stun=s["splash_stun"])
    run.add_ring(p.x, p.y, 16, r, 0.3, (150, 220, 255), 6)
    run.ult_fx.append(Flood(run, src, s))
    run.particles.drops(p.x, p.y - 10, 12, speed=200)
    run.particles.glow(p.x, p.y - 12, 54, (80, 170, 255), 0.22)
    run.add_ring(p.x, p.y, 10, 90, 0.35, (180, 230, 255), 6)


# =============================================================================================
# Husa Gerta – Husí řádění: nesmrtelnost, rychlost, kejhnutí rozhazují lišky, co srazí, zraní
# =============================================================================================
class GooseFury(Fx):
    kind = "goose_fury"

    def __init__(self, run, src, s) -> None:
        self.src = src
        self.s = s
        self.t = 0.0
        self.dur = s["dur"]
        self.next_pulse = 0.0
        self.trampled: dict = {}
        p = run.player
        p.invuln = max(p.invuln, self.dur)
        p.ult_speed = s["speed"]
        p.ult_aura = 1.0

    def update(self, run, dt: float) -> bool:
        p = run.player
        s = self.s
        st = p.stats
        self.t += dt
        p.ult_aura = max(0.0, 1.0 - self.t / self.dur)
        if p.dead or self.t >= self.dur:
            if not p.dead:
                self._finale(run)
            self.stop(run)
            return False
        if self.t >= self.next_pulse:
            self.next_pulse += s["pulse"]
            r = s["radius"] * st.area
            blast(run, self.src, p.x, p.y, r, s["dmg"] * st.might, s["hp_pct"], kb=s["kb"], stun=s["stun"])
            run.add_ring(p.x, p.y, 16, r, 0.3, (255, 120, 130), 6)
            run.particles.feathers(p.x, p.y - 10, 5, (255, 250, 245), 200)
            run.particles.pop_ring(p.x, p.y - 8, r * 0.7, (255, 200, 205), 0.22)
            if self.next_pulse > s["pulse"] * 1.5:      # první kejhnutí už řekl výkřik ultimátky
                j = run.particles.rng.uniform(-24, 24)
                run.add_text(p.x + j, p.y - 44, "KEJH!", (255, 150, 160), 2, 0.5)
            run.sfx("honk", 0.9)
            run.shake(0.05, 0.3)
        # co husa v běhu srazí, to dostane (každá liška nejvýš 1× za 0,3 s)
        flat = s["trample"] * st.might
        for e in run.grid.query(p.x, p.y, p.r + 50):
            if not e.alive or e.prop:
                continue
            dx, dy = e.x - p.x, e.y - p.y
            rr = p.r + e.r + 8
            if dx * dx + dy * dy < rr * rr and self.trampled.get(e.id, -1.0) <= self.t:
                self.trampled[e.id] = self.t + 0.3
                pct = 0.0 if e.boss else s["trample_pct"]
                run.damage_enemy(e, flat + pct * e.max_hp, self.src, dx, dy, 260, False)
        return True

    def _finale(self, run) -> None:
        """Závěrečné „KEJHHH“: odhodí a omráčí lišky kolem – husa má kam utéct, když nesmrtelnost skončí."""
        p = run.player
        s = self.s
        st = p.stats
        r = s["end_r"] * st.area
        blast(run, self.src, p.x, p.y, r, s["end_dmg"] * st.might, s["end_pct"], kb=s["end_kb"], stun=s["end_stun"])
        wipe_eprojs(run, p.x, p.y, r, (255, 220, 225))
        run.add_ring(p.x, p.y, 20, r * 1.05, 0.45, (255, 140, 150), 10)
        run.particles.feathers(p.x, p.y - 10, 18, (255, 250, 245), 300)
        run.particles.glow(p.x, p.y - 14, 60, (255, 90, 110), 0.2)
        run.add_text(p.x, p.y - 56, "KEJHHH!", (255, 150, 160), 3, 0.8)
        run.sfx("ult_goose", 0.7)
        run.shake(0.25, 0.5)

    def stop(self, run) -> None:
        run.player.ult_speed = 1.0
        run.player.ult_aura = 0.0


@effect("goose_fury")
def goose_fury(run, src, s) -> None:
    p = run.player
    run.ult_fx = [f for f in run.ult_fx if f.kind != "goose_fury"]     # nové řádění nahradí běžící
    run.ult_fx.append(GooseFury(run, src, s))
    run.particles.feathers(p.x, p.y - 10, 16, (255, 250, 245), 260)
    run.particles.glow(p.x, p.y - 14, 64, (255, 90, 110), 0.25)
    run.add_ring(p.x, p.y, 10, 170, 0.45, (255, 150, 160), 8)


# =============================================================================================
# Krocan Rambo – Operace Díkůvzdání: salvy brků do všech stran (průraz, kritické zásahy)
# =============================================================================================
class Volley(Fx):
    kind = "thanksgiving"

    def __init__(self, run, src, s) -> None:
        self.src = src
        self.s = s
        self.t = 0.0
        self.n = 0
        self.salvos = int(s["salvos"])
        self.dmg = s["dmg_hp"] * fox_hp(run) * run.player.stats.might    # škáluje s odolností lišek

    def update(self, run, dt: float) -> bool:
        self.t += dt
        while self.n < self.salvos and self.t >= self.n * self.s["gap"]:
            self._salvo(run, self.n)
            self.n += 1
        return self.n < self.salvos

    def _salvo(self, run, i: int) -> None:
        p = run.player
        s = self.s
        st = p.stats
        n = int(s["count"])
        sp = s["speed"] * st.proj_speed
        rot = assets.sprites.rot("feather_t")
        off = (i % 2) * math.pi / n + i * 0.11
        pierce = int(s["pierce"]) + st.pierce
        for k in range(n):
            a = off + k * TAU / n
            ca, sa = math.cos(a), math.sin(a)
            pr = run.add_proj(p.x + ca * 18, p.y - 10 + sa * 18, ca * sp, sa * sp, 8, self.dmg, self.src,
                              pierce=pierce, life=s["life"], kb=90)
            pr.rot = rot
        run.add_ring(p.x, p.y - 8, 12, 70, 0.22, (255, 170, 110), 5)
        run.particles.glow(p.x, p.y - 12, 40, (255, 140, 80), 0.1)
        run.particles.sparks(p.x, p.y - 10, 8, (255, 210, 140), 260)
        run.sfx("shotgun", 0.8)
        run.shake(0.06, 0.35)


@effect("thanksgiving")
def thanksgiving(run, src, s) -> None:
    p = run.player
    run.ult_fx.append(Volley(run, src, s))
    run.particles.feathers(p.x, p.y - 10, 14, (196, 120, 70), 240)
    run.particles.glow(p.x, p.y - 14, 56, (255, 110, 70), 0.2)


# =============================================================================================
# Kohout Elvis – Královské KIKIRIKÍ: původní kokrhání (+ ozvěna s Rockovým koncertem)
# =============================================================================================
def _kikiriki_wave(run, src, s, k: float = 1.0) -> None:
    p = run.player
    st = p.stats
    r = s["radius"] * st.area * (0.8 if k < 1 else 1.0)
    run.add_wave(p.x, p.y, 20, r, 0.45, s["dmg"] * st.might * k, src, kb=s["kb"] * k, stun=s["stun"] * k,
                 color=(255, 230, 120), follow=True).crit = False
    run.add_ring(p.x, p.y, 10, r * 1.1, 0.6, (255, 255, 255), 10)
    wipe_eprojs(run, p.x, p.y, r, (255, 255, 200))
    if k >= 1:
        # bonusové poškození podle max. HP běžných nepřátel (původní kokrhání)
        for e in run.grid.query(p.x, p.y, r):
            if e.alive and not e.boss and (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < r * r:
                run.damage_enemy(e, e.max_hp * s["hp_pct"], src, crit=False)
        p.invuln = max(p.invuln, s["invuln"])
        run.flash((255, 250, 220), 0.15)
        run.particles.stars(p.x, p.y - 20, 16, (255, 230, 90), 280)
        run.particles.glow(p.x, p.y - 14, 60, (255, 210, 110), 0.25)
    else:
        run.particles.stars(p.x, p.y - 20, 8, (255, 140, 255), 220)
        run.sfx("crow", 0.6)
    run.particles.notes(p.x, p.y - 30, 6 if k >= 1 else 4, (255, 230, 120) if k >= 1 else (255, 140, 255))


@effect("kikiriki")
def kikiriki(run, src, s) -> None:
    _kikiriki_wave(run, src, s)
    if s.get("echo"):
        # Rockový koncert: druhá sloka – slabší ozvěna o půl vteřiny později
        run.ult_fx.append(Delayed(0.5, lambda r: _kikiriki_wave(r, src, s, 0.5)))


# =============================================================================================
# Páv Diva – Božská krása: okouzlené lišky bojují za Divu proti ostatním
# =============================================================================================
class Hypno(Fx):
    kind = "hypno"

    def __init__(self, run, src, s) -> None:
        self.src = src
        self.s = s
        self.t = 0.0
        self.r = 0.0
        self.R = s["radius"] * run.player.stats.area
        self.n = 0
        self.x, self.y = run.player.x, run.player.y
        run.charm = (src, s["hit"], s["hit_pct"], s["hit_cd"], s["seek"], s["guard"], s["end_stun"])

    def update(self, run, dt: float) -> bool:
        s = self.s
        p = run.player
        self.t += dt
        self.x, self.y = p.x, p.y
        self.r = self.R * min(1.0, self.t / s["grow"])
        r2 = self.r * self.r
        dur = s["dur"]
        if self.n < s["max_n"]:
            for e in run.grid.query(p.x, p.y, self.r):
                if not e.alive or e.prop or e.boss or e.charm_t > 0:
                    continue
                if (e.x - p.x) ** 2 + (e.y - p.y) ** 2 > r2:
                    continue
                e.charm_t = dur * (0.5 if e.elite else 1.0)
                e.foe = None
                e.hyp_t = 0.0
                e.touch_cd = 0.2
                self.n += 1
                run.particles.hearts(e.x, e.y - 20, 2)
                if self.n >= s["max_n"]:
                    break
        return self.t < s["grow"] + 0.15


@effect("hypno")
def hypno(run, src, s) -> None:
    p = run.player
    run.ult_fx.append(Hypno(run, src, s))
    run.particles.hearts(p.x, p.y - 30, 8, 180)
    run.particles.glow(p.x, p.y - 14, 70, (200, 110, 255), 0.3)
    run.add_ring(p.x, p.y, 10, 60, 0.3, (255, 180, 255), 6)


def charm_target(run, e):
    """Okouzlená liška si hledá nejbližšího „neokouzleného“ nepřítele (i bosse)."""
    seek = run.charm[4] if run.charm else 260.0
    return run.grid.nearest(e.x, e.y, seek, lambda o: o is not e and o.alive and not o.prop and o.charm_t <= 0
                            and o.alpha >= 128)


def charm_hit(run, e, foe, dx: float, dy: float) -> None:
    src, hit, hit_pct, hit_cd = run.charm[:4]
    dmg = e.dmg * hit
    if not foe.boss:
        dmg = max(dmg, foe.max_hp * hit_pct * (0.4 if foe.elite else 1.0))
    run.damage_enemy(foe, dmg, src, dx, dy, 140, False)
    e.touch_cd = hit_cd
    if run.particles.rng.random() < 0.5:
        run.particles.hearts(foe.x, foe.y - 16, 1, 60)


# =============================================================================================
# Tajný tučňák – Doba ledová: ledová bouře mrazí a točí lišky dokola, na konci je roztříští
# =============================================================================================
class IceAge(Fx):
    kind = "ice_age"

    def __init__(self, run, src, s) -> None:
        p = run.player
        self.src = src
        self.s = s
        self.t = 0.0
        self.dur = s["dur"]
        self.next = 0.0
        self.R = s["radius"] * p.stats.area
        self.x, self.y = p.x, p.y
        self.spin = 1.0 if p.face == 0 else -1.0

    def update(self, run, dt: float) -> bool:
        p = run.player
        s = self.s
        st = p.stats
        self.t += dt
        self.x, self.y = p.x, p.y
        R = self.R
        tick = self.t >= self.next
        if tick:
            self.next += s["tick"]
        sw = s["swirl"] * self.spin * dt
        dr = s["drift"] * dt
        flat = s["dmg"] * st.might
        for e in run.grid.query(p.x, p.y, R + 30):
            if not e.alive or e.prop:
                continue
            dx, dy = e.x - p.x, e.y - p.y
            d2 = dx * dx + dy * dy
            rr = R + e.r
            if d2 >= rr * rr:
                continue
            if tick:
                if e.boss:
                    run.damage_enemy(e, flat, self.src, dx, dy, 0.0, False, s["boss_slow"], s["tick"] + 0.3,
                                     flash=False)
                else:
                    run.damage_enemy(e, flat + s["hp_pct"] * e.max_hp, self.src, dx, dy, 0.0, False,
                                     freeze=s["tick"] + 0.35, flash=False)
            if e.boss or not e.alive:
                continue
            # vír: zmrzlé lišky kloužou dokola a pomalu ven
            d = math.sqrt(d2) or 1.0
            k = 0.4 if e.elite else 1.0
            e.x += (-dy / d * sw + dx / d * dr) * k
            e.y += (dx / d * sw + dy / d * dr) * k
        if self.t >= self.dur or p.dead:
            self._shatter(run)
            return False
        return True

    def _shatter(self, run) -> None:
        p = run.player
        s = self.s
        st = p.stats
        blast(run, self.src, p.x, p.y, self.R, s["end_dmg"] * st.might, s["end_pct"], kb=s["end_kb"],
              freeze=s["end_freeze"])
        run.add_ring(p.x, p.y, 20, self.R * 1.1, 0.45, (200, 240, 255), 10)
        run.particles.shards(p.x, p.y - 10, 22, self.R * 0.9)
        run.particles.glow(p.x, p.y - 12, 70, (150, 210, 255), 0.25)
        run.sfx("shatter", 1.0)
        run.shake(0.15, 0.45)

    def stop(self, run) -> None:
        pass


@effect("ice_age")
def ice_age(run, src, s) -> None:
    p = run.player
    run.ult_fx = [f for f in run.ult_fx if f.kind != "ice_age"]
    run.ult_fx.append(IceAge(run, src, s))
    wipe_eprojs(run, p.x, p.y, s["radius"] * p.stats.area, (220, 245, 255))
    run.particles.flakes(p.x, p.y - 10, 16, 200)
    run.particles.glow(p.x, p.y - 14, 70, (150, 210, 255), 0.25)
    run.add_ring(p.x, p.y, 10, s["radius"] * p.stats.area, 0.4, (220, 245, 255), 8)


# =============================================================================================
# Straka Klepna – Velká loupež: oslní lišky kolem, okrade je o mince a stáhne k sobě zrní
# =============================================================================================
@effect("heist")
def heist(run, src, s) -> None:
    p = run.player
    st = p.stats
    r = s["radius"] * st.area
    rng = run.rng
    coins = 0
    for e in list(run.enemies):         # přímo seznam: okamžitý efekt nesmí záviset na tom, zda je mřížka už postavená
        if not e.alive or e.prop:
            continue
        dx, dy = e.x - p.x, e.y - p.y
        if dx * dx + dy * dy >= (r + e.r) ** 2:
            continue
        pct = 0.0 if e.boss else s["hp_pct"]
        run.damage_enemy(e, s["dmg"] * st.might + pct * e.max_hp, src, dx, dy, 120, False, stun=s["stun"])
        if not e.boss and coins < s["coins_max"] and rng.random() < s["coin"]:
            # kapsářka: oslněná liška upustí minci, která rovnou letí ke strace
            coins += 1
            pk = Pickup(e.x, e.y, P_COIN, 1)
            pk.vz = 140
            pk.z = 1
            pk.attract = True
            run.pickups.append(pk)
            run.particles.sparkle(e.x, e.y - 12, (255, 220, 90), 2)
    loot = s["loot"]
    for pk in run.pickups:
        if pk.kind in (P_XP, P_GOLDEGG, P_COIN) and (pk.x - p.x) ** 2 + (pk.y - p.y) ** 2 < loot * loot:
            pk.attract = True               # „všechno, co se třpytí, je moje“
    run.add_ring(p.x, p.y, 10, r, 0.4, (180, 210, 255), 8)
    run.add_ring(p.x, p.y, 10, r * 0.6, 0.3, (255, 236, 150), 4)
    run.particles.burst_ring(p.x, p.y - 16, 18, (255, 236, 150), 260)
    run.particles.stars(p.x, p.y - 20, 14, (200, 225, 255), 300)
    run.particles.glow(p.x, p.y - 14, 70, (170, 200, 255), 0.25)
    run.particles.feathers(p.x, p.y - 10, 10, (60, 60, 80), 220)
