"""Laboratoř ultimátek – měření bez okna (balanc, výkon, screenshoty).

    python tools/ult_lab.py measure [--minute 3] [--seeds 4] [--on hen]   # jedna aktivace v davu (zabití, poškození…)
    python tools/ult_lab.py boss [--seeds 4] [--on hen]                   # Zombie Kohout v rychlém módu, bot
    python tools/ult_lab.py runs --mode quick [--seeds 4] [--swap]        # celé runy botem (nabíjení, podíl, výhry)
    python tools/ult_lab.py perf                                          # 400 nepřátel + aktivní ultimátka (render)
    python tools/ult_lab.py shots OUT_DIR                                 # screenshot okamžiku aktivace každé ultimátky
    python tools/ult_lab.py table                                         # hodnoty spočítané z dat (bez simulace)

--on hen = všechny ultimátky na stejném zvířeti (srovnání bez vlivu zbraně a pasivky), jinak každá na svém zvířeti.
--swap   = runs: slepice postupně se všemi ultimátkami (A/B test).
"""
from __future__ import annotations

import argparse
import math
import os
import random
import statistics as stx
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ORDER = ["hen", "duck", "goose", "turkey", "rooster", "peacock", "penguin", "magpie"]


def _init(render: bool = False) -> None:
    pygame.init()
    if render:
        pygame.display.set_mode((540, 960))
    from game import assets
    assets.init(headless_sim=not render, audio_enabled=False)


def _fresh_ids() -> None:
    """Id nepřátel jsou globální čítač a ovlivňují AI (kličkování, separace) – reset = opakovatelný run."""
    from game.world import entities
    entities._ids[0] = 0


def _ult_of(char: str) -> str:
    from game.data.ultimates import ULT_BY_CHAR
    return ULT_BY_CHAR[char]


def _crowd_run(char: str, ult: str | None, seed: int, minute: float, n: int, headless: bool = True):
    from game import scenarios as SC
    from game.world.run import Run, RunConfig
    _fresh_ids()
    run = Run(RunConfig(character=char, mode="full", seed=seed, headless=headless, ult=ult))
    SC._skip_to(run, minute * 60.0)
    run.weapons[0].set_level(4 if minute < 6 else 7)
    kinds = SC.MIXES[3] if minute < 6 else SC.MIXES[8]
    SC.ring_of_enemies(run, n, random.Random(seed), kinds=kinds)
    run.director.update = lambda dt: None          # bez dalších spawnů – měří se jen tahle skupina
    return run


def _hook_hits(run, log: list) -> None:
    """Zaznamená každý zásah ultimátkou: (čas od aktivace, vzdálenost od hráče, id nepřítele)."""
    from game.world.ultimates import UltSource
    orig = run.damage_enemy

    def wrapped(e, dmg, src, *a, **k):
        if type(src) is UltSource:
            p = run.player
            hp = max(0.0, e.hp)
            r = orig(e, dmg, src, *a, **k)
            log.append((run.time - src.t0, math.hypot(e.x - p.x, e.y - p.y), e.id, hp - max(0.0, e.hp)))
            return r
        return orig(e, dmg, src, *a, **k)
    run.damage_enemy = wrapped


def measure_one(char: str, ult: str | None, seed: int, minute: float, n: int, activate: bool, secs: float = 8.0):
    from game.config import DT
    run = _crowd_run(char, ult, seed, minute, n)
    hits: list = []
    _hook_hits(run, hits)
    xp = [0.0]
    orig_drop = run.drop_xp

    def drop(x, y, v):
        xp[0] += v
        orig_drop(x, y, v)
    run.drop_xp = drop
    run.update(DT)
    run.player.stats.max_hp = run.player.hp = 1e6     # měří se úleva (přijaté poškození), ne smrt
    hp0 = sum(e.hp for e in run.enemies if not e.boss)
    taken0 = run.stats_dmg_taken
    if activate:
        run.crow_charge = run.crow_cap = 1.0
        run.crow()
    cc = 0.0
    fx_t = 0.0
    taken3 = None
    frames = int(secs / DT)
    for i in range(frames):
        if i == int(3.0 / DT):
            taken3 = run.stats_dmg_taken - taken0
        run.update(DT, 0.0, 0.0)
        if run.state != "playing":
            if run.state in ("levelup", "chest"):
                run.state = "playing"
                run.offer = None
                run.pending_levelups = 0
                run.pending_chests = []
            else:
                break
        if run.ult_fx:
            fx_t += DT
        cc += sum(1 for e in run.enemies if e.stun_t > 0 or e.freeze_t > 0 or e.charm_t > 0) * DT
    src = run.ult_log[-1] if (activate and run.ult_log) else None
    return dict(kills=src.kills if src else 0, dmg=sum(h[3] for h in hits), hp0=hp0,
                taken=run.stats_dmg_taken - taken0, cc=cc, reach=max((h[1] for h in hits), default=0.0),
                last_hit=max((h[0] for h in hits), default=0.0), fx_t=fx_t, hit_n=len({h[2] for h in hits}),
                alive=len(run.enemies), kills_total=run.kills, taken3=taken3 or 0.0, xp=xp[0])


