# Návrh updatu: LAST CHICKEN v1.1.0 (3. 10. 2026)

## Rozhodnutí
**Headline: „Nekonečná noc“ – nový mód, kde slunce nikdy nevyjde.** Odemkne se výhrou Plného módu.
Prvních 10 minut je stejných jako Plný mód, ale po porážce Zombie Kohouta noc pokračuje: přijde další kolo
bossů (silnějších), elity a formace se opakují, lišky dál sílí. Run končí jen smrtí – cílem je osobní rekord
času. Věta, kterou hráč zopakuje: *„Odemkl jsem Nekonečnou noc – zabil jsem kohouta dvakrát a vydržel 16 minut.“*

Podpůrné položky (S):
1. **Noční síla** – v Nekonečné noci dá každý level-up po dokončeném buildu (kdy dnes jen léčí) navíc trvalých
   +3 % poškození, bez přerušení hry. Ostatní módy beze změny.
2. **Rekord** – nejlepší čas se ukládá (`records.best_time_endless`), ukazuje se na tlačítku módu, v HUD během runu
   a ve výsledcích („NOVÝ REKORD!“).
3. **Výzva „Věčná tma“** – přežij 15 minut v Nekonečné noci (odměna vejce + zlatá vejce); 19. výzva.

## Proč (důkazy)
- Bot (Farma, Normal, slepice, bez Hnízda) vyhrál Plný mód 4/4 s **úplně vyvinutým buildem** (úroveň 49–58,
  6 evolucí, všechny pasivky na max., minimum HP 50–81 %) – po 10:00 + bossovi není kam hotový build nasadit.
- `PLAN.md` B-55: „build se v plném módu dokončí zhruba v 9:00–10:20… výplňové level-upy dál jen léčí.“
- Žánrový standard (Vampire Survivors endless, Brotato endless): „jak dlouho vydržím“ je hlavní dlouhodobý háček;
  hra už má v menu rekordy (`records.best_time_*`), ale žádný otevřený cíl.
- Poslední 3 updaty byly opravy a polish (B-67 – B-80, polish 1–6) – nový rozměr hraní je na řadě.

## Kandidáti (14) a hodnocení
`skóre = 5·hodnota + 3·soulad + 3·důkaz + 2·páka + 3·proveditelnost + 1·svěžest − 2·riziko`

| # | Kandidát | Lens | Hod | Soul | Důk | Páka | Prov | Svěž | Riz | Skóre |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | **Nekonečná noc** (endless mód s cykly bossů, rekord) | 5,6,4 | 5 | 5 | 4 | 4 | 4 | 5 | 2 | **73** |
| C2 | Prokletí: 6 modifikátorů denní výzvy volitelných pro běžné runy za bonus odměn | 6,8 | 3 | 4 | 3 | 4 | 5 | 4 | 1 | 61 |
| C3 | Pixel-art telegrafy útoků bossů (POLISH_REPORT „nejvíc prototypové“) | 7 | 3 | 4 | 4 | 2 | 4 | 2 | 1 | 55 |
| C4 | Duo-evoluce ze dvou pasivek (PLAN „Co by následovalo“) | 8 | 4 | 4 | 4 | 3 | 2 | 4 | 3 | 54 |
| C5 | Kontextové tipy: první bedna, první evoluce, kokrhání nabito | 3 | 3 | 4 | 2 | 2 | 5 | 3 | 1 | 53 |
| C6 | Pojízdný obchod v runu (utrácení mincí za léčení/rerol/bednu) | 4 | 4 | 4 | 2 | 3 | 3 | 4 | 3 | 51 |
| C7 | Denní úkoly (3 mise denně za žetony) | 6 | 3 | 3 | 2 | 3 | 4 | 3 | 1 | 49 |
| C8 | Kronika runů (historie posledních 20 runů, statistiky) | 6,9 | 2 | 3 | 2 | 2 | 5 | 3 | 1 | 45 |
| C9 | Nové zvíře s novou mechanikou (např. Holub s nálety) | 5 | 3 | 4 | 2 | 2 | 3 | 3 | 2 | 45 |
| C10 | Unikátní finální boss jednoho biomu (Továrna) | 5 | 3 | 4 | 3 | 2 | 2 | 3 | 2 | 45 |
| C11 | Stavové synergie (mráz + výbuch = roztříštění, hypnóza + jed…) | 8 | 3 | 3 | 2 | 4 | 3 | 4 | 3 | 45 |
| C12 | Mistrovství zvířat (úrovně za runy, odměny) | 6 | 3 | 3 | 2 | 3 | 3 | 3 | 2 | 44 |
| C13 | Zvukový pass (ručně laděné SFX/hudba) | 7 | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 42 |
| C14 | Release: AAB + target API 35 (POLISH_REPORT) | 9 | 2 | 4 | 4 | 3 | 1 | 2 | 3 | 39 |

