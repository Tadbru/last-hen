"""Spawn director – křivka obtížnosti, složení vln, formace, elity a bossové.

Čas v tabulkách je „efektivní minuta“ (v rychlém módu běží čas obtížnosti rychleji).
"""
from __future__ import annotations

# (minuta, spawnů/s, max naživu, váhy nepřátel)
TIMELINE = [
    (0.0, 1.2, 30, {"fox": 10}),
    (0.5, 2.0, 50, {"fox": 10, "bat": 2}),
    (1.0, 2.7, 70, {"fox": 10, "fast_fox": 3, "bat": 3}),
    (2.0, 4.2, 120, {"fox": 9, "fast_fox": 4, "bat": 3, "armored_fox": 2, "spitter": 1}),
    (3.0, 6.6, 180, {"fox": 8, "fast_fox": 4, "bat": 3, "armored_fox": 3, "spitter": 2, "exploder": 2}),
    (4.0, 8.6, 230, {"fox": 7, "fast_fox": 4, "bat": 3, "armored_fox": 3, "spitter": 2, "exploder": 2, "wolf": 1}),
    (5.0, 11.0, 280, {"fox": 7, "fast_fox": 5, "bat": 4, "armored_fox": 4, "spitter": 3, "exploder": 3, "wolf": 2}),
    (6.0, 14.0, 320, {"fox": 6, "fast_fox": 5, "bat": 4, "armored_fox": 4, "spitter": 3, "exploder": 3, "wolf": 3}),
    (7.0, 17.0, 360, {"fox": 6, "fast_fox": 6, "bat": 4, "armored_fox": 5, "spitter": 3, "exploder": 3, "wolf": 4}),
    (8.0, 20.0, 400, {"fox": 6, "fast_fox": 6, "bat": 5, "armored_fox": 5, "spitter": 4, "exploder": 4, "wolf": 5}),
    (9.0, 24.0, 400, {"fox": 5, "fast_fox": 7, "bat": 5, "armored_fox": 6, "spitter": 4, "exploder": 4, "wolf": 6}),
    (10.0, 26.0, 400, {"fox": 5, "fast_fox": 7, "bat": 5, "armored_fox": 6, "spitter": 4, "exploder": 4, "wolf": 6}),
]

# (efektivní minuta, formace, nepřítel, počet)
EVENTS = [
    (1.5, "ring", "fox", 24),
    (2.5, "horde", "fast_fox", 22),
    (3.4, "encircle", "armored_fox", 28),
    (4.4, "horde", "bat", 32),
    (5.4, "ring", "wolf", 12),
    (6.4, "encircle", "fox", 50),
    (7.4, "horde", "exploder", 26),
    (8.4, "ring", "mixed", 60),
    (9.3, "encircle", "mixed", 70),
]

# Elity: (reálný čas v s, druh) – plný mód
ELITES_FULL = [(50, "giant_fox"), (100, "owl"), (160, "giant_fox"), (210, "bear"), (265, "owl"), (300, "giant_fox"),
               (350, "bear"), (395, "owl"), (430, "giant_fox"), (470, "bear"), (520, "owl"), (555, "giant_fox"),
               (585, "bear")]
ELITES_QUICK = [(55, "giant_fox"), (95, "owl"), (128, "giant_fox")]

# Bossové: (reálný čas v s, boss)
BOSSES_FULL = [(120, "spy_fox"), (240, "rabbit"), (360, "zombie_bear"), (480, "wolf_alpha"), (600, "zombie_rooster")]
BOSSES_QUICK = [(150, "zombie_rooster")]

QUICK_TIME_SCALE = 1.8     # efektivní minuty = reálné × 1.8
QUICK_LENGTH = 150         # boss přilétá ve 2:30
FULL_LENGTH = 600

