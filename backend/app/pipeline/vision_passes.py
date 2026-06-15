import os, json, re, asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
CONCURRENCY = 12

CS2_WEAPONS = [
    "AK-47", "M4A4", "M4A1-S", "AWP", "Desert Eagle", "Glock-18", "USP-S",
    "P250", "Five-SeveN", "Tec-9", "CZ75-Auto", "Dual Berettas", "R8 Revolver",
    "MP9", "MAC-10", "UMP-45", "P90", "PP-Bizon", "Galil AR", "FAMAS",
    "SG 553", "AUG", "SSG 08", "G3SG1", "SCAR-20",
    "Nova", "XM1014", "MAG-7", "Sawed-Off", "M249", "Negev",
    "knife", "HE Grenade", "Molotov", "Incendiary", "flashbang",
]
VAL_WEAPONS = [
    "Vandal", "Phantom", "Operator", "Odin", "Ares", "Bulldog", "Guardian",
    "Marshal", "Outlaw", "Spectre", "Stinger", "Bucky", "Judge",
    "Classic", "Shorty", "Frenzy", "Ghost", "Sheriff",
    "knife", "Spike", "Ability",
]


async def _vision_call(b64: str, prompt: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        try:
            r = await client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ]}],
                max_tokens=400,
                temperature=0.05,
            )
            raw = r.choices[0].message.content.strip()
            return re.sub(r"```json|```", "", raw).strip()
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'


# ── PASS 1: GAME + MAP DETECTION ─────────────────────────────────────────────
DETECT_PROMPT = """You are looking at a gameplay screenshot.

Identify:
1. Which game is this? (CS2, VALORANT, or Unknown)
2. What map is being played? Look for map name on loading screens, minimap label, or scoreboard.
3. Is this a loading/map-select screen? (yes/no)

CS2 maps: de_dust2, de_mirage, de_inferno, de_nuke, de_overpass, de_anubis, de_vertigo, de_ancient
Valorant maps: Ascent, Bind, Breeze, Fracture, Haven, Icebox, Lotus, Pearl, Split, Sunset, Abyss

Respond ONLY with valid JSON, no markdown:
{"game": "CS2", "map": "de_dust2 or null", "is_loading_screen": false}
"""

async def pass1_detect_game_and_map(detection_frames: list) -> dict:
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [_vision_call(f["b64"], DETECT_PROMPT, sem) for f in detection_frames]
    results = await asyncio.gather(*tasks)

    game_votes, map_votes = {}, {}
    for raw in results:
        try:
            d = json.loads(raw)
            g = d.get("game", "")
            if g in ("CS2", "VALORANT"):
                game_votes[g] = game_votes.get(g, 0) + 1
            m = d.get("map")
            if m and m != "null" and m is not None:
                map_votes[m] = map_votes.get(m, 0) + 1
        except:
            pass

    game = max(game_votes, key=game_votes.get) if game_votes else "CS2"
    map_name = max(map_votes, key=map_votes.get) if map_votes else "Unknown"
    return {"game": game, "map_name": map_name}


# ── PASS 2: SCOREBOARD HARVESTING ─────────────────────────────────────────────
def _scoreboard_prompt(game: str) -> str:
    return f"""You are looking at a {game} gameplay screenshot.

TASK: Detect if this frame contains a SCOREBOARD or MATCH STATS OVERLAY.

A scoreboard appears when:
- The player presses TAB (shows all player stats mid-match)
- A round ends (shows round summary)
- The match ends (shows final MVP/results screen)

If a scoreboard IS visible, extract the LOCAL PLAYER's stats (usually highlighted or at top):
- Kills (K), Deaths (D), Assists (A)
- Headshot percentage (HS% or fraction)

Respond ONLY with valid JSON, no markdown:
{{"scoreboard_visible": true, "kills": 14, "deaths": 3, "assists": 2, "headshot_pct": 64, "is_match_end": false}}

OR if no scoreboard:
{{"scoreboard_visible": false}}
"""

async def pass2_harvest_scoreboard(scoreboard_crops: list, game: str) -> dict:
    if not scoreboard_crops:
        return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}

    sem = asyncio.Semaphore(CONCURRENCY)
    prompt = _scoreboard_prompt(game)
    tasks = [_vision_call(f["b64"], prompt, sem) for f in scoreboard_crops]
    results = await asyncio.gather(*tasks)

    best = {"found": False, "kills": None, "deaths": None, "headshot_pct": None, "is_match_end": False}
    best_kills = -1

    for raw in results:
        try:
            d = json.loads(raw)
            if d.get("scoreboard_visible") and d.get("kills") is not None:
                k = int(d["kills"])
                is_end = d.get("is_match_end", False)
                if is_end or k > best_kills:
                    best_kills = k
                    best = {
                        "found": True,
                        "kills": k,
                        "deaths": int(d.get("deaths", 0)),
                        "assists": int(d.get("assists", 0)),
                        "headshot_pct": int(d.get("headshot_pct", 0)),
                        "is_match_end": is_end,
                    }
                    if is_end:
                        break
        except:
            pass

    return best


