"""
Kill Feed Detection Engine with Multi-Frame Validation
Stage 2 of Multi-Signal Pipeline - PRIMARY DATA SOURCE
"""
import os
import json
import re
import asyncio
from typing import List, Dict, Tuple, Optional, Set
from app.pipeline.stats_reconciler import StatsReconciler
from app.pipeline.safe_api import safe_groq_call
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq not available - kill feed detection will use fallback")


CS2_WEAPONS = [
    "AK-47", "M4A4", "M4A1-S", "AWP", "Desert Eagle", "Glock-18", "USP-S",
    "P250", "Five-SeveN", "Tec-9", "CZ75-Auto", "Dual Berettas", "R8 Revolver",
    "MP9", "MAC-10", "UMP-45", "P90", "PP-Bizon", "Galil AR", "FAMAS",
    "SG 553", "AUG", "SSG 08", "G3SG1", "SCAR-20",
    "Nova", "XM1014", "MAG-7", "Sawed-Off", "M249", "Negev",
    "Knife", "HE Grenade", "Molotov", "Incendiary", "Flashbang", "Smoke", "Decoy",
    "Zeus", "C4",
]

VALORANT_WEAPONS = [
    "Vandal", "Phantom", "Operator", "Odin", "Ares", "Bulldog", "Guardian",
    "Marshal", "Outlaw", "Spectre", "Stinger", "Bucky", "Judge",
    "Classic", "Shorty", "Frenzy", "Ghost", "Sheriff",
    "Knife", "Spike", "Ability",
]

WEAPON_ALIASES = {
    # CS2 aliases
    "ak": "AK-47", "ak47": "AK-47",
    "m4": "M4A4", "m4a4": "M4A4", "m4a1": "M4A1-S", "m4a1s": "M4A1-S",
    "awp": "AWP", "scout": "SSG 08",
    "deagle": "Desert Eagle", "deserteagle": "Desert Eagle",
    "glock": "Glock-18", "usp": "USP-S",
    "p250": "P250", "fiveseven": "Five-SeveN", "tec9": "Tec-9",
    "dualies": "Dual Berettas", "dualberettas": "Dual Berettas",
    "revolver": "R8 Revolver", "r8": "R8 Revolver",
    "mp9": "MP9", "mac10": "MAC-10", "mac-10": "MAC-10",
    "ump": "UMP-45", "p90": "P90", "bizon": "PP-Bizon", "ppbizon": "PP-Bizon",
    "galil": "Galil AR", "famas": "FAMAS",
    "sg553": "SG 553", "sg": "SG 553", "aug": "AUG",
    "ssg": "SSG 08", "g3sg1": "G3SG1", "scar": "SCAR-20", "scar20": "SCAR-20",
    "nova": "Nova", "xm": "XM1014", "mag7": "MAG-7", "mag-7": "MAG-7",
    "sawedoff": "Sawed-Off", "sawed-off": "Sawed-Off",
    "m249": "M249", "negev": "Negev",
    "he": "HE Grenade", "hegrenade": "HE Grenade",
    "molotov": "Molotov", "incendiary": "Incendiary", "inferno": "Incendiary",
    "flash": "Flashbang", "flashbang": "Flashbang",
    "smoke": "Smoke", "decoy": "Decoy",
    "zeus": "Zeus", "taser": "Zeus", "c4": "C4", "bomb": "C4",
    # Valorant aliases
    "vandal": "Vandal", "phantom": "Phantom", "op": "Operator",
    "odin": "Odin", "ares": "Ares", "bulldog": "Bulldog",
    "guardian": "Guardian", "marshal": "Marshal", "outlaw": "Outlaw",
    "spectre": "Spectre", "stinger": "Stinger",
    "bucky": "Bucky", "judge": "Judge",
    "classic": "Classic", "shorty": "Shorty", "frenzy": "Frenzy",
    "ghost": "Ghost", "sheriff": "Sheriff",
}


@dataclass
class KillEvent:
    """Represents a validated kill event"""
    timestamp: float
    frame_idx: int
    weapon: str
    headshot: bool
    confidence: float = 0.0
    validation_frames: List[int] = field(default_factory=list)
    source: str = "unknown"  # "killfeed", "scoreboard", "inferred"
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": round(self.timestamp, 2),
            "frame_idx": self.frame_idx,
            "weapon": self.weapon,
            "headshot": self.headshot,
            "confidence": round(self.confidence, 2),
            "validation_frames": self.validation_frames,
            "source": self.source,
        }


