"""
Batched Frame Processors - RULE 6: Batch 10-20 frames per API call
Eliminates per-frame API calls to reduce 429 errors.
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.pipeline.safe_api import safe_groq_call_batch, GLOBAL_SEMAPHORE

logger = logging.getLogger(__name__)

# Batch configuration
BATCH_SIZE = 10  # Frames per API call
MAX_FRAMES_PER_STAGE = 30  # Total frames to analyze per stage


@dataclass
class BatchResult:
    """Result from processing a batch of frames"""
    batch_id: int
    frames_analyzed: int
    detections: List[Dict]
    success: bool
    error: Optional[str] = None


class BatchedGameDetector:
    """
    Batch-based game/map detection.
    Analyzes multiple frames in a single API call.
    """
    
    DETECT_PROMPT = """You are analyzing gameplay screenshots.

TASK: Identify the game and map from these frames.

For each frame, provide:
- game: CS2, VALORANT, or Unknown
- map: map name (e.g., de_dust2, Ascent) or "Unknown"
- confidence: 0-1 score

Respond with JSON array, one entry per frame:
[
  {"game": "CS2", "map": "de_mirage", "confidence": 0.9},
  {"game": "VALORANT", "map": "Ascent", "confidence": 0.85}
]
"""
    
    def __init__(self, client):
        self.client = client
    
    async def detect(self, detection_frames: List[Dict]) -> Dict:
        """
        Detect game and map using batched API calls.
        Processes frames in batches of BATCH_SIZE.
        """
        if not self.client or not detection_frames:
            return {"game": "CS2", "map_name": "Unknown"}
        
        # Limit total frames
        frames_to_analyze = detection_frames[:MAX_FRAMES_PER_STAGE]
        logger.info(f"Game detection: analyzing {len(frames_to_analyze)} frames in batches of {BATCH_SIZE}")
        
        # Split into batches
        batches = [
            frames_to_analyze[i:i + BATCH_SIZE] 
            for i in range(0, len(frames_to_analyze), BATCH_SIZE)
        ]
        
        # Process batches with safe task execution (RULE 7)
        tasks = [
            self._process_batch(batch, batch_id=i+1, total=len(batches))
            for i, batch in enumerate(batches)
        ]
        
        # RULE 7: return_exceptions=True to prevent cascading failures
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all detections, filtering out exceptions
        all_detections = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Batch {i+1} failed with exception: {result}")
                continue
            if result and result.success:
                all_detections.extend(result.detections)
        
        # Vote on game and map
        game_votes = {}
        map_votes = {}
        
        for detection in all_detections:
            game = detection.get("game", "")
            if game in ("CS2", "VALORANT"):
                game_votes[game] = game_votes.get(game, 0) + detection.get("confidence", 0.5)
            
            map_name = detection.get("map")
            if map_name and map_name not in ("null", "Unknown", ""):
                map_votes[map_name] = map_votes.get(map_name, 0) + detection.get("confidence", 0.5)
        
        detected_game = max(game_votes, key=game_votes.get) if game_votes else "CS2"
        detected_map = max(map_votes, key=map_votes.get) if map_votes else "Unknown"
        
        logger.info(f"Game detection complete: {detected_game} on {detected_map} (from {len(all_detections)} frame analyses)")
        
        return {
            "game": detected_game,
            "map_name": detected_map,
        }
    
    async def _process_batch(self, batch: List[Dict], batch_id: int, total: int) -> BatchResult:
        """Process a single batch of frames."""
        try:
            # Build multi-frame prompt
            frame_count = len(batch)
            content = [
                {"type": "text", "text": f"{self.DETECT_PROMPT}\n\nAnalyze these {frame_count} frames:"}
            ]
            
            for i, frame in enumerate(batch):
                content.append({"type": "text", "text": f"\n--- Frame {i+1} ---"})
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame['b64']}"}
                })
            
            payload = {
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 400,
                "temperature": 0.05,
            }
            
            result = await safe_groq_call_batch(self.client, payload, f"game-det-{batch_id}/{total}")
            
            if not result:
                return BatchResult(
                    batch_id=batch_id,
                    frames_analyzed=frame_count,
                    detections=[],
                    success=False,
                    error="API call failed"
                )
            
            # Parse array response
            detections = result if isinstance(result, list) else [result]
            
            return BatchResult(
                batch_id=batch_id,
                frames_analyzed=frame_count,
                detections=detections,
                success=True
            )
            
        except asyncio.CancelledError:
            # RULE 8: Handle cancellation gracefully
            logger.warning(f"Batch {batch_id} cancelled")
            return BatchResult(
                batch_id=batch_id,
                frames_analyzed=len(batch),
                detections=[],
                success=False,
                error="cancelled"
            )
        except Exception as e:
            logger.error(f"Batch {batch_id} error: {e}")
            return BatchResult(
                batch_id=batch_id,
                frames_analyzed=len(batch),
                detections=[],
                success=False,
                error=str(e)
            )


class BatchedScoreboardDetector:
    """
    Batch-based scoreboard detection.
    """
    
    SCOREBOARD_PROMPT = """You are analyzing gameplay screenshots.

