"""Nepřátelé – běžní, elitní, vyvolaní a biomové varianty."""
from __future__ import annotations

from dataclasses import dataclass

# AI kódy (int kvůli rychlosti v hot loopu)
AI_CHASE, AI_SPIT, AI_BAT, AI_NECRO, AI_BERSERK, AI_PROP, AI_BOSS = range(7)


@dataclass(frozen=True)
class EnemyDef:
    id: str
    name: str
    desc: str
    sprite: str
    hp: float
    speed: float
    dmg: float
    radius: float
    xp: int
    ai: int = AI_CHASE
    kb_res: float = 0.0
    elite: bool = False
    armor_hp: float = 0.0
    flyer: bool = False
    explode: float = 0.0          # poloměr výbuchu po smrti
    prop: bool = False
    fluff: tuple = (240, 150, 70)  # barva chlupů/peří při smrti
    collect: bool = True           # objevuje se ve sbírce


ENEMIES: dict[str, EnemyDef] = {e.id: e for e in [
    EnemyDef("fox", "Liška Zombie", "Pomalá, hloupá, ale v davech nebezpečná. Vstala z hrobu kvůli kuřeti.",
             "fox", 10, 52, 8, 14, 1),
    EnemyDef("fast_fox", "Rychlá liška", "Sprintuje jako o život. Vydrží jeden zásah.",
             "fast_fox", 5, 128, 6, 11, 1, fluff=(250, 190, 90)),
    EnemyDef("armored_fox", "Obrněná liška", "Plechová helma z kbelíku. Nejdřív musíš prorazit helmu.",
             "armored_fox", 16, 48, 10, 14, 3, armor_hp=30, fluff=(200, 205, 220)),
    EnemyDef("spitter", "Plivající liška", "Drží si odstup a plive zelený sliz. Fuj.",
             "spitter", 14, 56, 7, 14, 2, ai=AI_SPIT, fluff=(140, 230, 80)),
    EnemyDef("exploder", "Explodující liška", "Po smrti vybuchne. Nezabíjej ji u sebe!",
             "exploder", 12, 72, 7, 14, 2, explode=64, fluff=(255, 120, 60)),
    EnemyDef("wolf", "Vlk Zombie", "Velký, tlustý a vytrvalý tank.",
             "wolf", 70, 60, 14, 19, 6, kb_res=0.6, fluff=(160, 160, 175)),
    EnemyDef("bat", "Netopýr", "Létá přes překážky a kličkuje.",
             "bat", 7, 96, 6, 11, 1, ai=AI_BAT, flyer=True, fluff=(130, 70, 160)),
    EnemyDef("giant_fox", "Obří liška", "Dvakrát větší, dvakrát naštvanější. Nese bednu s pokladem.",
             "giant_fox", 520, 52, 20, 30, 40, kb_res=0.95, elite=True, fluff=(200, 90, 50)),
    EnemyDef("owl", "Necromancer Sova", "Oživuje padlé lišky. Hú-hú-hrůza.",
             "owl", 380, 64, 12, 20, 40, ai=AI_NECRO, kb_res=0.8, elite=True, fluff=(170, 100, 210)),
    EnemyDef("bear", "Medvěd Berserker", "Při polovině zdraví začne zuřit.",
             "bear", 820, 46, 24, 26, 50, ai=AI_BERSERK, kb_res=0.9, elite=True, fluff=(130, 90, 60)),
    EnemyDef("skeleton_fox", "Kostlivá liška", "Oživená sovou. Drží pohromadě jen ze zvyku.",
             "skeleton_fox", 7, 66, 7, 13, 1, fluff=(220, 230, 225)),
    EnemyDef("zchick", "Zombie slepice", "Padá z nebe, když Zombie Kohout kokrhá. Bývalé kamarádky.",
             "zchick", 10, 112, 6, 10, 1, fluff=(170, 205, 150)),
    EnemyDef("barrel", "Výbušný sud", "Střel do něj a uteč.", "barrel", 12, 0, 0, 14, 0, ai=AI_PROP,
             explode=90, prop=True, fluff=(220, 60, 50), collect=False),
    EnemyDef("snow_fox", "Sněžná liška", "Horská varianta. Klouže po sněhu rychleji.",
             "snow_fox", 13, 64, 9, 14, 1, fluff=(235, 240, 250)),
    EnemyDef("robo_fox", "Robo-liška", "Tovární model L-15. Obrněná a vytrvalá.",
             "robo_fox", 28, 50, 12, 14, 4, armor_hp=40, fluff=(180, 185, 200)),
    EnemyDef("rat", "Městský potkan", "Ve městě je jich víc než lidí.",
             "rat", 4, 140, 5, 9, 1, fluff=(150, 140, 150)),
    EnemyDef("mist_wolf", "Mlžný vlk", "Vynoří se z mlhy lesa, když to nejmíň čekáš.",
             "mist_wolf", 55, 72, 13, 19, 5, kb_res=0.5, fluff=(190, 205, 230)),
]}

COLLECT_ENEMIES = [e.id for e in ENEMIES.values() if e.collect]
