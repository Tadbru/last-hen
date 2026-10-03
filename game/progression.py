"""Progrese: levelup karty (rarity, rerol, skip, banish), bedny, odměny po runu, výzvy, sbírka."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .data import meta as M
from .data.bosses import BOSS_ORDER
from .data.characters import CHARACTERS
from .data.enemies import COLLECT_ENEMIES
from .data.passives import MAX_PASSIVE_LEVEL, PASSIVE_ORDER, PASSIVES
from .data.weapons import BASE_WEAPONS, EVOLUTIONS, MAX_WEAPON_LEVEL, STARTER_WEAPONS, WEAPONS
from .util import fmt_num

MAX_WEAPONS = 6
MAX_PASSIVES = 6


@dataclass
class Card:
    kind: str           # weapon | passive | heal | coins | crow
    id: str
    rarity: int
    levels: int
    new: bool
    cur: int
    to: int
    title: str
    desc: str
    icon: str


# ---------------------------------------------------------------------------------------------
# LEVELUP KARTY
# ---------------------------------------------------------------------------------------------
def _weapon_pool(run) -> list[str]:
    pool = list(BASE_WEAPONS)
    starter = run.char.weapon
    if starter not in pool:
        pool.append(starter)
    if run.cfg.mode == "bossrush":
        pool = list(BASE_WEAPONS) + [starter]
    return pool


def _candidates(run) -> list[tuple[str, str, float]]:
    out = []
    owned_w = {w.id: w for w in run.weapons}
    evo_passives = {WEAPONS[w.id].evo_passive for w in run.weapons if WEAPONS[w.id].evo_passive}
    for w in run.weapons:
        if not w.evolved and w.level < MAX_WEAPON_LEVEL and w.id not in run.banished:
            out.append(("weapon", w.id, 1.2))
    for pid, lv in run.passives.items():
        if lv < MAX_PASSIVE_LEVEL and pid not in run.banished:
            out.append(("passive", pid, 1.0 + (0.4 if pid in evo_passives else 0.0)))
    if len(run.weapons) < MAX_WEAPONS:
        evolved_from = {WEAPONS[w.id].evolved_from for w in run.weapons if w.evolved}
        for wid in _weapon_pool(run):
            if wid not in owned_w and wid not in evolved_from and wid not in run.banished:
                out.append(("weapon", wid, 0.75))
    if len(run.passives) < MAX_PASSIVES and "no_passives" not in run.mods:
        for pid in PASSIVE_ORDER:
            if pid not in run.passives and pid not in run.banished:
                out.append(("passive", pid, 0.7 + (1.0 if pid in evo_passives else 0.0)))
    return out


def has_choices(run) -> bool:
    """Je co vylepšit? (Pokud ne, levelup se vyřeší automaticky bez přerušení hry.)"""
    return bool(_candidates(run))


def roll_rarity(run) -> int:
    luck = run.player.stats.luck * getattr(run, "card_luck", 1.0)
    r = run.rng.random()
    if r < 0.045 * luck * luck:
        rar = 2
    elif r < 0.045 * luck * luck + 0.20 * luck:
        rar = 1
    else:
        rar = 0
    if "lucky" in run.mods:
        rar = min(2, rar + 1)       # Šťastný den: každá karta o stupeň vzácnější (B-59)
    return rar


def _take_weighted(rng, pool: list):
    """Vytáhne (a odebere) jednoho kandidáta z poolu podle váhy."""
    total = sum(c[2] for c in pool)
    r = rng.random() * total
    acc = 0.0
    for i, c in enumerate(pool):
        acc += c[2]
        if r <= acc:
            return pool.pop(i)
    return pool.pop()


def _card(run, kind: str, cid: str, rarity: int) -> Card:
    if kind == "weapon":
        d = WEAPONS[cid]
        w = run.weapon(cid)
        cur = w.level if w else 0
        levels = 1 + rarity
        to = min(MAX_WEAPON_LEVEL, cur + levels)
        if w is None:
            desc = d.desc
        else:
            desc = " ".join(d.level_text(lv) for lv in range(cur + 1, to + 1))
        return Card("weapon", cid, rarity, levels, w is None, cur, to, d.name, desc, d.icon)
    if kind == "passive":
        d = PASSIVES[cid]
        cur = run.passives.get(cid, 0)
        levels = 1 + rarity
        to = min(MAX_PASSIVE_LEVEL, cur + levels)
        n = to - cur
        desc = d.desc if n == 1 else f"{d.desc} (×{n})"
        if cur == 0:
            desc = f"{desc}. {d.flavor}"
        return Card("passive", cid, rarity, levels, cur == 0, cur, to, d.name, desc, d.icon)
    raise ValueError(kind)


# Výplň, když už není co vylepšovat: jen léčení (jedna karta, žádné duplikáty)
HEAL_FILL = 0.35
FILLERS = [
    ("heal", "Kuřecí polévka", "Vyléčí 35 % zdraví. Babička by měla radost.", "heart"),
]


def make_offer(run, count: int = 3) -> list[Card]:
    cands = _candidates(run)
    rng = run.rng
    cards: list[Card] = []
    pool = list(cands)
    while pool and len(cards) < count:
        pick = _take_weighted(rng, pool)
        cards.append(_card(run, pick[0], pick[1], roll_rarity(run)))
    fi = 0
    while len(cards) < count and fi < len(FILLERS):
        k, t, d, ic = FILLERS[fi]
        cards.append(Card(k, k, 0, 0, False, 0, 0, t, d, ic))
        fi += 1
    return cards


def apply_card(run, card: Card) -> None:
    if card.kind == "weapon":
        run.level_weapon(card.id, card.to - card.cur if card.cur else card.to)
    elif card.kind == "passive":
        run.add_passive(card.id, card.to - card.cur)
    elif card.kind == "heal":
        run.player.heal(run.player.stats.max_hp * HEAL_FILL)
    run.pending_levelups = max(0, run.pending_levelups - 1)
    run.resume()


def reroll(run) -> bool:
    if run.rerolls <= 0:
        return False
    run.rerolls -= 1
    run.offer = make_offer(run)
    return True


def skip(run) -> int:
    coins = 5 + run.level // 2
    run.coins += coins
    run.pending_levelups = max(0, run.pending_levelups - 1)
    run.resume()
    return coins


def banish(run, card: Card) -> bool:
    if run.banishes <= 0 or card.kind not in ("weapon", "passive"):
        return False
    run.banishes -= 1
    run.banished.add(card.id)
    offer = list(run.offer or [])
    idx = next((i for i, c in enumerate(offer) if c is card), -1)
    taken = {(c.kind, c.id) for c in offer}
    pool = [c for c in _candidates(run) if (c[0], c[1]) not in taken]
    new = None
    if pool:
        pick = _take_weighted(run.rng, pool)
        new = _card(run, pick[0], pick[1], roll_rarity(run))
    elif not any(c.kind == "heal" for c in offer):
        k, t, d, ic = FILLERS[0]
        new = Card(k, k, 0, 0, False, 0, 0, t, d, ic)
    # nahradí se jen vyřazená karta, ostatní zůstanou (dřív to byl rerol zdarma)
    if idx >= 0:
        if new is not None:
            offer[idx] = new
        else:
            offer.pop(idx)
    run.offer = offer
    return True


# ---------------------------------------------------------------------------------------------
# BEDNY
# ---------------------------------------------------------------------------------------------
def open_chest(run, kind: str = "elite") -> dict:
    rng = run.rng
    items: list[tuple[str, str, str, bool]] = []   # (icon, název, popis, evo)
    evos = run.evolvable()
    result = dict(evolution=None, items=items, coins=0)
    if evos:
        wid = rng.choice(evos)
        new_id = WEAPONS[wid].evo_to
        run.evolve(wid)
        d = WEAPONS[new_id]
        items.append((d.icon, d.name, "EVOLUCE! " + d.desc, True))
        result["evolution"] = new_id
    else:
        luck = run.player.stats.luck
        r = rng.random()
        n = 1
        if kind == "boss" or r < 0.05 * luck:
            n = 5 if kind == "boss" and rng.random() < 0.3 * luck else 3
        elif r < 0.3 * luck:
            n = 3
        # šance na novou zbraň
        if len(run.weapons) < MAX_WEAPONS and rng.random() < 0.55:
            owned = {w.id for w in run.weapons}
            evolved_from = {WEAPONS[w.id].evolved_from for w in run.weapons if w.evolved}
            opts = [w for w in _weapon_pool(run) if w not in owned and w not in evolved_from and w not in run.banished]
            if opts:
                wid = rng.choice(opts)
                run.add_weapon(wid, 1)
                d = WEAPONS[wid]
                items.append((d.icon, d.name, "Nová zbraň!", False))
                n -= 1
        for _ in range(max(0, n)):
            ups = [w for w in run.weapons if not w.evolved and w.level < MAX_WEAPON_LEVEL]
            if ups:
                w = rng.choice(ups)
                w.set_level(w.level + 1)
                items.append((w.d.icon, w.d.name, f"Úroveň {w.level}", False))
                continue
            ps = [pid for pid, lv in run.passives.items() if lv < MAX_PASSIVE_LEVEL]
            if ps:
                pid = rng.choice(ps)
                run.add_passive(pid, 1)
                items.append((PASSIVES[pid].icon, PASSIVES[pid].name, f"Úroveň {run.passives[pid]}", False))
                continue
            run.coins += 10
            items.append(("coin", "Mince", "+10 mincí", False))
    coins = rng.randint(6, 14) if kind != "boss" else rng.randint(25, 40)
    run.coins += coins
    result["coins"] = coins
    return result


# ---------------------------------------------------------------------------------------------
# ODMĚNY PO RUNU
# ---------------------------------------------------------------------------------------------
def compute_rewards(run) -> dict:
    t = run.time
    lines = []
    eggs_time = int(t / 10) * M.EGGS_PER_10S
    eggs_kills = run.kills // 10 * M.EGGS_PER_10_KILLS
    minis = [b for b in run.bosses_killed if b != "zombie_rooster"]
    final = "zombie_rooster" in run.bosses_killed
    eggs_boss = len(minis) * M.EGGS_PER_MINIBOSS + (M.EGGS_FINAL_BOSS if final else 0)
    eggs_win = M.EGGS_WIN_BONUS if run.victory else 0
    if run.cfg.mode in ("quick", "daily"):
        eggs_boss = int(eggs_boss * 0.6)
        eggs_win = int(eggs_win * 0.6)
    eggs_coins = run.coins
    mult = run.diff.reward * run.biome.reward_mult
    lines.append(("Přežitý čas", eggs_time))
    lines.append(("Zabití", eggs_kills))
    if eggs_boss:
        lines.append(("Bossové", eggs_boss))
    if eggs_win:
        lines.append(("Vítězství", eggs_win))
    if eggs_coins:
        lines.append(("Mince", eggs_coins))
    base = eggs_time + eggs_kills + eggs_boss + eggs_win + eggs_coins
    total = int(base * mult)
    gold = len(minis) + (2 if final else 0)
    return dict(lines=lines, base=base, mult=mult, eggs=total, gold=gold)


def score(run) -> int:
    return int(run.kills * 10 + run.time * 5 + run.level * 50 + (5000 if run.victory else 0)
               + len(run.bosses_killed) * 1000)


def apply_results(save, run, rewards: dict) -> list[str]:
    """Zapíše výsledky do save a vrátí seznam zpráv (odemčení, výzvy)."""
    msgs: list[str] = []
    d = save.data
    rec = d["records"]
    d["eggs"] += rewards["eggs"]
    d["gold"] += rewards["gold"]
    rec["total_eggs"] += rewards["eggs"]
    rec["runs"] += 1
    rec["total_kills"] += run.kills
    rec["best_kills"] = max(rec["best_kills"], run.kills)
    rec["max_level"] = max(rec["max_level"], run.level)
    key = "best_time_quick" if run.cfg.mode in ("quick", "daily") else "best_time_full"
    if run.cfg.mode in ("quick", "full", "daily"):
        rec[key] = max(rec[key], int(run.time))
    rec["boss_kills"] += len(run.bosses_killed)
    if run.victory:
        rec["wins"] += 1
    if run.biome.id not in d["played_biomes"]:
        d["played_biomes"].append(run.biome.id)
    # rubber-banding
    # rubber-banding jen po skutečné brzké smrti (ne po „Vzdát se“)
    d["rubber_band"] = (not run.victory) and (not run.gave_up) and run.player.dead and run.time < 90
    # sbírka
    for cat, items in run.discovered.items():
        for it in items:
            save.discover(cat, it)
    msgs += check_collection(save)
    # odemčení
    if "zombie_rooster" in run.bosses_killed and "rooster" not in d["unlocked_chars"]:
        d["unlocked_chars"].append("rooster")
        msgs.append("Odemčeno: Kohout Elvis!")
    if run.victory and run.cfg.mode != "bossrush":     # boss rush je vždy Farma/Normal – nic neodemyká (B-57)
        from .data.biomes import BIOME_ORDER
        i = BIOME_ORDER.index(run.biome.id)
        if i + 1 < len(BIOME_ORDER) and BIOME_ORDER[i + 1] not in d["unlocked_maps"] and run.cfg.mode != "daily":
            d["unlocked_maps"].append(BIOME_ORDER[i + 1])
            from .data.biomes import BIOMES
            msgs.append(f"Odemčena mapa: {BIOMES[BIOME_ORDER[i + 1]].name}!")
        nxt = {"normal": "hard", "hard": "nightmare"}.get(run.cfg.difficulty)
        if nxt and nxt not in d["unlocked_diffs"]:
            d["unlocked_diffs"].append(nxt)
            msgs.append(f"Odemčena obtížnost: {M.DIFFICULTIES[nxt].name}!")
    # výzvy
    msgs += check_challenges(save, run)
    save.save()
    return msgs


def complete_challenge(save, cid: str) -> list[str]:
    d = save.data
    if d["challenges"].get(cid):
        return []
    c = M.CHALLENGE_BY_ID[cid]
    d["challenges"][cid] = True
    eggs, gold = c["reward"]
    d["eggs"] += eggs
    d["gold"] += gold
    msgs = [f"Výzva splněna: {c['name']}! (+{fmt_num(eggs)} vajec, +{gold} zl.)"]
    unlock = c.get("unlock")
    if unlock and unlock.startswith("char:"):
        ch = unlock[5:]
        if ch not in d["unlocked_chars"]:
            d["unlocked_chars"].append(ch)
            msgs.append(f"Odemčeno zvíře: {CHARACTERS[ch].name}!")
    return msgs


def check_challenges(save, run) -> list[str]:
    d = save.data
    v = run.victory
    mode = run.cfg.mode
    conds = {
        "thousand": run.kills >= 1000,
        "first_dawn": v and mode == "quick",
        "full_night": v and mode == "full",
        "ascetic": v and not run.ever_passive,
        "goose5": run.char.id == "goose" and run.time >= 300,
        "evolve": bool(run.discovered["evolutions"] & set(EVOLUTIONS)),
        "crow10": run.crows_used >= 10,
        "massacre": run.max_burst >= 50,
        "arsenal": run.max_weapons >= 6,
        "nightmare": v and run.cfg.difficulty == "nightmare",
        "tourist": len(d["played_biomes"]) >= 5,
        "bossrush": v and mode == "bossrush",
        "factory": v and run.biome.id == "factory",
        "untouchable": run.best_no_hit >= 180,
        "critic": run.char.id == "turkey" and run.crits >= 500,
        "level40": run.level >= 40,
        "rich": d["records"]["total_eggs"] >= 10000,
    }
    msgs = []
    for cid, ok in conds.items():
        if ok:
            msgs += complete_challenge(save, cid)
    return msgs


COLLECTION_CATS = {
    "enemies": ("Nepřátelé", COLLECT_ENEMIES),
    "bosses": ("Bossové", BOSS_ORDER),
    "weapons": ("Zbraně", BASE_WEAPONS + STARTER_WEAPONS),
    "evolutions": ("Evoluce", EVOLUTIONS),
    "passives": ("Pasivky", PASSIVE_ORDER),
}


def collection_progress(save) -> tuple[int, int]:
    have = total = 0
    for cat, (_, items) in COLLECTION_CATS.items():
        total += len(items)
        have += sum(1 for i in items if save.is_discovered(cat, i))
    return have, total


def check_collection(save) -> list[str]:
    msgs = []
    d = save.data
    for cat, (name, items) in COLLECTION_CATS.items():
        if cat in d["collection_rewards"]:
            continue
        if all(save.is_discovered(cat, i) for i in items):
            d["collection_rewards"].append(cat)
            d["gold"] += M.COLLECTION_REWARD_GOLD
            msgs.append(f"Sbírka „{name}“ kompletní! +{M.COLLECTION_REWARD_GOLD} zlatá vejce")
    return msgs


# ---------------------------------------------------------------------------------------------
# DENNÍ OBSAH
# ---------------------------------------------------------------------------------------------
def today() -> _dt.date:
    return _dt.date.today()


def daily_spec(day: _dt.date | None = None) -> dict:
    import random as _r
    day = day or today()
    seed = int(day.strftime("%Y%m%d"))
    rng = _r.Random(seed)
    from .data.biomes import BIOME_ORDER
    from .data.characters import CHAR_ORDER
    return dict(
        seed=seed,
        date=day.isoformat(),
        character=rng.choice(CHAR_ORDER[:6]),
        biome=rng.choice(BIOME_ORDER),
        modifier=rng.choice(M.DAILY_MODIFIERS)["id"],
    )


def daily_date(seed: int) -> str:
    """Datum denní výzvy z jejího seedu (YYYYMMDD); při neplatném seedu dnešek."""
    try:
        return _dt.datetime.strptime(str(int(seed)), "%Y%m%d").date().isoformat()
    except (ValueError, TypeError):
        return today().isoformat()


def daily_leaderboard(save, spec: dict) -> list[tuple[str, int, bool]]:
    import random as _r
    rng = _r.Random(spec["seed"] * 7 + 1)
    names = rng.sample(M.NEIGHBOURS, 9)
    board = [(n, int(rng.uniform(2000, 26000)), False) for n in names]
    for s in save.data["daily"]["scores"]:
        if s.get("date") == spec["date"]:
            board.append(("Ty", int(s.get("score", 0)), True))
    board.sort(key=lambda b: -b[1])
    return board[:10]


def iso_week(day: _dt.date | None = None) -> str:
    day = day or today()
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"


def season_for(day: _dt.date | None, setting: str) -> str | None:
    if setting == "off":
        return None
    if setting in M.SEASONS:
        return setting
    day = day or today()
    if day.month == 10:
        return "halloween"
    if day.month == 12:
        return "christmas"
    if day.month in (3, 4):
        return "easter"
    return None


def skin_usable(save, skin_id: str | None) -> bool:
    """Skin lze nosit, pokud ho hráč vlastní, nebo je to sezónní skin a právě běží jeho skutečná sezóna
    (podle data – vynucená sezóna v Nastavení mění jen vzhled světa, ne odemčení skinů)."""
    if not skin_id:
        return False
    if skin_id in save["skins_owned"]:
        return True
    s = M.SKIN_BY_ID.get(skin_id)
    return bool(s and s["season"] and s["season"] == season_for(None, "auto"))


def daily_login(save) -> dict | None:
    """Vrátí odměnu, pokud je dnes první přihlášení."""
    d = save.data["daily"]
    t = today()
    last = d.get("login_last", "")
    if last == t.isoformat():
        return None
    try:
        last_day = _dt.date.fromisoformat(last) if last else None
    except ValueError:
        last_day = None
    if last_day and t < last_day:
        return None          # hodiny posunuté zpátky – žádná odměna, série zůstává
    if last_day and (t - last_day).days == 1:
        d["login_streak"] = d.get("login_streak", 0) + 1
    else:
        d["login_streak"] = 1
    d["login_last"] = t.isoformat()
    idx = (d["login_streak"] - 1) % len(M.LOGIN_REWARDS)
    reward = dict(M.LOGIN_REWARDS[idx])
    save.data["eggs"] += reward.get("eggs", 0)
    save.data["tokens"] += reward.get("tokens", 0)
    save.data["gold"] += reward.get("gold", 0)
    save.save()
    reward["streak"] = d["login_streak"]
    return reward
