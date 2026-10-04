"""Ultimátky zvířat – jedna aktivní schopnost na zvíře (tlačítko vpravo dole / mezerník).

Nová ultimátka = řádek v ULTIMATES + jedna funkce `@effect("id")` v `game/world/ultimates.py`.
Parametry v `params` čte jen funkce efektu; společná pravidla (bossové, nabíjení) jsou níže.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ULT_KILLS = 70              # výchozí počet zabití na plné nabití (Elvisova pasivka ho dělí dvěma)
ULT_MIN_CD = 6.0            # výchozí nejkratší doba nabití (s) – strop nabití roste od nuly po použití (B-73)
ULT_START = 0.5             # run začíná s napůl nabitou ultimátkou – hráč ji pozná už v první minutě
ULT_BOSS_CAP = 0.04         # jedna aktivace ubere bossovi nejvýš 4 % max. HP – souboj se nedá přeskočit
ULT_CLOCK_STEP = 0.08       # Budík: −8 % nejkratší doby nabití za úroveň…
ULT_CLOCK_MIN = 0.6         # …nejvýš −40 %, a nikdy pod `cd_floor` ultimátky (B-91)
ULT_NAME_GAP = 20.0         # název ultimátky se ukáže nejvýš jednou za 20 s – první použití velkým bannerem (B-94)


@dataclass(frozen=True)
class UltDef:
    id: str
    name: str                   # celý název – banner při aktivaci
    short: str                  # krátký nápis pod tlačítkem (max. ~10 znaků)
    desc: str                   # popis pro výběr zvířete
    shout: str                  # výkřik nad zvířetem při aktivaci
    icon: str                   # ikona v gfx/icons.py
    color: tuple                # barva tlačítka, banneru a efektů
    sound: str                  # zvuk v audio/synth.py
    kills: int = ULT_KILLS      # zabití na plné nabití
    min_cd: float = ULT_MIN_CD  # nejkratší doba nabití (s)
    cd_floor: float = 0.0       # nejkratší možný rozestup použití i s Budíkem a pasivkou zvířete (s) – omezení
                                # davu nesmí trvat déle než nabití, jinak je dav trvale vyřazený (B-91)
    evo: str = ""               # evoluce startovní zbraně, která ultimátku posílí
    shake: float = 0.4          # třes kamery při aktivaci (přes Camera.shake se stropem)
    slowmo: float = 0.0         # krátké zpomalení času při aktivaci (s reálného času, 0 = bez)
    params: dict = field(default_factory=dict)
    evo_params: dict = field(default_factory=dict)   # přepisy parametrů s evolucí startovní zbraně


ULTIMATES: dict[str, UltDef] = {u.id: u for u in [
    UltDef("egg_rain", "Zlatá nadílka", "NADÍLKA",
           "Z nebe naprší zlatá vejce na lišky kolem. Co padne, dá dvojité XP.",
           "Kdák-kdák-BUM!", "ult_egg_rain", (255, 206, 64), "ult_hen",
           kills=70, min_cd=8.0, cd_floor=5.0, evo="golden_bomb", shake=0.3,
           params=dict(eggs=14, near=5, spread=1.6, range=330, radius=58, dmg=30, hp_pct=0.35, kb=160, stun=0.5,
                       xp_bonus=1.0),
           evo_params=dict(eggs=18)),
    UltDef("flood", "Velká voda", "VLNA",
           "Obří vlna ve směru pohybu smete lišky s sebou a nechá je promočené.",
           "KVÁÁÁÁK!", "ult_flood", (90, 196, 255), "ult_duck",
           kills=65, min_cd=8.0, cd_floor=5.0, evo="fire_hose", shake=0.35,
           params=dict(length=560, speed=520, half_w=210, dmg=25, hp_pct=0.40, slow=0.6, slow_t=4.0,
                       crash=10, crash_pct=0.20, crash_stun=0.8, elite_carry=0.4,
                       splash=140, splash_dmg=15, splash_pct=0.15, splash_kb=320, splash_stun=0.6),
           evo_params=dict(length=700, half_w=260)),
    UltDef("goose_fury", "Husí řádění", "ŘÁDĚNÍ",
           "Na 3 s nesmrtelná a rychlejší, kejhnutím rozhází lišky a nakonec je omráčí.",
           "KEJH! KEJH!", "ult_goose_fury", (255, 108, 120), "ult_goose",
           kills=75, min_cd=14.0, cd_floor=10.0, evo="goose_rage", shake=0.3,
           params=dict(dur=3.0, speed=1.35, pulse=0.6, radius=150, dmg=22, hp_pct=0.12, kb=420, stun=0.6,
                       trample=10, trample_pct=0.10, end_r=230, end_dmg=20, end_pct=0.10, end_kb=520,
                       end_stun=1.6),
           evo_params=dict(dur=4.0)),
    UltDef("thanksgiving", "Operace Díkůvzdání", "PALBA",
           "Salvy ostrých brků do všech stran. Krocaní kritické zásahy platí.",
           "HUDRY-HUDRY!", "ult_thanksgiving", (240, 84, 70), "ult_turkey",
           kills=70, min_cd=7.0, cd_floor=5.0, evo="gatling", shake=0.35,
           params=dict(salvos=4, gap=0.22, count=20, speed=520, pierce=2, life=1.25, dmg_hp=0.8),
           evo_params=dict(salvos=5, count=24)),
    UltDef("kikiriki", "Královské KIKIRIKÍ", "KIKIRIKÍ",
           "Původní kokrhání: odhodí a omráčí lišky kolem a smete jejich sliz.",
           "KIKIRIKÍ!", "ult_kikiriki", (255, 196, 70), "crow",
           kills=70, min_cd=6.0, cd_floor=3.0, evo="rock_concert", shake=0.6,
           params=dict(radius=290, dmg=40, hp_pct=0.25, kb=560, stun=2.2, invuln=1.0, echo=0),
           evo_params=dict(echo=1)),
    UltDef("hypno", "Božská krása", "HYPNÓZA",
           "Lišky kolem se zamilují a 5 s bojují za Divu proti ostatním.",
           "Zírejte na mě!", "ult_hypno", (214, 120, 255), "ult_peacock",
           kills=75, min_cd=12.0, cd_floor=8.0, evo="rainbow_show", shake=0.25, slowmo=0.12,
           params=dict(radius=280, grow=0.5, dur=5.0, max_n=50, hit=2.0, hit_pct=0.12, hit_cd=0.45, seek=260,
                       guard=150, end_stun=0.8),
           evo_params=dict(radius=340, dur=6.5)),
    UltDef("ice_age", "Doba ledová", "MRAZ",
           "Ledová bouře kolem tučňáka: mrazí, točí lišky dokola a nakonec je roztříští.",
           "Brrrr!", "ult_ice_age", (170, 226, 255), "ult_penguin",
           kills=75, min_cd=12.0, cd_floor=8.0, evo="frozen_tsunami", shake=0.3,
           params=dict(dur=3.0, radius=215, tick=0.25, dmg=6, hp_pct=0.015, swirl=150, drift=35,
                       boss_slow=0.4, end_dmg=20, end_pct=0.12, end_kb=300, end_freeze=1.2),
           evo_params=dict(dur=4.5, radius=250)),
]}

# zvíře → ultimátka (chybějící zvíře dostane klasické kokrhání)
ULT_BY_CHAR = {"hen": "egg_rain", "duck": "flood", "goose": "goose_fury", "turkey": "thanksgiving",
               "rooster": "kikiriki", "peacock": "hypno", "penguin": "ice_age"}
DEFAULT_ULT = "kikiriki"


def ult_for(char_id: str, override: str | None = None) -> UltDef:
    uid = override if override in ULTIMATES else ULT_BY_CHAR.get(char_id, DEFAULT_ULT)
    return ULTIMATES[uid]