def cmd_measure(a) -> None:
    _init()
    rows = []
    print(f"Jedna aktivace, minuta {a.minute}, {a.n} lišek kolem, {a.seeds} seedů, "
          f"{'všechny na: ' + a.on if a.on else 'každá na svém zvířeti'}. Medián přes seedy.")
    print(f"{'ultimátka':14s} {'zabití':>6s} {'poškoz.':>8s} {'%HP davu':>8s} {'zasaž.':>6s} {'dosah':>6s} "
          f"{'trvání':>6s} {'kontrola':>8s} {'přij. 3 s':>9s} {'přij. 8 s':>9s} {'XP navíc':>8s}")
    for char in ORDER:
        uid = _ult_of(char)
        on = a.on or char
        res = [measure_one(on, uid, s, a.minute, a.n, True) for s in range(1, a.seeds + 1)]
        base = [measure_one(on, uid, s, a.minute, a.n, False) for s in range(1, a.seeds + 1)]
        md = lambda k, L=res: stx.median(r[k] for r in L)  # noqa: E731
        cc = md("cc") - stx.median(r["cc"] for r in base)
        mb = lambda k: stx.median(r[k] for r in base)  # noqa: E731
        row = dict(ult=uid, kills=md("kills"), dmg=md("dmg"), pct=md("dmg") / max(1, md("hp0")) * 100,
                   hit=md("hit_n"), reach=md("reach"), dur=max(md("last_hit"), md("fx_t")), cc=cc,
                   t3=md("taken3") / max(1.0, mb("taken3")) * 100, t8=md("taken") / max(1.0, mb("taken")) * 100,
                   xp=md("xp") - mb("xp"))
        rows.append(row)
        print(f"{uid:14s} {row['kills']:6.0f} {row['dmg']:8.0f} {row['pct']:7.0f}% {row['hit']:6.0f} {row['reach']:6.0f} "
              f"{row['dur']:5.1f}s {row['cc']:7.0f}s {row['t3']:8.0f}% {row['t8']:8.0f}% {row['xp']:8.0f}")
    return rows


def boss_one(char: str, ult: str | None, seed: int, max_t: float = 240.0):
    """Bot odehraje rychlý mód až k příletu Kohouta (všechny varianty stejně – s klasickým kokrháním),
    pak dostane zkoušenou ultimátku. Stejný seed = stejný stav na začátku souboje."""
    from game.bot import Bot
    from game.config import DT
    from game.data.ultimates import ULTIMATES
    from game.world.run import Run, RunConfig
    _fresh_ids()
    run = Run(RunConfig(character=char, mode="quick", seed=seed * 11 + 5, headless=True, ult="kikiriki"))
    bot = Bot(run)
    while run.final_boss is None and run.state not in ("dead", "victory") and run.time < 400:
        bot.step(DT)
    if run.final_boss is None:
        return None                     # bot nepřežil do příletu bosse
    run.ult = ULTIMATES[ult] if ult else run.ult
    run.crow_charge = run.crow_cap = 1.0
    used0 = run.crows_used
    boss = run.final_boss
    t0 = run.time
    while run.time - t0 < max_t:
        bot.step(DT)
        if run.state in ("dead", "victory"):
            break
    bh = boss.e.max_hp
    logs = [s for s in run.ult_log if s.t0 >= t0]
    ult_boss = sum(s.boss_dmg.get(boss.e.id, 0.0) for s in logs)
    return dict(win=run.victory, t=run.time - t0, uses=run.crows_used - used0, ult_pct=ult_boss / bh * 100,
                per_use=max((s.boss_dmg.get(boss.e.id, 0.0) for s in logs), default=0.0) / bh * 100,
                hp=run.player.hp / run.player.stats.max_hp)