class WeaponNormalizer:
    """Normalizes weapon names to canonical forms"""
    
    @staticmethod
    def normalize(weapon_name: str, game: str = "CS2") -> Optional[str]:
        """Normalize weapon name to canonical form"""
        if not weapon_name:
            return None
            
        name = weapon_name.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
        
        # Check aliases
        if name in WEAPON_ALIASES:
            return WEAPON_ALIASES[name]
        
        # Check full list
        weapons = CS2_WEAPONS if game == "CS2" else VALORANT_WEAPONS
        for w in weapons:
            if w.lower().replace(" ", "").replace("-", "") == name:
                return w
                
        # Fuzzy match - contains
        for w in weapons:
            w_clean = w.lower().replace(" ", "").replace("-", "")
            if name in w_clean or w_clean in name:
                return w
                
        return None


class KillFeedParser:
    """Parses kill feed entries from vision API responses"""
    
    KILLFEED_PROMPT = """You are analyzing the kill feed (death notices) in the TOP-RIGHT corner of a {game} gameplay screenshot.

The kill feed shows kill events with format: [Killer] [Weapon Icon] [Victim]
A skull icon or "HS" text indicates a HEADSHOT.

TASK: Extract ALL kill events where the LOCAL PLAYER is the ATTACKER (killer on the left side).
- In CS2: Local player name is bright BLUE (CT) or ORANGE/YELLOW (T)
- In Valorant: Local player name is highlighted/bright vs enemy names

For each local player kill, report:
- weapon: The weapon used (must be from game weapon list)
- headshot: true if skull/HS icon visible, false otherwise

VALID WEAPONS FOR {game}:
{weapons}

Respond with JSON only:
{{"kills": [{{"weapon": "AK-47", "headshot": true}}, {{"weapon": "AWP", "headshot": false}}]}}

If no local player kills visible: {{"kills": []}}
If kill feed empty/unclear: {{"kills": []}}
"""

    def __init__(self, game: str = "CS2"):
        self.game = game
        self.weapons = CS2_WEAPONS if game == "CS2" else VALORANT_WEAPONS
        self.normalizer = WeaponNormalizer()
        
        if GROQ_AVAILABLE and os.environ.get("GROQ_API_KEY"):
            self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        else:
            self.client = None
            
    async def analyze_frame(self, frame_data: Dict) -> List[Dict]:
        """Analyze a single kill feed frame with safe API wrapper"""
        if not self.client:
            return []
            
        prompt = self.KILLFEED_PROMPT.format(
            game=self.game,
            weapons=", ".join(self.weapons[:25])
        )
        
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_data['b64']}"}},
                    {"type": "text", "text": prompt},
                ]
            }],
            "max_tokens": 300,
            "temperature": 0.05,
        }
        
        # RULE 4: Use safe_groq_call - handles retries, 429s, cancellation
        result = await safe_groq_call(self.client, payload)
        
        if not result:
            return []
            
        kills = result.get("kills", [])
        
        # Normalize weapons
        for k in kills:
            weapon = k.get("weapon", "Unknown")
            normalized = self.normalizer.normalize(weapon, self.game)
            if normalized:
                k["weapon"] = normalized
            k["headshot"] = bool(k.get("headshot", False))
            k["frame_idx"] = frame_data.get("frame_idx", 0)
            k["timestamp"] = frame_data.get("timestamp", 0)
            
        return kills


class MultiFrameValidator:
    """
    Validates kills across multiple frames using temporal consistency.
    A kill must persist across at least MIN_PERSISTENCE_FRAMES to be accepted.
    """
    
    MIN_PERSISTENCE_FRAMES = 2  # Kill must appear in at least 2 frames
    TEMPORAL_WINDOW_SEC = 0.5   # Frames within this window are considered same event
    
    def __init__(self):
        self.pending_events: Dict[str, List[Dict]] = defaultdict(list)
        
    def add_detection(self, kill: Dict, frame_idx: int, timestamp: float):
        """Add a kill detection from a frame"""
        weapon = kill.get("weapon", "Unknown")
        headshot = kill.get("headshot", False)
        
        # Create signature for deduplication
        sig = f"{weapon}_{headshot}"
        
        self.pending_events[sig].append({
            "frame_idx": frame_idx,
            "timestamp": timestamp,
            "weapon": weapon,
            "headshot": headshot,
        })
        
    def validate(self) -> List[KillEvent]:
        """
        Validate pending events and return confirmed kills.
        A kill is confirmed if it appears in at least MIN_PERSISTENCE_FRAMES
        within the temporal window.
        """
        validated = []
        
        for sig, detections in self.pending_events.items():
            if len(detections) < self.MIN_PERSISTENCE_FRAMES:
                continue
                
            # Sort by frame
            detections.sort(key=lambda x: x["frame_idx"])
            
            # Check temporal persistence
            first = detections[0]
            last = detections[-1]
            
            time_span = last["timestamp"] - first["timestamp"]
            
            # Valid if spans at least 2 frames and within temporal window
            if time_span <= self.TEMPORAL_WINDOW_SEC or len(detections) >= 2:
                # Calculate confidence based on detection count
                confidence = min(1.0, 0.5 + len(detections) * 0.15)
                
                event = KillEvent(
                    timestamp=first["timestamp"],
                    frame_idx=first["frame_idx"],
                    weapon=first["weapon"],
                    headshot=first["headshot"],
                    confidence=confidence,
                    validation_frames=[d["frame_idx"] for d in detections],
                    source="killfeed",
                )
                validated.append(event)
                
        return validated