Důkazy u vedoucích kandidátů:
- **C1**: bot 4/4 výher s maxovaným buildem; PLAN B-55; žádný otevřený cíl po výhrách (GAME_STATE „Pozdní hra“).
- **C2**: `data/meta.py` DAILY_MODIFIERS jsou hotové a otestované, ale použitelné jen 1× denně; výběrová obrazovka
  je ale plná (sekce Mapa/Mód/Obtížnost) – potřebuje nový dialog. Dobrý další krok, menší dopad než C1.
- **C3**: POLISH_REPORT bod 2; čistě vizuální, navazuje na sérii polish updatů (svěžest nízká).

## Brány
- G1 stabilita: neaktivní – 16/16 testů, sandbox běhy bez chyby, BUG_REPORT bez otevřených nálezů.
- G2 základy: neaktivní – efekty, onboarding a UI jsou na dobré úrovni (6 kol polish).
- G3 dokončitelnost: C1 je M – využívá director, bosse, arénu, výsledky; nové jsou jen plánování cyklů, HUD,
  tlačítko módu, záznam rekordu. Vejde se celé.
- G4 identita: sedí („přežij noc“ → „noc, která nekončí“), jeden palec, krátké relace zůstávají (mód je volitelný).

## Rozsah
- Nový mód `endless` (RunConfig, Director, Run.spawn_boss/boss_killed, ZombieRooster hlášky, osvětlení, HUD,
  výběr, výsledky, progression, save default, README/PLAN).
- Mimo rozsah: online žebříček, nové typy nepřátel, nové zbraně, změny balancu existujících módů.

## Pre-mortem
1. **Rozbije existující módy** (sdílený director/boss kód). → Všechny větve podmíněné `mode == "endless"`;
   porovnání starý/nový se stejným seedem (rychlý, plný, boss rush) musí dát identický výsledek.
2. **Mód je nekonečně snadný nebo okamžitě nehratelný** (exploze HP nepřátel `hp_mult` je kubická). → Ladit botem:
   cíl = medián přežití bota s čerstvým buildem 13–18 min, žádný run nad 30 min; bossové 2. kola 30–150 s.
3. **Dlouhé runy = výkon/paměť** (20+ min). → Headless běh 25 min: počty entit, ms/tick; renderovaný běh se
   sandboxem; stropy entit už existují.
4. **Matoucí UI** (tři tlačítka módu, zamčený mód). → Zamčené tlačítko s „zamčeno“ a vysvětlujícím toastem,
   screenshot výběru i HUD.
5. **Exploit ekonomiky** (nekonečné farmení vajec). → Odměny podle stávajícího vzorce (čas, zabití, bossové);
   za 15 min zhruba jako 1,5 plného runu – úměrné času, bez bonusu za výhru.

## Akceptační kritéria
1. Mód je zamčený, dokud není splněna výzva „Celá noc“; po odemčení jde vybrat a spustit; volba se pamatuje.
2. 0:00–10:00 je časování identické s Plným módem (stejní bossové a elity ve stejných časech).
3. Po porážce Kohouta: žádné vítězství, banner „NOC POKRAČUJE“, boss bedna, zpět hudba biomu, další kolo bossů
   se silnějším HP, opakované elity a formace; Kohout se vrátí.
4. Run končí jen smrtí / vzdáním; výsledky ukazují čas, rekord, „NOVÝ REKORD!“; rekord se uloží.
5. HUD ukazuje uběhlý čas, číslo noci (kola) a rekord.
6. Bot (Farma, Normal, čerstvá slepice, 6 seedů): medián přežití 13–18 min, nikdy > 30 min, 0 pádů.
7. Rychlý, Plný, Denní a Boss rush se stejným seedem dávají bit po bitu stejný výsledek jako stará verze.
8. Smoke testy 16/16 + nový test endless módu; screenshoty výběru, HUD, banneru a výsledků zkontrolované.
9. Starý save.json se načte (chybějící klíč se doplní), nový save jde načíst.
