import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def ask_gemini(question: str, ctx: dict) -> str:
    d = ctx.get("data", {})
    game = d.get("game", "CS2")
    weapons = list(d.get("weapon_usage", {}).keys())
    top_weapon = d.get("most_used_weapon", "Unknown")
    kills = d.get("kills", 0)
    deaths = d.get("deaths", 0)
    assists = d.get("assists", 0)
    kd = d.get("kd_ratio", 0)
    hs_pct = d.get("headshot_percentage", 0)
    accuracy = d.get("accuracy", 0)
    playstyle = d.get("playstyle", "Unknown")
    map_name = d.get("map_name", "Unknown")
    rating = d.get("performance_rating", 0)
    multi_kills = d.get("multi_kills", {})
    predicted_kd = d.get("predicted_kd", 0)
    source_conf = d.get("source_confidence", "MEDIUM")

    # Tier assessment
    if kd >= 2.5:
        tier = "ELITE / TOP 5%"
    elif kd >= 1.8:
        tier = "ADVANCED / TOP 20%"
    elif kd >= 1.2:
        tier = "ABOVE AVERAGE"
    elif kd >= 0.8:
        tier = "AVERAGE"
    else:
        tier = "BELOW AVERAGE — NEEDS WORK"

    if "CS2" in game or "CS" in game:
        game_context = (
            "CS2 TACTICAL FRAMEWORK:\n"
            "• T-side: Entry fragging, lurking, eco round management, force-buys, site executes with utility\n"
            "• CT-side: Angle holding, crossfire setups, information gathering, economy reads, rotations\n"
            "• Economy: Full buy = rifle + armor + util; Force buy = pistol/SMG + armor; Eco = pistols only\n"
            "• Key mechanics: Counter-strafing (A+D release timing), spray control (first 8 bullets then burst),\n"
            "  grenade lineups, peek timings, pre-aiming common angles\n"
            "• Map awareness: Mini-map calls, flashing for teammates, playing off information\n"
            "• Weapon tier: AWP/AK/M4A1-S (high value), Deagle/M4A4/AK alternates, pistols (eco)\n"
        )
        drill_suggestions = (
            "DRILL LIBRARY (CS2):\n"
            "• Aim: Deathmatch (10 min/day), KovaaK's CS2 scenarios, refrag training in FFA\n"
            "• Movement: Counter-strafe trainer maps, bhop maps, crouch-peek practice\n"
            "• Utility: Yprac maps for smoke lineups, flash practice, molotov placements\n"
            "• Positioning: POV analysis of pro players on same map, watch NaVi/Vitality demos\n"
        )
    else:
        game_context = (
            "VALORANT TACTICAL FRAMEWORK:\n"
            "• Attacker side: Spike plant execution, site defaults, split pushes, operator duels\n"
            "• Defender side: Holding site, retake coordination, off-angle plays, flank watches\n"
            "• Agent categories: Duelist (entry frag), Controller (smokes/walls), Initiator (recon/flash),\n"
            "  Sentinel (anchor/flank watch)\n"
            "• Economy: Full buy = rifle + all util; Half buy = spectre/bulldog; Eco = pistol/classic\n"
            "• Key mechanics: Spike timing, ability usage for information, gunfight discipline,\n"
            "  crosshair placement, orb control\n"
            "• Weapon tier: Vandal/Phantom (equal but different), Operator (power rifle), Spectre (eco rush)\n"
        )
        drill_suggestions = (
            "DRILL LIBRARY (Valorant):\n"
            "• Aim: The Range training mode (30 min/day), Aimlabs Valorant pack\n"
            "• Agents: Study top IGL VODs for your agent role, watch Aspas/TenZ for Duelist play\n"
            "• Utility: Practice lineups in custom games, coordinate with team comps\n"
            "• Positioning: Sentinel angle maps, defender default setups per site\n"
        )

    system = f"""You are GameSense AI — an elite {game} performance analyst, ex-pro player, and personal esports coach.
You have just completed a deep analysis of the player's gameplay footage using computer vision and ML.

══════════════════════════════════════════
MATCH ANALYSIS REPORT
══════════════════════════════════════════
Game:              {game} | Map: {map_name}
K/D/A:             {kills}/{deaths}/{assists}
K/D Ratio:         {kd} → Player Tier: {tier}
Headshot %:        {hs_pct}%
Accuracy Score:    {accuracy}%
Performance:       {rating}/100
Playstyle:         {playstyle}
Primary Weapon:    {top_weapon}
All Weapons:       {', '.join(weapons) if weapons else 'Not detected'}
Multi-kills:       2K×{multi_kills.get('2k', 0)}  3K×{multi_kills.get('3k', 0)}  4K+×{multi_kills.get('4k+', 0)}
Predicted K/D:     {predicted_kd} (LSTM model)
Data Confidence:   {source_conf}
══════════════════════════════════════════

{game_context}

{drill_suggestions}

COACHING PHILOSOPHY & RULES:
1. ALWAYS reference the player's EXACT stats — never give generic advice
2. Be direct, tactical, and specific — like a real pro coach would be
3. Identify the #1 improvement area based on the stats
4. Provide 2-3 SPECIFIC, ACTIONABLE drills or techniques
5. Use **bold text** for the single most important insight
6. Structure: Strength assessment → Key weakness → Specific drills → Mindset cue
7. Maximum 4 focused paragraphs — no fluff, no padding
8. If K/D > 2.0: acknowledge the skill, then find the advanced improvement area
9. If HS% < 30%: prioritize aim training above all else
10. If multi-kills exist: praise the clutch ability and build on it
11. Speak like you KNOW this player's game — reference their specific weapons and playstyle

TONE: Confident, direct, encouraging but brutally honest. Like having a personal coach who's seen your footage.
"""

    # Model cascade: try newest models first, fall back gracefully
    _MODELS = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"]

    last_error = None
    for model_name in _MODELS:
        try:
            response = _client.models.generate_content(
                model=model_name,
                contents=[system, f"Player asks: {question}"],
                config=types.GenerateContentConfig(
                    max_output_tokens=800,
                    temperature=0.68,
                ),
            )
            return response.text
        except Exception as e:
            last_error = e
            # If it's a 404/NOT_FOUND, try the next model in cascade
            if "404" in str(e) or "NOT_FOUND" in str(e) or "not found" in str(e).lower():
                continue
            # For other errors (auth, quota), stop immediately
            break

    return f"⚠️ Coach temporarily offline: {last_error}. Check your GEMINI_API_KEY in backend/.env"