def cmd_boss(a) -> None:
    _init()
    print(f"Zombie Kohout (rychlý mód, 15 % HP), bot, {a.seeds} seedů, "
          f"{'všechny na: ' + a.on if a.on else 'každá na svém zvířeti'}")
    print(f"{'ultimátka':14s} {'výhry':>6s} {'souboj':>7s} {'min':>5s} {'použití':>7s} {'ult % HP':>8s} {'max/akt.':>8s}")
    for char in ORDER:
        uid = _ult_of(char)
        on = a.on or char
        res = [r for r in (boss_one(on, uid, s) for s in range(1, a.seeds + 1)) if r is not None]
        if not res:
            print(f"{uid:14s} bot se k bossovi nedostal")
            continue
        wins = sum(r["win"] for r in res)
        ts = [r["t"] for r in res if r["win"]]
        print(f"{uid:14s} {wins:3d}/{len(res):<2d} {stx.median(ts) if ts else 0:6.0f}s {min(ts) if ts else 0:4.0f}s "
              f"{stx.mean(r['uses'] for r in res):7.1f} {stx.mean(r['ult_pct'] for r in res):7.1f}% "
              f"{max(r['per_use'] for r in res):7.1f}%")


def run_one(char: str, ult: str | None, mode: str, seed: int, max_t: float = 900.0):
    from game.bot import Bot
    from game.config import DT
    from game.world.run import Run, RunConfig
    _fresh_ids()
    run = Run(RunConfig(character=char, mode=mode, seed=seed * 7 + 3, headless=True, ult=ult))
    bot = Bot(run)
    ready_t, last_use, was_ready, used = [], 0.0, run.crow_ready, 0
    while run.time < max_t:
        bot.step(DT)
        if run.crow_ready and not was_ready:
            ready_t.append(run.time - last_use)
        if run.crows_used != used:
            used = run.crows_used
            last_use = run.time
        was_ready = run.crow_ready
        if run.state in ("dead", "victory"):
            break
    wdmg = sum(w.damage_dealt for w in run.weapons)
    udmg = sum(s.damage_dealt for s in run.ult_log)
    ukills = sum(s.kills for s in run.ult_log)
    bl = run.boss_log.get("zombie_rooster")
    return dict(win=run.victory, t=run.time, kills=run.kills, uses=run.crows_used,
                charge=stx.mean(ready_t) if ready_t else 0.0, first=ready_t[0] if ready_t else 0.0,
                kshare=ukills / max(1, run.kills) * 100, dshare=udmg / max(1.0, udmg + wdmg) * 100,
                boss=bl[1] if bl and bl[1] else None)


def cmd_runs(a) -> None:
    _init()
    pairs = [("hen", _ult_of(c)) for c in ORDER] if a.swap else [(c, _ult_of(c)) for c in ORDER]
    print(f"Celé runy botem, mód {a.mode}, Farma, Normal, bez Hnízda, {a.seeds} seedů"
          f"{', slepice se všemi ultimátkami' if a.swap else ''}")
    print(f"{'zvíře':8s} {'ultimátka':14s} {'výhry':>6s} {'čas':>6s} {'zabití':>7s} {'použití':>7s} {'nabití':>7s} "
          f"{'1. nab.':>7s} {'zabití ult':>10s} {'poškoz. ult':>11s} {'boss':>6s}")
    for char, uid in pairs:
        t0 = time.perf_counter()
        res = [run_one(char, uid, a.mode, s) for s in range(1, a.seeds + 1)]
        bs = [r["boss"] for r in res if r["boss"]]
        print(f"{char:8s} {uid:14s} {sum(r['win'] for r in res):3d}/{len(res):<2d} "
              f"{stx.median(r['t'] for r in res):6.0f} {stx.median(r['kills'] for r in res):7.0f} "
              f"{stx.mean(r['uses'] for r in res):7.1f} {stx.mean(r['charge'] for r in res):6.1f}s "
              f"{stx.mean(r['first'] for r in res):6.1f}s {stx.mean(r['kshare'] for r in res):9.1f}% "
              f"{stx.mean(r['dshare'] for r in res):10.1f}% {stx.median(bs) if bs else 0:5.0f}s"
              f"   ({time.perf_counter() - t0:.0f} s)", flush=True)


