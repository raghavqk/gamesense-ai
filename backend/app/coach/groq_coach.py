"""
GameSense AI Coach — Groq Backend
===================================
Uses Groq's LLM API (llama-3.3-70b-versatile) to power the AI Game Coach.
Supports runtime API key injection (no server restart needed).
"""
from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Model cascade — fastest/cheapest first, fallback to larger
_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]


def _build_system_prompt(ctx: dict) -> str:
    """Build a rich system prompt from the analysis context."""
    d           = ctx.get("data", {})
    game        = d.get("game", "CS2")
    kills       = d.get("kills", 0)
    deaths      = d.get("deaths", 0)
    assists     = d.get("assists", 0)
    kd          = d.get("kd_ratio", 0)
    hs_pct      = d.get("headshot_percentage", 0)
    accuracy    = d.get("accuracy", 0)
    playstyle   = d.get("playstyle", "Unknown")
    map_name    = d.get("map_name", "Unknown")
    rating      = d.get("performance_rating", 0)
    top_weapon  = d.get("most_used_weapon", "Unknown")
    weapons     = list(d.get("weapon_usage", {}).keys())
    multi_kills = d.get("multi_kills", {})
    predicted_kd = d.get("predicted_kd", 0)
    source_conf = d.get("source_confidence", "MEDIUM")

    # Tier
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
        )
        drills = (
            "DRILL LIBRARY (CS2):\n"
            "• Aim: Deathmatch (10 min/day), KovaaK's CS2 scenarios, refrag training in FFA\n"
            "• Movement: Counter-strafe trainer maps, bhop maps, crouch-peek practice\n"
            "• Utility: Yprac maps for smoke lineups, flash practice, molotov placements\n"
        )
    else:
        game_context = (
            "VALORANT TACTICAL FRAMEWORK:\n"
            "• Attacker side: Spike plant execution, site defaults, split pushes, operator duels\n"
            "• Defender side: Holding site, retake coordination, off-angle plays, flank watches\n"
            "• Agent categories: Duelist (entry frag), Controller (smokes/walls), Initiator (recon/flash),\n"
            "  Sentinel (anchor/flank watch)\n"
            "• Economy: Full buy = rifle + all util; Half buy = spectre/bulldog; Eco = pistol/classic\n"
        )
        drills = (
            "DRILL LIBRARY (Valorant):\n"
            "• Aim: The Range training mode (30 min/day), Aimlabs Valorant pack\n"
            "• Agents: Study top IGL VODs for your agent role\n"
            "• Utility: Practice lineups in custom games\n"
        )

    return f"""You are GameSense AI — an elite {game} performance analyst, ex-pro player, and personal esports coach.
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
Predicted K/D:     {predicted_kd} (ML model)
Data Confidence:   {source_conf}
══════════════════════════════════════════

{game_context}

{drills}

COACHING RULES:
1. ALWAYS reference the player's EXACT stats — never give generic advice
2. Be direct, tactical, and specific — like a real pro coach would be
3. Identify the #1 improvement area based on the stats
4. Provide 2-3 SPECIFIC, ACTIONABLE drills or techniques
5. Use **bold text** for the single most important insight
6. Structure: Strength assessment → Key weakness → Specific drills → Mindset cue
7. Maximum 4 focused paragraphs — no fluff, no padding
8. If K/D > 2.0: acknowledge the skill, then find the advanced improvement area
9. If HS% < 30%: prioritize aim training above all else
10. Speak like you KNOW this player's game — reference their specific weapons and playstyle

TONE: Confident, direct, encouraging but brutally honest. Like having a personal coach who's seen your footage.
"""


def ask_groq(question: str, ctx: dict, api_key: Optional[str] = None) -> str:
    """
    Ask the Groq-powered AI coach a question.

    Args:
        question:  The player's question.
        ctx:       Analysis context dict { data: {...} }.
        api_key:   Optional API key override (takes priority over env var).

    Returns:
        Coach response string.
    """
    # Resolve API key: runtime override > env var
    key = api_key or os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return (
            "⚠️ No Groq API key configured. "
            "Paste your key in the API Key field above and click **Connect**."
        )

    system = _build_system_prompt(ctx)

    try:
        from groq import Groq  # type: ignore
    except ImportError:
        return (
            "⚠️ Groq library not installed. "
            "Run:  pip install groq"
        )

    client = Groq(api_key=key)
    last_error: Optional[Exception] = None

    for model in _GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": question},
                ],
                max_tokens=900,
                temperature=0.68,
            )
            return response.choices[0].message.content
        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()
            # If model not found, try next
            if "model" in err_str and ("not found" in err_str or "404" in err_str):
                logger.debug("Groq model %s not available, trying next …", model)
                continue
            # Auth / quota errors — stop immediately
            break

    return f"⚠️ Coach temporarily offline: {last_error}"


def test_groq_connection(api_key: str) -> dict:
    """
    Test whether the given Groq API key is valid.

    Returns:
        { success: bool, model: str, message: str }
    """
    if not api_key or not api_key.strip():
        return {"success": False, "model": None, "message": "No API key provided."}

    try:
        from groq import Groq  # type: ignore
    except ImportError:
        return {
            "success": False,
            "model": None,
            "message": "Groq library not installed. Run: pip install groq",
        }

    client = Groq(api_key=api_key.strip())

    for model in _GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=5,
                temperature=0,
            )
            reply = resp.choices[0].message.content.strip()
            if reply:
                return {
                    "success": True,
                    "model": model,
                    "message": f"Connected via {model}. Coach is ready.",
                }
        except Exception as exc:
            err = str(exc).lower()
            if "model" in err and ("not found" in err or "404" in err):
                continue
            # Auth / network error
            return {
                "success": False,
                "model": None,
                "message": f"Connection failed: {exc}",
            }

    return {
        "success": False,
        "model": None,
        "message": "No available Groq models found. Check your API key and plan.",
    }
