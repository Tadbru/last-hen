"""Syntéza zvuků a hudby v numpy (chiptune s „farmářským“ nádechem).

Vše vrací mono float32 pole v rozsahu -1..1 při SR Hz.
"""
from __future__ import annotations

import math
import random

import numpy as np

SR = 22050


def _n(dur: float) -> int:
    return max(1, int(SR * dur))


def phase_of(freq, n: int) -> np.ndarray:
    """Fáze (v cyklech) pro konstantní nebo proměnnou frekvenci."""
    if np.isscalar(freq):
        return np.arange(n, dtype=np.float32) * (float(freq) / SR)
    f = np.asarray(freq, dtype=np.float32)
    if len(f) < n:
        f = np.concatenate([f, np.full(n - len(f), f[-1] if len(f) else 440.0, dtype=np.float32)])
    elif len(f) > n:
        f = f[:n]
    return np.cumsum(f) / SR


def wave(kind: str, freq, dur: float, duty: float = 0.5) -> np.ndarray:
    n = _n(dur)
    ph = phase_of(freq, n) % 1.0
    if kind == "square":
        return np.where(ph < duty, 1.0, -1.0).astype(np.float32)
    if kind == "saw":
        return (2.0 * ph - 1.0).astype(np.float32)
    if kind == "tri":
        return (4.0 * np.abs(ph - 0.5) - 1.0).astype(np.float32)
    if kind == "sine":
        return np.sin(ph * 2 * np.pi).astype(np.float32)
    raise ValueError(kind)


def noise(dur: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, _n(dur)).astype(np.float32)


def sweep(f0: float, f1: float, dur: float, curve: float = 1.0) -> np.ndarray:
    t = np.linspace(0, 1, _n(dur), dtype=np.float32) ** curve
    return f0 + (f1 - f0) * t


def env(n: int, a: float = 0.005, d: float = 0.05, s: float = 0.6, r: float = 0.1, hold: float | None = None) -> np.ndarray:
    """ADSR obálka délky n vzorků."""
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    if hold is None:
        hold_n = max(0, n - a_n - d_n - r_n)
    else:
        hold_n = int(hold * SR)
    parts = [np.linspace(0, 1, max(1, a_n), dtype=np.float32),
             np.linspace(1, s, max(1, d_n), dtype=np.float32),
             np.full(hold_n, s, dtype=np.float32),
             np.linspace(s, 0, max(1, r_n), dtype=np.float32)]
    e = np.concatenate(parts)
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e), dtype=np.float32)])
    return e[:n]