# --- Nekonečná noc --------------------------------------------------------------------------------
# 1. noc = přesně Plný mód. Po porážce Kohouta začne další noc: časy níže jsou v s od jeho porážky.
ENDLESS_CYCLE = [(60, "spy_fox"), (120, "rabbit"), (180, "zombie_bear"), (240, "wolf_alpha"),
                 (330, "zombie_rooster")]
ENDLESS_ELITES = [(25, "giant_fox"), (55, "owl"), (90, "bear"), (115, "giant_fox"), (150, "owl"), (205, "bear"),
                  (225, "giant_fox"), (265, "owl"), (290, "bear"), (310, "giant_fox")]
ENDLESS_EVENT_FROM = 4.4    # formace od této minuty se po 9:30 opakují…
ENDLESS_EVENT_REPEAT = 6.0  # …s posunem o 6 min (10:24, 11:24, … 16:24, …)
ENDLESS_NIGHT_MIGHT = 0.04  # noční síla: +4 % poškození za level-up po dokončeném buildu (dřív 2 % – neznatelné, B-84)
ENDLESS_HP_RAMP = 0.75      # po 10. minutě HP lišek roste lineárně o 75 % HP z 10. minuty za minutu (B-84)
ENDLESS_ENRAGE = 150.0      # Kohout dalších nocí zuří po 2,5 min souboje (dřív 2 min – zeď, B-81; Plný mód 3 min)
ENDLESS_MINI_MULT = 3.0     # HP mini-bossů ×3 za každou další noc
ENDLESS_FINAL_MULT = 2.0    # HP Kohouta ×2 za každou další noc (dřív ×4 – nikdo ho ve 2. noci neporazil, B-81)
ENDLESS_BOSS_GAP = 20.0     # od 2. noci přijde další boss nejdřív 20 s po porážce předchozího (B-82)
ENDLESS_LATE_NIGHT_HP = 1.5 # od 3. noci HP lišek ×1,5 za každou noc – silný build jinak vydržel přes 45 min
ENDLESS_DARK = 0.7          # osvětlení se zastaví před svítáním (0 = noc, 1 = den)


def endless_boss_hp(night: int, final: bool = False) -> float:
    """Násobič HP bossů v dalších nocích (1. noc = Plný mód)."""
    if night <= 1:
        return 1.0
    return (ENDLESS_FINAL_MULT if final else ENDLESS_MINI_MULT) ** (night - 1)


def endless_hp_mult(eff_min: float, night: int = 1) -> float:
    """HP křivka nepřátel v Nekonečné noci: do 10. minuty přesně jako Plný mód, potom lineárně.
    Kubická křivka Plného módu (+ dřívější přídavek 20 %/min) dělala z 15.–20. minuty zeď: ×18 HP za 10 min (B-84).
    Od 3. noci přidává každá noc ×ENDLESS_LATE_NIGHT_HP, aby runy nekonečně netrvaly."""
    if eff_min <= 10.0:
        return hp_mult(eff_min)
    late = ENDLESS_LATE_NIGHT_HP ** max(0, night - 2)
    return hp_mult(10.0) * (1.0 + ENDLESS_HP_RAMP * (eff_min - 10.0)) * late


def hp_mult(eff_min: float) -> float:
    return 1.0 + 0.2 * eff_min + 0.04 * eff_min ** 2 + 0.011 * eff_min ** 3


def dmg_mult(eff_min: float) -> float:
    return 1.0 + 0.1 * eff_min


def sample(eff_min: float):
    """Vrátí (rate, max_alive, weights) interpolované pro daný čas."""
    prev = TIMELINE[0]
    for key in TIMELINE:
        if key[0] > eff_min:
            t = (eff_min - prev[0]) / max(1e-6, key[0] - prev[0])
            rate = prev[1] + (key[1] - prev[1]) * t
            alive = int(prev[2] + (key[2] - prev[2]) * t)
            return rate, alive, prev[3]
        prev = key
    return prev[1], prev[2], prev[3]