# ── PASS 3: KILL FEED READING ─────────────────────────────────────────────────
def _killfeed_prompt(game: str, weapons: list) -> str:
    weapon_str = ", ".join(weapons[:20])
    return f"""You are reading ONLY the kill feed / death notices in the top-right corner of a {game} screenshot.

The kill feed shows lines like: [Attacker Name] [weapon icon] [Victim Name]
A headshot shows a skull or "HS" icon next to the weapon icon.

Report ONLY kills made BY the local player (attacker on the LEFT side).
In CS2: local player name appears in bright blue (CT) or orange (T).
In Valorant: local player name appears highlighted vs enemy entries.

RULES:
- Only report kills where local player is the attacker
- "headshot": true ONLY if you see a skull icon or HS text in that entry
- weapon must match one of: {weapon_str}
- If kill feed is empty: return empty array

Respond ONLY with valid JSON, no markdown:
{{"kills": [{{"weapon": "AK-47", "headshot": true}}, {{"weapon": "AWP", "headshot": false}}]}}
"""

async def pass3_read_killfeed(killfeed_crops: list, game: str) -> dict:
    weapons = CS2_WEAPONS if game == "CS2" else VAL_WEAPONS
    prompt = _killfeed_prompt(game, weapons)
    sem = asyncio.Semaphore(CONCURRENCY)

    tasks = [_vision_call(f["b64"], prompt, sem) for f in killfeed_crops]
    results = await asyncio.gather(*tasks)

    all_kills = []
    seen_keys = set()

    for i, raw in enumerate(results):
        ts = killfeed_crops[i]["ts"]
        try:
            d = json.loads(raw)
            for k in d.get("kills", []):
                weapon = k.get("weapon", "Unknown")
                hs = bool(k.get("headshot", False))
                key = (round(ts / 3), weapon)
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_kills.append({"ts": ts, "weapon": weapon, "headshot": hs})
        except:
            pass

    weapon_stats = {}
    for k in all_kills:
        w = k["weapon"]
        weapon_stats.setdefault(w, {"count": 0, "headshots": 0})
        weapon_stats[w]["count"] += 1
        if k["headshot"]:
            weapon_stats[w]["headshots"] += 1

    total = len(all_kills)
    for w, v in weapon_stats.items():
        v["percentage"] = round(v["count"] / total * 100) if total else 0
        v["hs_rate"] = round(v["headshots"] / v["count"] * 100) if v["count"] else 0

    # Multi-kill detection
    times = sorted(k["ts"] for k in all_kills)
    multi_kills = {"2k": 0, "3k": 0, "4k+": 0}
    used = set()
    for i, t in enumerate(times):
        if i in used:
            continue
        window = [j for j, t2 in enumerate(times) if t <= t2 <= t + 5 and j not in used]
        n = len(window)
        if n == 2:
            multi_kills["2k"] += 1; used.update(window)
        elif n == 3:
            multi_kills["3k"] += 1; used.update(window)
        elif n >= 4:
            multi_kills["4k+"] += 1; used.update(window)

    buckets = {}
    for k in all_kills:
        b = int(k["ts"] // 30) * 30
        buckets[b] = buckets.get(b, 0) + 1
    timeline = [{"time_sec": t, "kills": c} for t, c in sorted(buckets.items())]

    return {
        "kill_events": all_kills,
        "kill_feed_count": total,
        "weapon_stats": weapon_stats,
        "most_used_weapon": max(weapon_stats, key=lambda w: weapon_stats[w]["count"]) if weapon_stats else "Unknown",
        "multi_kills": multi_kills,
        "timeline": timeline,
        "kf_headshot_pct": round(sum(1 for k in all_kills if k["headshot"]) / total * 100) if total else 0,
    }


# ── ORCHESTRATOR ─────────────────────────────────────────────────────────────
async def run_three_pass_analysis(frame_data: dict, game_hint: str) -> dict:
    p1_task = asyncio.create_task(pass1_detect_game_and_map(frame_data["detection_frames"]))
    p2_task = asyncio.create_task(pass2_harvest_scoreboard(frame_data["scoreboard_crops"], game_hint))
    p3_task = asyncio.create_task(pass3_read_killfeed(frame_data["killfeed_crops"], game_hint))

    p1, p2, p3 = await asyncio.gather(p1_task, p2_task, p3_task)

    game = p1["game"]
    map_name = p1["map_name"]

    if p2["found"]:
        kills = p2["kills"]
        deaths = p2["deaths"]
        headshot_pct = p2["headshot_pct"]
        data_source = "scoreboard (authoritative)"
        confidence = "HIGH"
    else:
        kills = p3["kill_feed_count"]
        deaths = 0
        headshot_pct = p3["kf_headshot_pct"]
        data_source = "kill feed analysis"
        confidence = "MEDIUM"

    weapon_stats = p3["weapon_stats"]
    if p2["found"] and p3["kill_feed_count"] > 0 and p2["kills"] != p3["kill_feed_count"]:
        scale = p2["kills"] / max(1, p3["kill_feed_count"])
        if 0.5 < scale < 2.0:
            for w in weapon_stats:
                weapon_stats[w]["count"] = round(weapon_stats[w]["count"] * scale)
                weapon_stats[w]["percentage"] = round(weapon_stats[w]["count"] / p2["kills"] * 100)

    return {
        "game": game,
        "map_name": map_name,
        "kills": kills,
        "deaths": deaths,
        "headshot_pct": headshot_pct,
        "assists": p2.get("assists", 0),
        "weapon_stats": weapon_stats,
        "most_used_weapon": p3["most_used_weapon"],
        "kill_events": p3["kill_events"],
        "multi_kills": p3["multi_kills"],
        "timeline": p3["timeline"],
        "data_source": data_source,
        "confidence": confidence,
    }