def decay(n: int, k: float = 8.0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    return np.exp(-k * t).astype(np.float32)


def lowpass(x: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return x
    k = np.ones(width, dtype=np.float32) / width
    return np.convolve(x, k, mode="same").astype(np.float32)


def highpass(x: np.ndarray, width: int) -> np.ndarray:
    return (x - lowpass(x, width)).astype(np.float32)


def mix(*parts: np.ndarray) -> np.ndarray:
    n = max(len(p) for p in parts)
    out = np.zeros(n, dtype=np.float32)
    for p in parts:
        out[: len(p)] += p
    return out


def concat(*parts: np.ndarray) -> np.ndarray:
    return np.concatenate(parts).astype(np.float32)


def silence(dur: float) -> np.ndarray:
    return np.zeros(_n(dur), dtype=np.float32)


def vibrato(base: float, dur: float, rate: float = 6.0, depth: float = 0.02) -> np.ndarray:
    t = np.arange(_n(dur), dtype=np.float32) / SR
    return base * (1 + depth * np.sin(2 * np.pi * rate * t))


def formant_voice(f0, dur: float, formants=((500, 1.0), (900, 0.6)), bw: float = 140.0) -> np.ndarray:
    """Aditivní syntéza samohlásky – harmonické vážené podle formantů (kvok, kokrhání)."""
    n = _n(dur)
    if np.isscalar(f0):
        f0_arr = np.full(n, f0, dtype=np.float32)
    else:
        f0_arr = np.asarray(f0, dtype=np.float32)
        if len(f0_arr) < n:
            f0_arr = np.concatenate([f0_arr, np.full(n - len(f0_arr), f0_arr[-1], dtype=np.float32)])
        f0_arr = f0_arr[:n]
    ph = np.cumsum(f0_arr) / SR
    out = np.zeros(n, dtype=np.float32)
    mean_f0 = float(np.mean(f0_arr))
    for k in range(1, 24):
        fk = k * mean_f0
        if fk > SR / 2 - 500:
            break
        amp = 0.0
        for fc, g in formants:
            amp += g * math.exp(-((fk - fc) / bw) ** 2)
        amp += 0.04 / k
        if amp < 0.01:
            continue
        out += amp * np.sin(2 * np.pi * k * ph).astype(np.float32)
    m = np.max(np.abs(out)) or 1.0
    return out / m


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    if m < 1e-6:
        return x
    return (x * (peak / m)).astype(np.float32)


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------------------------------------------------------------------
# SFX recepty
# ---------------------------------------------------------------------------

def sfx_library() -> dict[str, np.ndarray]:
    L: dict[str, np.ndarray] = {}

    def add(name, x, peak=0.8):
        L[name] = normalize(x, peak)

    # plop – smrt nepřítele (3 výšky)
    for i, base in enumerate((620, 700, 560)):
        n = _n(0.09)
        x = wave("square", sweep(base, 140, 0.09, 0.6), 0.09, 0.4) * decay(n, 30)
        x += noise(0.09, i) * decay(n, 60) * 0.3
        add(f"plop{i}", lowpass(x, 3), 0.55)
    n = _n(0.05)
    add("hit", lowpass(noise(0.05, 3), 2) * decay(n, 70) + wave("square", 180, 0.05) * decay(n, 50) * 0.5, 0.45)
    n = _n(0.13)
    add("throw", lowpass(noise(0.13, 4), 6) * env(n, 0.04, 0.03, 0.6, 0.05) + wave("tri", sweep(300, 700, 0.13), 0.13) * 0.3 * decay(n, 15), 0.5)
    n = _n(0.45)
    boom = lowpass(noise(0.45, 5), 10) * decay(n, 9) + wave("sine", sweep(110, 35, 0.45), 0.45) * decay(n, 7)
    add("explode", boom, 0.85)
    n = _n(1.1)
    nuke = lowpass(noise(1.1, 6), 18) * decay(n, 3.5) + wave("sine", sweep(90, 25, 1.1), 1.1) * decay(n, 3) * 1.2
    add("nuke", nuke, 0.95)
    n = _n(0.1)
    add("water", wave("tri", sweep(900, 1500, 0.1), 0.1) * decay(n, 25) + lowpass(noise(0.1, 7), 3) * decay(n, 40) * 0.25, 0.45)
    n = _n(0.16)
    add("whip", highpass(noise(0.16, 8), 8) * env(n, 0.06, 0.02, 0.5, 0.06), 0.5)
    n = _n(0.22)
    add("shotgun", lowpass(noise(0.22, 9), 4) * decay(n, 16) + wave("sine", sweep(160, 50, 0.22), 0.22) * decay(n, 14), 0.75)
    n = _n(0.32)
    add("wave", wave("sine", sweep(380, 90, 0.32), 0.32) * decay(n, 8) + wave("tri", sweep(760, 180, 0.32), 0.32) * 0.3 * decay(n, 10), 0.6)
    n = _n(0.45)
    add("laser_charge", wave("square", sweep(180, 1000, 0.45, 2.0), 0.45, 0.3) * env(n, 0.3, 0.05, 0.8, 0.05) * 0.6, 0.35)
    n = _n(0.4)
    las = wave("saw", vibrato(130, 0.4, 30, 0.05), 0.4) + wave("square", 261, 0.4, 0.25) * 0.5 + noise(0.4, 10) * 0.3
    add("laser", lowpass(las, 2) * env(n, 0.01, 0.05, 0.8, 0.15), 0.5)
    n = _n(0.16)
    crack = noise(0.16, 11) * (np.random.default_rng(1).random(n) > 0.6) * decay(n, 18)
    add("zap", crack + wave("saw", sweep(1800, 300, 0.16), 0.16) * 0.3 * decay(n, 25), 0.55)
    n = _n(0.45)
    add("cloud", lowpass(noise(0.45, 12), 12) * env(n, 0.1, 0.1, 0.6, 0.2), 0.35)
    howl_f = np.concatenate([sweep(320, 620, 0.35), sweep(620, 560, 0.35), sweep(560, 380, 0.3)])
    howl_f = howl_f * (1 + 0.025 * np.sin(np.arange(len(howl_f)) / SR * 2 * np.pi * 6))
    n = len(howl_f)
    add("howl", formant_voice(howl_f, n / SR, ((600, 1.0), (1000, 0.4)), 160) * env(n, 0.1, 0.1, 0.8, 0.25), 0.55)
    n = _n(0.7)
    add("whistle", wave("sine", sweep(1800, 500, 0.7, 0.8), 0.7) * env(n, 0.02, 0.1, 0.7, 0.1) * 0.6, 0.35)
    for i, f in enumerate((1250, 1400, 1580)):
        n = _n(0.045)
        add(f"pickup{i}", wave("square", f, 0.045, 0.25) * decay(n, 40), 0.25)
    notes = [72, 76, 79, 84]
    arp = concat(*[wave("square", midi(m), 0.075, 0.5) * decay(_n(0.075), 12) for m in notes])
    arp = concat(arp, wave("square", midi(88), 0.25, 0.5) * decay(_n(0.25), 6))
    add("levelup", arp, 0.45)
    ch = concat(*[wave("tri", midi(m), 0.06) * decay(_n(0.06), 10) for m in (67, 71, 74, 79, 83, 86)])
    ch = mix(ch, wave("sine", midi(91), 0.6) * decay(_n(0.6), 5) * 0.4)
    add("chest", ch, 0.5)
    # kokrhání: ki-ki-ri-kíí
    syl = []
    for f, d in ((680, 0.11), (720, 0.11), (820, 0.13), (980, 0.5)):
        fr = vibrato(f, d, 9, 0.03) if d > 0.2 else sweep(f * 0.9, f, d)
        v = formant_voice(fr, d, ((1100, 1.0), (2400, 0.5), (700, 0.4)), 220)
        syl.append(v * env(_n(d), 0.01, 0.03, 0.85, 0.05 if d < 0.2 else 0.18))
        syl.append(silence(0.025))
    add("crow", concat(*syl), 0.7)
    # kvok – formantová samohláska „o“
    for i, f in enumerate((420, 470, 380)):
        d1 = 0.07
        v1 = formant_voice(sweep(f * 1.15, f * 0.85, d1), d1, ((480, 1.0), (850, 0.55)), 130)
        v1 = v1 * env(_n(d1), 0.004, 0.02, 0.7, 0.03)
        d2 = 0.06
        v2 = formant_voice(sweep(f * 0.95, f * 0.75, d2), d2, ((450, 1.0), (800, 0.5)), 130) * env(_n(d2), 0.004, 0.02, 0.6, 0.03)
        add(f"cluck{i}", concat(v1, silence(0.03), v2), 0.5)
    d = 0.32
    v = formant_voice(vibrato(720, d, 14, 0.06), d, ((850, 1.0), (1250, 0.7)), 170)
    add("cluck_hurt", concat(formant_voice(sweep(600, 900, 0.07), 0.07, ((800, 1), (1200, 0.6)), 160) * env(_n(0.07), 0.005, 0.02, 0.8, 0.02),
                             v * env(_n(d), 0.01, 0.05, 0.8, 0.15)), 0.65)
    n = _n(1.0)
    roar = wave("saw", vibrato(75, 1.0, 11, 0.08), 1.0) + lowpass(noise(1.0, 14), 6) * 0.6 + wave("saw", vibrato(112, 1.0, 7, 0.05), 1.0) * 0.5
    add("roar", lowpass(roar, 3) * env(n, 0.08, 0.1, 0.8, 0.35), 0.8)
    n = _n(0.12)
    beep = concat(wave("square", 880, 0.12) * env(n, 0.005, 0.01, 0.8, 0.02), silence(0.05),
                  wave("square", 660, 0.12) * env(n, 0.005, 0.01, 0.8, 0.02))
    add("warning", concat(beep, silence(0.06), beep), 0.4)
    n = _n(0.035)
    add("click", wave("square", 900, 0.035, 0.3) * decay(n, 60) + noise(0.035, 15) * decay(n, 120) * 0.3, 0.35)
    add("back", wave("square", 500, 0.05, 0.3) * decay(_n(0.05), 50), 0.35)
    add("coin", concat(wave("square", midi(83), 0.06, 0.5) * 0.8, wave("square", midi(88), 0.2, 0.5) * decay(_n(0.2), 10)), 0.35)
    mel = [(67, 0.12), (72, 0.12), (76, 0.12), (79, 0.24), (76, 0.12), (79, 0.5)]
    add("victory", concat(*[wave("square", midi(m), d, 0.5) * env(_n(d), 0.005, 0.03, 0.7, 0.04) for m, d in mel]), 0.5)
    mel = [(67, 0.25), (66, 0.25), (65, 0.25), (64, 0.7)]
    add("defeat", concat(*[wave("saw", vibrato(midi(m), d, 5, 0.012), d) * env(_n(d), 0.02, 0.05, 0.7, 0.08) for m, d in mel]), 0.45)
    sh = concat(*[wave("sine", midi(m), 0.05) * decay(_n(0.05), 15) for m in (84, 88, 91, 96, 91, 96, 100)])
    add("gold", sh, 0.4)
    n = _n(0.6)
    add("slowmo", wave("sine", sweep(400, 60, 0.6), 0.6) * env(n, 0.02, 0.1, 0.7, 0.3) + lowpass(noise(0.6, 16), 20) * 0.4 * decay(n, 4), 0.6)
    fr = concat(*[wave("sine", midi(m), 0.06) * decay(_n(0.06), 20) for m in (96, 103, 100, 108)])
    add("freeze", fr, 0.3)
    n = _n(0.08)
    add("bite", lowpass(noise(0.08, 17), 2) * decay(n, 35), 0.4)
    n = _n(0.3)
    add("teleport", wave("square", np.concatenate([sweep(300, 1500, 0.15), sweep(1500, 300, 0.15)]), 0.3, 0.3) * env(n, 0.01, 0.05, 0.6, 0.1), 0.35)
    n = _n(0.4)
    add("stomp", wave("sine", sweep(90, 30, 0.4), 0.4) * decay(n, 8) + lowpass(noise(0.4, 18), 14) * decay(n, 10), 0.9)
    n = _n(0.12)
    add("hop", wave("sine", sweep(200, 600, 0.12), 0.12) * decay(n, 20), 0.4)
    n = _n(0.14)
    add("spit", lowpass(noise(0.14, 19), 5) * env(n, 0.01, 0.03, 0.5, 0.06) + wave("sine", sweep(500, 200, 0.14), 0.14) * 0.4 * decay(n, 18), 0.4)
    rv = mix(*[wave("tri", sweep(midi(m) * 0.5, midi(m), 0.6), 0.6) * env(_n(0.6), 0.2, 0.1, 0.7, 0.2) for m in (60, 64, 67, 72)])
    add("revive", rv, 0.5)
    add("heal", concat(*[wave("sine", midi(m), 0.07) * decay(_n(0.07), 10) for m in (76, 79, 84)]), 0.35)
    n = _n(0.2)
    add("helmet", wave("square", sweep(1400, 900, 0.2), 0.2, 0.15) * decay(n, 18) + noise(0.2, 20) * decay(n, 50) * 0.3, 0.35)
    n = _n(0.25)
    add("fanfare", concat(*[wave("square", midi(m), 0.09, 0.5) * env(_n(0.09), 0.005, 0.02, 0.8, 0.03) for m in (72, 72, 72, 79)]), 0.4)
    n = _n(0.5)
    add("avalanche", lowpass(noise(0.5, 21), 30) * env(n, 0.15, 0.1, 0.8, 0.2), 0.7)
    n = _n(0.18)
    add("stamp", wave("square", sweep(140, 60, 0.18), 0.18) * decay(n, 15) + noise(0.18, 22) * decay(n, 40) * 0.6, 0.7)
    # Lesklé cetky: švih + skleněné „tink“ – vlastní zvuk, ať hod nezní jako sebraná mince (B-102)
    n = _n(0.12)
    add("trinket", highpass(noise(0.12, 23), 4) * env(n, 0.02, 0.02, 0.4, 0.05) * 0.5
        + wave("sine", sweep(2600, 3200, 0.12), 0.12) * decay(n, 45) * 0.35, 0.35)
    _ult_sounds(add)
    return L


def _honk(f0: float, dur: float) -> np.ndarray:
    """Husí „kejh“: nosová samohláska s chraplavým šumem."""
    v = formant_voice(sweep(f0 * 1.08, f0 * 0.92, dur), dur, ((650, 1.0), (1150, 0.8), (2500, 0.35)), 190)
    v = v + highpass(noise(dur, 31), 4) * 0.25
    return v * env(_n(dur), 0.01, 0.04, 0.8, dur * 0.35)


def _ult_sounds(add) -> None:
    """Zvuky ultimátek – každé zvíře má vlastní (Elvis dál „crow“)."""
    # slepice: „kdák“ + zlatá zvonkohra vzhůru + vzdálené bouchnutí
    cl = formant_voice(sweep(500, 380, 0.1), 0.1, ((480, 1.0), (850, 0.55)), 130) * env(_n(0.1), 0.004, 0.02, 0.7, 0.04)
    chimes = concat(*[wave("sine", midi(m), 0.07) * decay(_n(0.07), 12) for m in (84, 88, 91, 96, 100)])
    chimes = mix(chimes, wave("tri", midi(103), 0.5) * decay(_n(0.5), 6) * 0.5)
    add("ult_hen", concat(cl, silence(0.03), chimes), 0.6)
    # kachna: nabíhající vlna (šum) + dlouhé „KVÁÁÁK“
    n = _n(0.9)
    rush = lowpass(noise(0.9, 32), 9) * env(n, 0.25, 0.1, 0.8, 0.4)
    q = formant_voice(sweep(560, 390, 0.42), 0.42, ((900, 1.0), (1500, 0.6), (2600, 0.2)), 210)
    q = (q + wave("saw", sweep(280, 195, 0.42), 0.42) * 0.25) * env(_n(0.42), 0.01, 0.05, 0.8, 0.15)
    add("ult_duck", mix(rush * 0.8, concat(silence(0.05), q)), 0.75)
    # husa: dvojité kejhnutí + syčení
    hiss = highpass(noise(0.35, 33), 2) * env(_n(0.35), 0.05, 0.05, 0.6, 0.15) * 0.5
    add("ult_goose", concat(_honk(340, 0.17), silence(0.04), _honk(380, 0.24), hiss), 0.75)
    add("honk", _honk(360, 0.15), 0.55)
    # krocan: „hudry-hudry“ (rychle chvějivý formant) + buben
    d = 0.5
    t = np.arange(_n(d), dtype=np.float32) / SR
    gob = formant_voice(sweep(300, 240, d), d, ((600, 1.0), (1000, 0.6)), 160)
    gob = gob * (0.55 + 0.45 * np.sin(2 * np.pi * 24 * t)) * env(_n(d), 0.01, 0.05, 0.8, 0.12)
    drum = wave("sine", sweep(120, 45, 0.3), 0.3) * decay(_n(0.3), 10) + lowpass(noise(0.3, 34), 5) * decay(_n(0.3), 18)
    add("ult_turkey", mix(gob, concat(silence(0.42), drum)), 0.75)
    # páv: třpytivé glissando vzhůru + páví „mí-áu“
    gl = mix(*[wave("sine", vibrato(midi(m), 0.6, 7, 0.01), 0.6) * env(_n(0.6), 0.02 + i * 0.07, 0.05, 0.6, 0.25) * 0.5
               for i, m in enumerate((79, 84, 88, 91, 96))])
    call = formant_voice(np.concatenate([sweep(900, 1300, 0.12), sweep(1300, 700, 0.28)]), 0.4,
                         ((1500, 1.0), (2800, 0.5)), 260) * env(_n(0.4), 0.01, 0.05, 0.8, 0.12)
    add("ult_peacock", mix(gl, concat(silence(0.3), call * 0.8)), 0.6)
    # tučňák: ledový vítr + krystalky
    n = _n(1.0)
    wind = highpass(lowpass(noise(1.0, 35), 3), 30) * env(n, 0.2, 0.1, 0.7, 0.45)
    cry = concat(*[wave("sine", midi(m), 0.09) * decay(_n(0.09), 18) for m in (96, 103, 100, 108, 105)])
    add("ult_penguin", mix(wind, concat(silence(0.15), cry * 0.7)), 0.6)
    # straka: „čača-čača“ (rychlé ostré cvrčky) + cinkot mincí
    parts = []
    for i in range(6):
        d = 0.055
        c = highpass(noise(d, 40 + i), 2) * decay(_n(d), 30) * 0.6
        c = c + wave("square", sweep(2300 - i * 60, 1500, d), d, 0.3) * decay(_n(d), 25) * 0.5
        parts += [c, silence(0.035 if i % 2 == 0 else 0.07)]
    jingle = concat(*[wave("sine", midi(m), 0.08) * decay(_n(0.08), 14) for m in (88, 95, 91, 100)])
    add("ult_magpie", concat(*parts, jingle), 0.6)
    # roztříštění ledu
    n = _n(0.35)
    sh = highpass(noise(0.35, 36), 2) * decay(n, 14)
    pings = mix(*[concat(silence(0.02 * i), wave("sine", f, 0.2) * decay(_n(0.2), 20)) for i, f in
                  enumerate((2100, 2900, 1700, 3400, 2500))])
    add("shatter", mix(sh, pings * 0.5), 0.6)


# ---------------------------------------------------------------------------
# HUDBA – generátor vrstvených smyček
# ---------------------------------------------------------------------------
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixo": [0, 2, 4, 5, 7, 9, 10],
    "phryg": [0, 1, 3, 5, 7, 8, 10],
}


def _chord_tones(root_deg: int, scale: list[int]) -> list[int]:
    return [scale[(root_deg + i) % 7] + 12 * ((root_deg + i) // 7) for i in (0, 2, 4)]


def _pluck(freq: float, dur: float, bright: float = 1.0) -> np.ndarray:
    n = _n(dur)
    x = wave("saw", freq, dur) * 0.6 + wave("square", freq * 2, dur, 0.3) * 0.25 * bright
    x += wave("tri", freq * 0.5, dur) * 0.2
    return lowpass(x, 2) * decay(n, 9.0)


def _fiddle(freq: float, dur: float) -> np.ndarray:
    n = _n(dur)
    x = wave("saw", vibrato(freq, dur, 5.5, 0.012), dur)
    return lowpass(x, 3) * env(n, 0.05, 0.05, 0.75, min(0.08, dur * 0.3))


def _kick(dur=0.18):
    n = _n(dur)
    return wave("sine", sweep(140, 40, dur, 0.5), dur) * decay(n, 16)


def _snare(dur=0.14, seed=1):
    n = _n(dur)
    return highpass(noise(dur, seed), 3) * decay(n, 22) * 0.7 + wave("tri", 190, dur) * decay(n, 30) * 0.4


def _hat(dur=0.04, seed=2):
    n = _n(dur)
    return highpass(noise(dur, seed), 2) * decay(n, 90) * 0.35


def _clank(dur=0.1, seed=3):
    n = _n(dur)
    return (wave("square", 1150, dur, 0.1) * 0.5 + highpass(noise(dur, seed), 2) * 0.5) * decay(n, 35)


def make_theme(spec: dict) -> list[np.ndarray]:
    """Vrátí 4 vrstvy (bas+kopák, bicí, melodie, „hype“) stejné délky."""
    rng = random.Random(spec.get("seed", 1))
    bpm = spec["bpm"]
    beat = 60.0 / bpm
    bars = spec.get("bars", 8)
    steps_per_bar = 8   # osminy
    step = beat / 2
    total = _n(bars * 4 * beat)
    scale = SCALES[spec.get("scale", "major")]
    root = spec.get("root", 55)
    prog = spec.get("prog", [0, 3, 4, 0])
    style = spec.get("style", "folk")
    layers = [np.zeros(total + SR, dtype=np.float32) for _ in range(4)]

    def put(layer: int, sig: np.ndarray, t: float, gain: float = 1.0):
        i = int(t * SR)
        end = min(len(layers[layer]), i + len(sig))
        if end > i:
            layers[layer][i:end] += sig[: end - i] * gain

    # motiv melodie – opakuje se s variací
    motif = []
    for s in range(steps_per_bar * 2):
        if rng.random() < (0.55 if s % 2 == 0 else 0.3):
            motif.append((s, rng.choice([0, 1, 2, 2, 4, 4, 5, 7]), rng.choice([1, 1, 2, 2, 3])))
    for bar in range(bars):
        deg = prog[bar % len(prog)]
        tones = _chord_tones(deg, scale)
        t0 = bar * 4 * beat
        # vrstva 0: bas + kopák
        for s in range(steps_per_bar):
            t = t0 + s * step
            if style == "industrial":
                if s % 2 == 0:
                    put(0, _kick(), t, 0.9)
            elif s in (0, 4) or (s == 6 and bar % 2 == 1):
                put(0, _kick(), t, 0.9)
            if s % 2 == 0:
                note = root - 12 + tones[0] if s % 4 == 0 else root - 12 + tones[2] - 12 * (s % 8 == 6)
                f = midi(note)
                put(0, wave("tri", f, step * 1.8) * env(_n(step * 1.8), 0.005, 0.05, 0.7, 0.05) * 0.8
                    + wave("square", f, step * 1.8, 0.5) * env(_n(step * 1.8), 0.005, 0.05, 0.5, 0.05) * 0.15, t)
        # vrstva 1: bicí
        for s in range(steps_per_bar):
            t = t0 + s * step
            put(1, _hat(seed=s + bar), t, 0.9 if s % 2 else 0.6)
            if s in (2, 6):
                put(1, _snare(seed=bar), t, 0.85)
            if style == "industrial" and s in (3, 7):
                put(1, _clank(seed=bar + s), t, 0.6)
            if style == "boss" and s % 2 == 1:
                put(1, _snare(0.06, seed=s), t, 0.3)
        # vrstva 2: melodie
        half = (bar % 2) * steps_per_bar
        for s, sdeg, length in motif:
            if not (half <= s < half + steps_per_bar):
                continue
            ss = s - half
            t = t0 + ss * step
            var = 0 if bar < bars // 2 else rng.choice([0, 0, 1, -1])
            idx = (deg + sdeg + var)
            note = root + 12 + scale[idx % 7] + 12 * (idx // 7)
            d = step * length * 0.95
            if spec.get("lead") == "pluck":
                sig = _pluck(midi(note), d + 0.15)
            elif spec.get("lead") == "fiddle":
                sig = _fiddle(midi(note), d)
            else:
                sig = wave("square", midi(note), d, 0.25) * env(_n(d), 0.005, 0.04, 0.6, 0.04)
            put(2, sig, t, 0.55)
        # vrstva 3: hype – banjo arpeggia / housle
        for s in range(steps_per_bar):
            t = t0 + s * step
            tone = tones[[0, 1, 2, 1, 0, 2, 1, 2][s]]
            note = root + tone + (12 if s % 4 == 3 else 0)
            if style == "boss":
                put(3, _fiddle(midi(note + 12), step * 0.95), t, 0.35)
            else:
                put(3, _pluck(midi(note), step * 2, 1.4), t, 0.4)
    out = []
    for lay in layers:
        x = lay[:total]
        # crossfade konce do začátku (bez lupnutí ve smyčce)
        tail = lay[total: total + _n(0.3)]
        x[: len(tail)] += tail * np.linspace(1, 0, len(tail), dtype=np.float32)
        out.append(x)
    peak = max(float(np.max(np.abs(sum(out)))), 1e-3)
    return [(x * (0.85 / peak)).astype(np.float32) for x in out]


THEMES = {
    "menu": dict(bpm=104, root=60, scale="major", prog=[0, 3, 4, 3], lead="pluck", style="folk", seed=3),
    "farm": dict(bpm=128, root=55, scale="mixo", prog=[0, 0, 3, 4], lead="pluck", style="folk", seed=11),
    "forest": dict(bpm=112, root=57, scale="minor", prog=[0, 5, 3, 4], lead="square", style="folk", seed=23),
    "city": dict(bpm=134, root=62, scale="dorian", prog=[0, 3, 0, 4], lead="square", style="folk", seed=37),
    "mountain": dict(bpm=120, root=52, scale="minor", prog=[0, 2, 5, 4], lead="fiddle", style="folk", seed=41),
    "factory": dict(bpm=142, root=48, scale="phryg", prog=[0, 1, 0, 5], lead="square", style="industrial", seed=53),
    "boss": dict(bpm=152, root=57, scale="minor", prog=[0, 5, 6, 4], lead="fiddle", style="boss", seed=67),
}