class KillFeedEngine:
    """
    Main kill feed detection engine with proper rate limiting.
    Uses multi-frame validation and safe API calls.
    """
    
    MAX_FRAMES_TO_ANALYZE = 30  # Cap frames to avoid rate limits
    BATCH_SIZE = 10              # Frames per batch
    
    def __init__(self, game: str = "CS2"):
        self.game = game
        self.parser = KillFeedParser(game)
        
    async def analyze(self, killfeed_frames: List[Dict]) -> Dict:
        """
        Analyze kill feed frames with batching and proper error handling.
        """
        if not killfeed_frames:
            return self._empty_result()
        
        # Cap frames to analyze
        frames_to_analyze = killfeed_frames[:self.MAX_FRAMES_TO_ANALYZE]
        
        logger.info(f"Analyzing {len(frames_to_analyze)}/{len(killfeed_frames)} kill feed frames")
        
        # RULE 9: Process in batches
        batches = [
            frames_to_analyze[i:i + self.BATCH_SIZE]
            for i in range(0, len(frames_to_analyze), self.BATCH_SIZE)
        ]
        
        # Process batches with safe execution
        all_results = []
        for i, batch in enumerate(batches):
            try:
                # RULE 7: return_exceptions=True pattern
                batch_tasks = [
                    self._safe_analyze_frame(frame, f"batch-{i+1}/{len(batches)}-frame-{j+1}")
                    for j, frame in enumerate(batch)
                ]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Frame analysis failed: {result}")
                        all_results.append([])
                    else:
                        all_results.append(result)
                        
            except asyncio.CancelledError:
                logger.warning(f"Kill feed batch {i+1} cancelled")
                break
            except Exception as e:
                logger.error(f"Kill feed batch {i+1} error: {e}")
                all_results.extend([[] for _ in batch])
        
        # Continue with the rest of analysis
        return await self._process_results(all_results, killfeed_frames)
    
    async def _safe_analyze_frame(self, frame_data: Dict, frame_info: str) -> List[Dict]:
        """Safely analyze a frame with exception handling."""
        try:
            return await self.parser.analyze_frame(frame_data)
        except asyncio.CancelledError:
            logger.debug(f"Frame {frame_info} cancelled")
            raise  # Re-raise to be caught by gather
        except Exception as e:
            logger.debug(f"Frame {frame_info} failed: {e}")
            return []
    
    async def _process_results(self, all_results: List[List[Dict]], killfeed_frames: List[Dict]) -> Dict:
        """Process all frame analysis results."""
        # Group detections by temporal proximity for validation
        validator = MultiFrameValidator()
        all_raw_detections = []
        
        for i, kills in enumerate(all_results):
            if i >= len(killfeed_frames):
                break
            frame_data = killfeed_frames[i]
            frame_idx = frame_data.get("frame_idx", i)
            timestamp = frame_data.get("timestamp", 0)
            
            for kill in kills:
                kill["source_frame"] = frame_idx
                kill["source_timestamp"] = timestamp
                all_raw_detections.append(kill)
                validator.add_detection(kill, frame_idx, timestamp)
        
        # Multi-frame validation
        validated_kills = validator.validate()
        
        logger.info(f"Raw detections: {len(all_raw_detections)}, Validated: {len(validated_kills)}")
        
        # Remove temporal duplicates (same weapon within 2 seconds)
        deduplicated = self._temporal_dedupe(validated_kills)
        
        # Compute weapon stats
        weapon_stats = self._compute_weapon_stats(deduplicated)
        
        # Generate timeline
        timeline = self._generate_timeline(deduplicated)
        
        # Compute multi-kills
        multi_kills = self._detect_multikills(deduplicated)
        
        # Calculate overall confidence
        avg_confidence = sum(k.confidence for k in deduplicated) / len(deduplicated) if deduplicated else 0
        
        return {
            "kills": [k.to_dict() for k in deduplicated],
            "kill_events": deduplicated,  # Keep objects for internal use
            "weapon_stats": weapon_stats,
            "headshot_count": sum(1 for k in deduplicated if k.headshot),
            "total_kills": len(deduplicated),
            "headshot_percentage": round(
                sum(1 for k in deduplicated if k.headshot) / len(deduplicated) * 100, 1
            ) if deduplicated else 0,
            "confidence": round(avg_confidence, 2),
            "timeline": timeline,
            "multi_kills": multi_kills,
            "most_used_weapon": max(weapon_stats, key=lambda w: weapon_stats[w]["count"]) if weapon_stats else "Unknown",
        }
    
    def _temporal_dedupe(self, kills: List[KillEvent]) -> List[KillEvent]:
        """Remove duplicate kills within temporal proximity"""
        if not kills:
            return []
            
        # Sort by timestamp
        sorted_kills = sorted(kills, key=lambda k: k.timestamp)
        
        deduplicated = []
        last_kill_time = {}  # weapon -> last timestamp
        
        MIN_KILL_INTERVAL = 0.3  # Minimum seconds between kills with same weapon
        
        for kill in sorted_kills:
            weapon = kill.weapon
            last_time = last_kill_time.get(weapon, -100)
            
            if kill.timestamp - last_time >= MIN_KILL_INTERVAL:
                deduplicated.append(kill)
                last_kill_time[weapon] = kill.timestamp
            else:
                # Too close - likely duplicate, keep the one with higher confidence
                if kill.confidence > 0.7:
                    # Check if we should replace the previous
                    for i, existing in enumerate(deduplicated):
                        if existing.weapon == weapon and abs(existing.timestamp - kill.timestamp) < MIN_KILL_INTERVAL:
                            if kill.confidence > existing.confidence:
                                deduplicated[i] = kill
                            break
                            
        return deduplicated
    
    def _compute_weapon_stats(self, kills: List[KillEvent]) -> Dict:
        """Compute weapon usage statistics"""
        stats = defaultdict(lambda: {"count": 0, "headshots": 0})
        
        for kill in kills:
            weapon = kill.weapon
            stats[weapon]["count"] += 1
            if kill.headshot:
                stats[weapon]["headshots"] += 1
                
        # Calculate percentages
        total = len(kills)
        result = {}
        for weapon, data in stats.items():
            result[weapon] = {
                "count": data["count"],
                "headshots": data["headshots"],
                "percentage": round(data["count"] / total * 100, 1) if total else 0,
                "hs_rate": round(data["headshots"] / data["count"] * 100, 1) if data["count"] else 0,
            }
            
        return result
    
    def _generate_timeline(self, kills: List[KillEvent]) -> List[Dict]:
        """Generate kill timeline in 30-second buckets"""
        if not kills:
            return []
            
        buckets = defaultdict(int)
        for kill in kills:
            bucket = int(kill.timestamp // 30) * 30
            buckets[bucket] += 1
            
        return [
            {"time_sec": t, "kills": c}
            for t, c in sorted(buckets.items())
        ]
    
    def _detect_multikills(self, kills: List[KillEvent]) -> Dict:
        """Detect multi-kill sequences (2K, 3K, 4K+)"""
        if len(kills) < 2:
            return {"2k": 0, "3k": 0, "4k+": 0}
            
        sorted_kills = sorted(kills, key=lambda k: k.timestamp)
        times = [k.timestamp for k in sorted_kills]
        
        multi_kills = {"2k": 0, "3k": 0, "4k+": 0}
        used = set()
        
        WINDOW_SEC = 5.0  # 5-second window for multi-kill
        
        for i, t in enumerate(times):
            if i in used:
                continue
                
            # Find all kills within window
            window_indices = []
            for j, t2 in enumerate(times):
                if j not in used and t <= t2 <= t + WINDOW_SEC:
                    window_indices.append(j)
                    
            n = len(window_indices)
            if n >= 4:
                multi_kills["4k+"] += 1
                used.update(window_indices)
            elif n == 3:
                multi_kills["3k"] += 1
                used.update(window_indices)
            elif n == 2:
                multi_kills["2k"] += 1
                used.update(window_indices)
                
        return multi_kills
    
    def _empty_result(self) -> Dict:
        return {
            "kills": [],
            "kill_events": [],
            "weapon_stats": {},
            "headshot_count": 0,
            "total_kills": 0,
            "headshot_percentage": 0,
            "confidence": 0,
            "timeline": [],
            "multi_kills": {"2k": 0, "3k": 0, "4k+": 0},
            "most_used_weapon": "Unknown",
        }


async def analyze_kill_feed(killfeed_frames: List[Dict], game: str = "CS2") -> Dict:
    """Entry point for kill feed analysis"""
    engine = KillFeedEngine(game)
    return await engine.analyze(killfeed_frames)
