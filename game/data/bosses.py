"""Bossové, jejich hlášky a biomové varianty finálního Zombie Kohouta."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BossDef:
    id: str
    name: str
    desc: str
    sprite: str
    hp: float
    speed: float
    dmg: float
    radius: float
    intro: str
    lines: tuple = ()
    death: str = ""
    phase_hp: tuple = ()       # pro vícefázové bosse (poměry HP)
    extra: dict = field(default_factory=dict)


BOSSES: dict[str, BossDef] = {b.id: b for b in [
    BossDef("spy_fox", "Pan Liška Špión", "Mistr převleků. Teleportuje se a útočí zezadu.",
            "spy_fox", 2000, 95, 12, 26,
            "Jmenuji se Liška. Pan Liška.",
            ("Za tebou!", "Tvoje vejce jsou kompromitována.", "Jsem neviditelný! …skoro.", "Licence ke kvokání odebrána."),
            "Mise… selhala…"),
    BossDef("rabbit", "Králík Zabiják", "Roztomilý chlupáček. S mrkvemi jako dýky.",
            "rabbit", 4000, 125, 18, 26,
            "Jsem jen roztomilý zajíček. Hehe.",
            ("Mrkev do oka!", "Hop! Hop! HOP!", "Velikonoce letos nebudou!", "Ňam ňam, kuřátko."),
            "Řekni Velikonocům… že jsem je měl rád."),
    BossDef("zombie_bear", "Obří Zombie Medvěd", "Probuzený ze zimního spánku. Hladový. Velmi hladový.",
            "zombie_bear", 13000, 42, 30, 46,
            "MÉĎA… HLADOVÝ.",
            ("Zem se třese, kuře se klepe!", "MED! KDE JE MŮJ MED?!", "BRUMBRUM!"),
            "Hibernace… navždy…"),
    BossDef("wolf_alpha", "Vlčí Alfa", "Vůdce smečky. Nikdy nebojuje sám.",
            "wolf_alpha", 36000, 88, 26, 36,
            "Smečko, k noze!",
            ("Au-uuuuu!", "Obklíčit kuře!", "Alfa nikdy neprohrává!"),
            "Kdo teď bude alfa…?"),
    BossDef("zombie_rooster", "ZOMBIE KOHOUT", "Kdysi král dvora. Teď nemrtvý tyran, který nesnáší svítání.",
            "zombie_rooster", 120000, 80, 30, 40,
            "Na tomhle dvoře může kokrhat jen JEDEN!",
            ("KIKIRIKÍÍÍ!", "Prší slepice! Haleluja!", "TEĎ UŽ JSEM OPRAVDU NAŠTVANÝ!", "Slunce nevyjde!"),
            "Kikiri… kí… (vychází slunce)",
            phase_hp=(0.3, 0.33, 0.37)),
]}

BOSS_ORDER = ["spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster"]

# Varianta finálního bosse podle biomu: jméno, tónování, co padá z nebe ve fázi 2
FINAL_VARIANTS = {
    "farm": dict(name="ZOMBIE KOHOUT", tint=None, rain="zchick",
                 quote="Na tomhle dvoře může kokrhat jen JEDEN!"),
    "forest": dict(name="KOHOUT MLHOŠ", tint=(150, 190, 255), rain="bat",
                   quote="Z mlhy jsem přišel, v mlze tě sním!"),
    "city": dict(name="KOHOUT KMOTR", tint=(255, 200, 120), rain="rat",
                 quote="Udělám ti nabídku, kterou nemůžeš odkvokat."),
    "mountain": dict(name="KOHOUT YETTI", tint=(220, 240, 255), rain="snow_fox",
                     quote="Na horách je zima. Pro tebe věčná!"),
    "factory": dict(name="ROBOKOHOUT 3000", tint=(190, 200, 230), rain="robo_fox",
                    quote="ZAHAJUJI PROTOKOL: KUŘECÍ ŘÍZEK."),
}
