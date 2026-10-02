"""Meta-progrese: Hnízdo, obtížnosti, výzvy, skiny, denní odměny, modifikátory."""
from __future__ import annotations

from dataclasses import dataclass

# --- Hnízdo (trvalá vylepšení za vejce) -------------------------------------------------
NEST_UPGRADES = [
    dict(id="hp", name="Silné kosti", desc="+8 % max. zdraví", icon="hp", step=0.08, costs=[120, 260, 480, 800, 1300]),
    dict(id="dmg", name="Ostrý zobák", desc="+6 % poškození", icon="dmg", step=0.06, costs=[150, 320, 600, 1000, 1600]),
    dict(id="speed", name="Běžecký trénink", desc="+4 % rychlost", icon="speed", step=0.04, costs=[100, 220, 420, 700, 1100]),
    dict(id="magnet", name="Zrní-radar", desc="+12 % dosah sběru", icon="magnet", step=0.12, costs=[80, 180, 340, 560, 900]),
    dict(id="xp", name="Moudrost předků", desc="+6 % zkušeností", icon="xp", step=0.06, costs=[140, 300, 560, 920, 1500]),
    dict(id="reroll", name="Kostka osudu", desc="+1 rerol karet", icon="reroll", step=1, costs=[200, 400, 700, 1100, 1700]),
]
NEST_BY_ID = {u["id"]: u for u in NEST_UPGRADES}


# --- Obtížnosti -------------------------------------------------------------------------
@dataclass(frozen=True)
class Difficulty:
    id: str
    name: str
    hp: float
    dmg: float
    spawn: float
    reward: float
    unlock_text: str
    color: tuple


DIFFICULTIES = {d.id: d for d in [
    Difficulty("normal", "Normal", 1.0, 1.0, 1.0, 1.0, "", (120, 220, 90)),
    Difficulty("hard", "Hard", 1.6, 1.35, 1.2, 1.6, "Vyhraj run na Normal", (255, 170, 60)),
    Difficulty("nightmare", "Nightmare", 2.4, 1.7, 1.4, 2.4, "Vyhraj run na Hard", (220, 60, 90)),
]}
DIFF_ORDER = ["normal", "hard", "nightmare"]

# --- Výzvy a achievementy -----------------------------------------------------------------
# reward: (vejce, zlatá vejce) ; unlock: co odemyká
CHALLENGES = [
    dict(id="thousand", name="Tisíc lišek", desc="Zabij 1 000 lišek v jednom runu.", reward=(300, 2), unlock="char:peacock"),
    dict(id="first_dawn", name="První úsvit", desc="Vyhraj rychlý mód.", reward=(200, 1)),
    dict(id="full_night", name="Celá noc", desc="Vyhraj plný 10minutový mód.", reward=(600, 3)),
    dict(id="ascetic", name="Asketa", desc="Vyhraj run bez jediné pasivky.", reward=(400, 2)),
    dict(id="goose5", name="Husí kůže", desc="Přežij 5 minut jako Husa Gerta.", reward=(250, 1)),
    dict(id="evolve", name="Evoluce!", desc="Vyvij jakoukoli zbraň.", reward=(150, 1)),
    dict(id="crow10", name="Kokrhací mistr", desc="Použij kokrhání 10× v jednom runu.", reward=(200, 1)),
    dict(id="massacre", name="Masakr", desc="Zabij 50 nepřátel téměř naráz.", reward=(150, 1)),
    dict(id="arsenal", name="Arzenál", desc="Měj 6 zbraní najednou.", reward=(150, 1)),
    dict(id="nightmare", name="Noční můra", desc="Vyhraj na obtížnost Nightmare.", reward=(1000, 5)),
    dict(id="tourist", name="Turista", desc="Zahraj si všech 5 biomů.", reward=(300, 2)),
    dict(id="bossrush", name="Boss rush", desc="Poraz všechny bossy v týdenním boss rushi.", reward=(500, 3)),
    dict(id="factory", name="Továrník", desc="Vyhraj v Továrně na kuřata.", reward=(600, 3)),
    dict(id="untouchable", name="Nedotknutelná", desc="Přežij 3 minuty bez zásahu.", reward=(300, 2)),
    dict(id="critic", name="Krocaní kritik", desc="Dej 500 kritických zásahů v jednom runu jako Rambo.", reward=(250, 1)),
    dict(id="penguin", name="Kde se tu vzal?", desc="Najdi tajného tučňáka.", reward=(100, 1)),
    dict(id="level40", name="Vzdělaná slepice", desc="Dosáhni úrovně 40 v jednom runu.", reward=(300, 2)),
    dict(id="rich", name="Vaječný magnát", desc="Nasbírej celkem 10 000 vajec.", reward=(0, 3)),
]
CHALLENGE_BY_ID = {c["id"]: c for c in CHALLENGES}