def cmd_perf(a) -> None:
    """Nejhorší scéna: 400 nepřátel (nesmrtelní), ~300 projektilů, ultimátka stále aktivní; logika + render."""
    _init(render=True)
    from game import scenarios as SC
    from game.config import DT, H, W
    from game.core.input import Joystick
    from game.ui import hud
    from game.world.render import RunRenderer
    surf = pygame.Surface((W, H))
    joy = Joystick()
    print("400 nepřátel + ~300 projektilů + aktivní ultimátka (600 snímků, logika + render + HUD)")
    print(f"{'ultimátka':14s} {'avg ms':>7s} {'p95 ms':>7s} {'max ms':>7s} {'nepřátel':>8s} {'proj.':>6s} {'částic':>6s}")
    for char in ORDER:
        run, sc = SC.make_run(f"ult_stress_{char}", seed=3, headless=False)
        ren = RunRenderer(run)
        rng = random.Random(2)
        times = []
        mx_e = mx_p = mx_pa = 0
        for i in range(660):
            sc.tick(run)
            while len(run.projs) < 300:
                ang = rng.uniform(0, math.tau)
                run.add_proj(run.player.x, run.player.y, math.cos(ang) * 300, math.sin(ang) * 300, 6, 1, None,
                             pierce=999, life=1.5)
            t0 = time.perf_counter()
            run.update(DT, math.cos(i * 0.02), math.sin(i * 0.02), crow=run.crow_ready)
            if run.state != "playing":
                run.state = "playing"
                run.offer = None
                run.pending_levelups = 0
            ren.draw(surf, DT)
            hud.draw_hud(surf, run, joy, i * DT)
            if i >= 60:
                times.append((time.perf_counter() - t0) * 1000)
            mx_e, mx_p, mx_pa = max(mx_e, len(run.enemies)), max(mx_p, len(run.projs)), max(mx_pa, len(run.particles))
        times.sort()
        print(f"{run.ult.id:14s} {stx.mean(times):7.2f} {times[int(len(times) * 0.95)]:7.2f} {times[-1]:7.2f} "
              f"{mx_e:8d} {mx_p:6d} {mx_pa:6d}")


def cmd_shots(a) -> None:
    _init(render=True)
    from game import scenarios as SC
    from game.config import DT, H, W
    from game.core.input import Joystick
    from game.ui import hud
    from game.world.render import RunRenderer
    os.makedirs(a.out, exist_ok=True)
    joy = Joystick()
    surf = pygame.Surface((W, H))
    for char in ORDER:
        for variant in ("", "_boss"):
            run, sc = SC.make_run(f"ult_{char}{variant}", seed=2, headless=False)
            ren = RunRenderer(run)
            for i in range(40):
                run.update(DT, 0.6, -0.3)
            shots = {0.0: "ready", 0.25: "a", 0.7: "b", 1.6: "c"}
            run.crow()
            t = 0.0
            frame = 0
            while t <= 1.7:
                if run.state != "playing":
                    run.state = "playing"
                    run.offer = None
                    run.pending_levelups = 0
                for k, tag in list(shots.items()):
                    if t >= k:
                        ren.draw(surf, DT)
                        hud.draw_hud(surf, run, joy, frame * DT)
                        pygame.image.save(surf, os.path.join(a.out, f"{char}{variant}_{tag}.png"))
                        del shots[k]
                run.update(DT, 0.6, -0.3)
                ren.draw(surf, DT)        # renderer počítá čas animací z volání draw
                t += DT
                frame += 1
        print("ok", char)