TASK: Find the BEST scoreboard frame showing player stats.

Look for:
- TAB scoreboard (CS2/VALORANT)
- Round end summary
- Match end MVP screen

From the best scoreboard visible, extract:
- kills: player kills
- deaths: player deaths  
- assists: player assists
- headshot_pct: headshot percentage (0-100)
- is_match_end: true if match complete

Respond ONLY with JSON for the best frame:
{"scoreboard_visible": true, "kills": 15, "deaths": 4, "assists": 3, "headshot_pct": 62, "is_match_end": false}

If no good scoreboard: {"scoreboard_visible": false}
"""
    
    def __init__(self, client, game: str = "CS2"):
        self.client = client
        self.game = game
    
    async def detect(self, scoreboard_frames: List[Dict]) -> Dict:
        """Detect scoreboard using batched processing."""
        if not self.client or not scoreboard_frames:
            return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}
        
        frames_to_analyze = scoreboard_frames[:MAX_FRAMES_PER_STAGE]
        logger.info(f"Scoreboard detection: analyzing {len(frames_to_analyze)} frames in batches of {BATCH_SIZE}")
        
        # Process in batches
        batches = [
            frames_to_analyze[i:i + BATCH_SIZE]
            for i in range(0, len(frames_to_analyze), BATCH_SIZE)
        ]
        
        all_results = []
        for i, batch in enumerate(batches):
            try:
                result = await self._process_batch(batch, i+1, len(batches))
                if result and result.get("scoreboard_visible"):
                    all_results.append(result)
                    # If we found a match-end scoreboard, stop early
                    if result.get("is_match_end"):
                        logger.info(f"Found match-end scoreboard in batch {i+1}, stopping early")
                        break
            except asyncio.CancelledError:
                logger.warning(f"Scoreboard batch {i+1} cancelled")
                break
            except Exception as e:
                logger.warning(f"Scoreboard batch {i+1} error: {e}")
                continue
        
        # Find best result (prefer match end, then highest kills)
        best = None
        best_kills = -1
        
        for r in all_results:
            if not r or not r.get("scoreboard_visible"):
                continue
            kills = r.get("kills", 0)
            is_end = r.get("is_match_end", False)
            
            if is_end or kills > best_kills:
                best = r
                best_kills = kills
                if is_end:
                    break
        
        if best:
            logger.info(f"Scoreboard found: K={best.get('kills')}, D={best.get('deaths')}, HS={best.get('headshot_pct', 0)}%")
            return {
                "found": True,
                "kills": int(best["kills"]),
                "deaths": int(best.get("deaths", 0)),
                "assists": int(best.get("assists", 0)),
                "headshot_pct": int(best.get("headshot_pct", 0)),
                "is_match_end": best.get("is_match_end", False),
            }
        
        logger.info("No scoreboard detected")
        return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}
    
    async def _process_batch(self, batch: List[Dict], batch_id: int, total: int) -> Optional[Dict]:
        """Process a batch of scoreboard frames."""
        frame_count = len(batch)
        
        content = [
            {"type": "text", "text": f"{self.SCOREBOARD_PROMPT}\n\nAnalyze these {frame_count} frames and return the BEST scoreboard found:"}
        ]
        
        for i, frame in enumerate(batch):
            content.append({"type": "text", "text": f"\n--- Frame {i+1} ---"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame['b64']}"}
            })
        
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 200,
            "temperature": 0.05,
        }
        
        return await safe_groq_call_batch(self.client, payload, f"scoreboard-{batch_id}/{total}")