# --- Skiny ----------------------------------------------------------------------------------
SKINS = [
    dict(id="pirate", name="Pirát", price=5, season=None),
    dict(id="cowboy", name="Kovboj", price=5, season=None),
    dict(id="astronaut", name="Astronaut", price=8, season=None),
    dict(id="ninja", name="Ninja", price=8, season=None),
    dict(id="pumpkin", name="Dýňová hlava", price=0, season="halloween"),
    dict(id="santa", name="Santa", price=0, season="christmas"),
    dict(id="bunny", name="Zajíček", price=0, season="easter"),
]
SKIN_BY_ID = {s["id"]: s for s in SKINS}

SEASONS = {
    "halloween": dict(name="Halloween", tint=(255, 150, 60), decor="pumpkin"),
    "christmas": dict(name="Vánoce", tint=(200, 230, 255), decor="gift"),
    "easter": dict(name="Velikonoce", tint=(255, 220, 240), decor="easter_egg"),
}

# --- Denní login (cyklus 7 dní) ------------------------------------------------------------
LOGIN_REWARDS = [
    dict(eggs=50), dict(tokens=1), dict(eggs=100), dict(tokens=1), dict(eggs=150), dict(tokens=2),
    dict(eggs=250, gold=1),
]

# --- Truhla za žeton ------------------------------------------------------------------------
CHEST_COST = 1

# --- Modifikátory denní výzvy ------------------------------------------------------------------
DAILY_MODIFIERS = [
    dict(id="speedy", name="Splašené lišky", desc="Nepřátelé jsou o 30 % rychlejší."),
    dict(id="glass", name="Skleněné kuře", desc="Poloviční zdraví, dvojnásobné poškození."),
    dict(id="horde", name="Horda", desc="O 50 % víc nepřátel, o 25 % víc XP."),
    dict(id="giants", name="Obři", desc="Nepřátelé jsou větší a mají víc zdraví, ale dávají víc XP."),
    dict(id="lucky", name="Šťastný den", desc="Všechny karty mají vyšší raritu."),
    dict(id="explosive", name="Ohňostroj", desc="Každá liška po smrti vybuchne."),
]
DAILY_MOD_BY_ID = {m["id"]: m for m in DAILY_MODIFIERS}

# Jména „sousedů“ pro lokální žebříček denní výzvy
NEIGHBOURS = ["Farmář Franta", "Babička Božka", "Kohout Karel", "Kačer Donát", "Husa Hedvika", "Krůta Klára",
              "Strejda Lojza", "Pes Alík", "Kocour Mikeš", "Prase Pepa", "Kráva Stáňa", "Koza Líza",
              "Beran Béďa", "Holub Hugo", "Králík Kuba"]

COLLECTION_REWARD_GOLD = 3      # za 100 % kategorie sbírky

# Ekonomika výsledků runu
EGGS_PER_10S = 2
EGGS_PER_10_KILLS = 1
EGGS_PER_MINIBOSS = 50
EGGS_FINAL_BOSS = 250
EGGS_WIN_BONUS = 150