def cmd_table(a) -> None:
    """Hodnoty spočítané přímo z tabulky ULTIMATES (síla 1, dosah 1, bez evoluce): dosah, trvání, poškození
    jedné lišce v 3. a 8. minutě plného módu, nabíjení."""
    from game.data import waves as WV
    from game.data.ultimates import ULT_BOSS_CAP, ULTIMATES
    fox = {m: 10 * WV.hp_mult(m) for m in (3, 8)}
    print(f"Liška má v 3. min {fox[3]:.0f} HP, v 8. min {fox[8]:.0f} HP. Strop bosse {ULT_BOSS_CAP * 100:.0f} % max. HP"
          " za aktivaci.")
    print("| Ultimátka | Nabití (zabití / nejdřív s / nejkratší rozestup i s Budíkem) | Dosah | Trvání | Poškození lišce 3. / 8. min "
          "| Evoluce |")
    print("|---|---|---|---|---|---|")

    def dmg(m, flat, pct):
        return min(fox[m], flat + pct * fox[m]) / fox[m] * 100

    for char in ORDER:
        u = ULTIMATES[_ult_of(char)]
        s = u.params
        if u.id == "egg_rain":
            reach, dur = f"{s['range']} (výbuch r {s['radius']})", f"{s['spread']:.1f} s + let"
            d = [dmg(m, s["dmg"], s["hp_pct"]) for m in (3, 8)]
            note = f"{s['eggs']} vajec, omráčí {s['stun']} s, XP ×{1 + s['xp_bonus']:.0f}"
        elif u.id == "flood":
            reach, dur = f"{s['length']} × {s['half_w'] * 2}", f"{s['length'] / s['speed']:.1f} s"
            d = [dmg(m, s["dmg"] + s["crash"], s["hp_pct"] + s["crash_pct"]) for m in (3, 8)]
            note = f"rozstřik r {s['splash']}, zpomalí {s['slow'] * 100:.0f} % na {s['slow_t']:.0f} s"
        elif u.id == "goose_fury":
            n = int(s["dur"] / s["pulse"]) + 1
            reach, dur = f"{s['radius']} / závěr {s['end_r']}", f"{s['dur']:.1f} s"
            d = [dmg(m, s["dmg"] * n + s["end_dmg"], s["hp_pct"] * n + s["end_pct"]) for m in (3, 8)]
            note = f"nesmrtelnost {s['dur']:.0f} s, rychlost ×{s['speed']}, {n} kejhnutí, závěr omráčí {s['end_stun']} s"
        elif u.id == "thanksgiving":
            reach, dur = f"{s['speed'] * s['life']:.0f}", f"{(s['salvos'] - 1) * s['gap']:.1f} s"
            d = [min(100.0, s["dmg_hp"] * 100)] * 2
            note = f"{s['salvos']}×{s['count']} brků, průraz {s['pierce']}, každý brk {s['dmg_hp'] * 100:.0f} % HP lišky"
        elif u.id == "kikiriki":
            reach, dur = f"{s['radius']}", "0,5 s"
            d = [dmg(m, s["dmg"], s["hp_pct"]) for m in (3, 8)]
            note = f"odhoz {s['kb']}, omráčí {s['stun']} s, ničí sliz, nesmrtelnost {s['invuln']:.0f} s"
        elif u.id == "hypno":
            reach, dur = f"{s['radius']}", f"{s['dur']:.0f} s"
            d = [0.0, 0.0]
            note = (f"okouzlí max. {s['max_n']} lišek, úder {s['hit']:.0f}× poškození lišky / "
                    f"{s['hit_pct'] * 100:.0f} % HP cíle za {s['hit_cd']} s")
        elif u.id == "heist":
            reach, dur = f"{s['radius']} (zrní {s['loot']})", "0,5 s"
            d = [dmg(m, s["dmg"], s["hp_pct"]) for m in (3, 8)]
            note = (f"omráčí {s['stun']} s, {s['coin'] * 100:.0f} % lišek upustí minci (max. {s['coins_max']}), "
                    f"stáhne zrní do {s['loot']} px")
        else:
            n = int(s["dur"] / s["tick"])
            reach, dur = f"{s['radius']}", f"{s['dur']:.1f} s"
            d = [dmg(m, s["dmg"] * n + s["end_dmg"], s["hp_pct"] * n + s["end_pct"]) for m in (3, 8)]
            note = f"mrazí, vír {s['swirl']} px/s, konec omráčí mrazem {s['end_freeze']} s"
        evo = ", ".join(f"{k}={v}" for k, v in u.evo_params.items())
        dd = "nepřímé" if u.id == "hypno" else f"{d[0]:.0f} % / {d[1]:.0f} %"
        print(f"| {u.name} | {u.kills} / {u.min_cd:g} / {u.cd_floor:g} | {reach} | {dur} | {dd} | {u.evo}: {evo} |")
        print(f"| – | {note} | | | | |")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")       # české texty i v konzoli s jinou kódovou stránkou
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["measure", "boss", "runs", "perf", "shots", "table"])
    ap.add_argument("out", nargs="?", default="ult_shots")
    ap.add_argument("--minute", type=float, default=3.0)
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--on", default="")
    ap.add_argument("--mode", default="quick")
    ap.add_argument("--swap", action="store_true")
    a = ap.parse_args()
    {"measure": cmd_measure, "boss": cmd_boss, "runs": cmd_runs, "perf": cmd_perf, "shots": cmd_shots,
     "table": cmd_table}[a.cmd](a)


if __name__ == "__main__":
    main()
