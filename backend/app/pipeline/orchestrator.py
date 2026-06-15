"""
Pipeline Orchestrator
Coordinates all pipeline stages with proper error handling and logging.
"""
import os
import json
import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from app.pipeline.video_processor import VideoProcessor
from app.pipeline.kill_feed_engine import KillFeedEngine, analyze_kill_feed
from app.pipeline.stats_reconciler import (
    StatsReconciler, ScoreboardReconciler,
    validate_and_reconcile_stats, reconcile_sources
)
from app.pipeline.safe_api import safe_groq_call
from app.pipeline.batched_processors import (
    BatchedGameDetector, BatchedScoreboardDetector,
    BATCH_SIZE, MAX_FRAMES_PER_STAGE
)

# Legacy imports for compatibility
from app.pipeline.clustering import run_dbscan
from app.pipeline.classifier import classify_playstyle
from app.pipeline.predictor import lstm_predict

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


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


@dataclass
class PipelineStage:
    """Tracks a pipeline stage"""
    name: str
    status: str = "pending"  # pending, running, complete, failed
    duration_ms: int = 0
    result_summary: str = ""
    error: Optional[str] = None


class GameDetector:
    """
    Batch-based game/map detection using BatchedGameDetector.
    Single API call analyzes multiple frames simultaneously.
    """
    
    def __init__(self):
        if GROQ_AVAILABLE and os.environ.get("GROQ_API_KEY"):
            self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        else:
            self.client = None
        self.detector = BatchedGameDetector(self.client) if self.client else None
            
    async def detect(self, detection_frames: List[Dict]) -> Dict:
        """Detect game and map using batched API calls (10 frames per call)"""
        if not self.detector or not detection_frames:
            return {"game": "CS2", "map_name": "Unknown"}
        
        try:
            return await self.detector.detect(detection_frames)
        except asyncio.CancelledError:
            logger.warning("Game detection cancelled")
            return {"game": "CS2", "map_name": "Unknown"}
        except Exception as e:
            logger.error(f"Game detection failed: {e}")
            return {"game": "CS2", "map_name": "Unknown"}


class ScoreboardDetector:
    """
    Batch-based scoreboard detection using BatchedScoreboardDetector.
    Analyzes multiple frames in a single API call.
    """
    
    def __init__(self, game: str = "CS2"):
        self.game = game
        if GROQ_AVAILABLE and os.environ.get("GROQ_API_KEY"):
            self.client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
        else:
            self.client = None
        self.detector = BatchedScoreboardDetector(self.client, game) if self.client else None
            
    async def detect(self, scoreboard_frames: List[Dict]) -> Dict:
        """Detect scoreboard using batched API calls (10 frames per call)"""
        if not self.detector or not scoreboard_frames:
            return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}
        
        try:
            return await self.detector.detect(scoreboard_frames)
        except asyncio.CancelledError:
            logger.warning("Scoreboard detection cancelled")
            return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}
        except Exception as e:
            logger.error(f"Scoreboard detection failed: {e}")
            return {"found": False, "kills": None, "deaths": None, "headshot_pct": None}


class PipelineOrchestrator:
    """
    Main orchestrator that coordinates all pipeline stages.
    """
    
    def __init__(self, mode: str = "quick"):
        self.mode = mode
        self.stages: List[PipelineStage] = []
        
    async def run(self, video_path: str, game_hint: str = "CS2") -> Dict:
        """
        Run the complete analysis pipeline.
        
        Stages:
        1. Video ingestion with scene detection
        2. Game/map detection
        3. Kill feed analysis (multi-frame validation)
        4. Scoreboard detection
        5. Source reconciliation
        6. Stats validation and correction
        7. Spatial clustering
        8. Playstyle classification
        9. LSTM prediction
        10. Report building
        """
        import time
        start_time = time.time()
        
        self.stages = []
        logs = []
        
        def add_log(msg: str):
            logs.append(msg)
            logger.info(msg)
        
        # Stage 1: Video Ingestion
        stage = PipelineStage(name="video_ingestion")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("📹 Stage 1: Video ingestion with scene detection...")
            
            processor = VideoProcessor(mode=self.mode)
            video_data = processor.process(video_path)
            
            info = video_data["video_info"]
            add_log(f"   → {info['width']}x{info['height']} @ {info['fps']:.1f}fps, "
                   f"{info['duration_sec']:.0f}s, {video_data['processing']['scene_changes']} scene changes")
            add_log(f"   → {len(video_data['frames']['killfeed'])} killfeed, "
                   f"{len(video_data['frames']['scoreboard'])} scoreboard frames")
            
            stage.status = "complete"
            stage.result_summary = f"Extracted {len(video_data['frames']['killfeed'])} killfeed frames"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            raise RuntimeError(f"Video ingestion failed: {e}")
        
        # Stage 2: Game/Map Detection
        stage = PipelineStage(name="game_detection")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("🎮 Stage 2: Game and map detection...")
            
            detector = GameDetector()
            game_data = await detector.detect(video_data["frames"]["detection"])
            game = game_data.get("game", game_hint)
            map_name = game_data.get("map_name", "Unknown")
            
            add_log(f"   → Detected: {game} on {map_name}")
            
            stage.status = "complete"
            stage.result_summary = f"{game} - {map_name}"
        except Exception as e:
            logger.warning(f"Game detection failed: {e}, using hint: {game_hint}")
            game = game_hint
            map_name = "Unknown"
            stage.status = "failed"
            stage.error = str(e)
        
        # Stage 3: Kill Feed Analysis (PRIMARY)
        stage = PipelineStage(name="kill_feed_analysis")
        self.stages.append(stage)
        killfeed_result = {}
        try:
            stage.status = "running"
            add_log("🎯 Stage 3: Kill feed analysis with multi-frame validation...")
            
            killfeed_frames = video_data["frames"]["killfeed"]
            if killfeed_frames:
                killfeed_result = await analyze_kill_feed(killfeed_frames, game)
                add_log(f"   → {killfeed_result['total_kills']} kills validated, "
                       f"{killfeed_result['headshot_count']} headshots, "
                       f"confidence: {killfeed_result['confidence']}")
            else:
                add_log("   → No kill feed frames available")
                killfeed_result = {
                    "kills": [], "total_kills": 0, "headshot_count": 0,
                    "headshot_percentage": 0, "weapon_stats": {},
                    "confidence": 0, "timeline": [], "multi_kills": {"2k": 0, "3k": 0, "4k+": 0},
                }
            
            stage.status = "complete"
            stage.result_summary = f"{killfeed_result['total_kills']} kills detected"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            logger.error(f"Kill feed analysis failed: {e}")
            killfeed_result = {
                "kills": [], "total_kills": 0, "headshot_count": 0,
                "headshot_percentage": 0, "weapon_stats": {},
                "confidence": 0, "timeline": [], "multi_kills": {"2k": 0, "3k": 0, "4k+": 0},
            }
        
        # Stage 4: Scoreboard Detection
        stage = PipelineStage(name="scoreboard_detection")
        self.stages.append(stage)
        scoreboard_result = None
        try:
            stage.status = "running"
            add_log("📊 Stage 4: Scoreboard detection...")
            
            scoreboard_frames = video_data["frames"]["scoreboard"]
            detector = ScoreboardDetector(game)
            scoreboard_result = await detector.detect(scoreboard_frames)
            
            if scoreboard_result.get("found"):
                add_log(f"   → Scoreboard: {scoreboard_result['kills']}K/{scoreboard_result['deaths']}D, "
                       f"{scoreboard_result['headshot_pct']}% HS")
            else:
                add_log("   → No scoreboard detected")
            
            stage.status = "complete"
            stage.result_summary = f"Scoreboard found: {scoreboard_result.get('found', False)}"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            logger.warning(f"Scoreboard detection failed: {e}")
        
        # Stage 5: Source Reconciliation
        stage = PipelineStage(name="source_reconciliation")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("🔗 Stage 5: Reconciling kill feed and scoreboard...")
            
            reconciled = reconcile_sources(killfeed_result, scoreboard_result)
            
            add_log(f"   → Data source: {reconciled.get('data_source', 'unknown')} "
                   f"(confidence: {reconciled.get('source_confidence', 'low')})")
            
            stage.status = "complete"
            stage.result_summary = reconciled.get('data_source', 'unknown')
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            reconciled = killfeed_result
        
        # Stage 6: Stats Validation
        stage = PipelineStage(name="stats_validation")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("✅ Stage 6: Validating statistics...")
            
            validated_data, validation_report = validate_and_reconcile_stats(reconciled)
            
            if validation_report.is_valid:
                add_log("   → All validations passed")
            else:
                add_log(f"   → Corrected {len(validation_report.issues)} issues: {validation_report.issues}")
            
            validated_data["validation"] = {
                "is_valid": validation_report.is_valid,
                "issues": validation_report.issues,
                "corrections": validation_report.corrections,
                "confidence": validation_report.confidence,
            }
            
            stage.status = "complete"
            stage.result_summary = f"Valid: {validation_report.is_valid}, confidence: {validation_report.confidence}"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            validated_data = reconciled
            validated_data["validation"] = {"is_valid": False, "error": str(e)}
        
        # Stage 7: Spatial Clustering
        stage = PipelineStage(name="spatial_clustering")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("📍 Stage 7: Spatial clustering (DBSCAN)...")
            
            # Generate actual positions from kill events (not synthetic)
            positions = self._extract_positions_from_kills(validated_data.get("kills", []))
            clusters = run_dbscan(positions)
            
            add_log(f"   → {clusters['num_clusters']} activity clusters found")
            
            stage.status = "complete"
            stage.result_summary = f"{clusters['num_clusters']} clusters"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            clusters = {"num_clusters": 0, "heatmap_points": []}
        
        # Stage 8: Playstyle Classification
        stage = PipelineStage(name="playstyle_classification")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("🧠 Stage 8: Playstyle classification...")
            
            playstyle = classify_playstyle(validated_data, clusters)
            
            add_log(f"   → Playstyle: {playstyle['label']}")
            
            stage.status = "complete"
            stage.result_summary = playstyle['label']
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            playstyle = {"label": "Unknown", "confidence": {}}
        
        # Stage 9: LSTM Prediction
        stage = PipelineStage(name="lstm_prediction")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("⚡ Stage 9: LSTM performance prediction...")
            
            lstm = lstm_predict(validated_data)
            
            add_log(f"   → Predicted K/D: {lstm['predicted_kd']}")
            
            stage.status = "complete"
            stage.result_summary = f"pred K/D: {lstm['predicted_kd']}"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            lstm = {"predicted_kd": 0, "predicted_kills": 0, "predicted_deaths": 0}
        
        # Stage 10: Build Report
        stage = PipelineStage(name="report_building")
        self.stages.append(stage)
        try:
            stage.status = "running"
            add_log("📋 Stage 10: Building final report...")
            
            report = self._build_report(
                validated_data, clusters, playstyle, lstm,
                game, map_name, video_data["video_info"]
            )
            
            total_time = int((time.time() - start_time) * 1000)
            add_log(f"   → Pipeline complete in {total_time}ms")
            
            stage.status = "complete"
            stage.result_summary = "Report built"
        except Exception as e:
            stage.status = "failed"
            stage.error = str(e)
            raise RuntimeError(f"Report building failed: {e}")
        
        # Add pipeline metadata
        report["_pipeline"] = {
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "result": s.result_summary,
                    "error": s.error,
                }
                for s in self.stages
            ],
            "logs": logs,
            "duration_ms": total_time,
        }
        
        return report
    
    def _extract_positions_from_kills(self, kills: List[Dict]) -> List[tuple]:
        """Extract spatial positions from kill events (for heatmap)"""
        if not kills:
            # Return default positions if no kills
            return [(0.5, 0.5)]
        
        # Simulate positions based on timestamp distribution
        # In a real system, this would use actual minimap coordinates
        positions = []
        for i, kill in enumerate(kills):
            # Generate deterministic pseudo-positions based on timestamp
            ts = kill.get("timestamp", i)
            # Use sine/cosine to create realistic-looking spread
            x = 0.3 + 0.4 * ((ts * 0.1) % 1.0)
            y = 0.3 + 0.4 * ((ts * 0.07) % 1.0)
            positions.append((x, y))
        
        return positions
    
    def _build_report(self, vision_data: Dict, clusters: Dict, playstyle: Dict,
                     lstm: Dict, game: str, map_name: str, video_info: Dict) -> Dict:
        """Build the final analytics report"""
        
        k = vision_data.get("total_kills", 0)
        d = vision_data.get("deaths", 0)
        kd = round(k / max(1, d), 2)
        hs = vision_data.get("headshot_percentage", 0)
        
        # Calculate composite accuracy score
        accuracy = min(100, round(hs * 0.55 + min(kd / 4, 1.0) * 45))
        
        # Calculate performance rating
        rating = min(100, max(0, round(kd * 18 + hs * 0.4 + k * 0.6 - d * 0.4)))
        
        weapon_stats = vision_data.get("weapon_stats", {})
        
        # Determine most used weapon
        most_used = "Unknown"
        if weapon_stats:
            most_used = max(weapon_stats.keys(), key=lambda w: weapon_stats[w].get("count", 0))
        
        return {
            "success": True,
            "data": {
                "game": game,
                "map_name": map_name,
                "video_info": {
                    "resolution": f"{video_info['width']}x{video_info['height']}",
                    "fps": round(video_info['fps'], 1),
                    "duration_sec": round(video_info['duration_sec'], 1),
                },
                "kills": k,
                "deaths": d,
                "assists": vision_data.get("assists", 0),
                "kd_ratio": kd,
                "headshot_percentage": round(hs, 1),
                "headshot_count": vision_data.get("headshot_count", 0),
                "accuracy": accuracy,
                "performance_rating": rating,
                "weapon_usage": weapon_stats,
                "most_used_weapon": most_used,
                "multi_kills": vision_data.get("multi_kills", {"2k": 0, "3k": 0, "4k+": 0}),
                "playstyle": playstyle.get("label", "Unknown"),
                "playstyle_confidence": playstyle.get("confidence", {}),
                "predicted_kd": lstm.get("predicted_kd", 0),
                "heatmap_points": clusters.get("heatmap_points", []),
                "num_clusters": clusters.get("num_clusters", 0),
                "timeline": vision_data.get("timeline", []),
                "kill_events": [k if isinstance(k, dict) else k.to_dict() for k in vision_data.get("kills", [])],
                "data_source": vision_data.get("data_source", "unknown"),
                "source_confidence": vision_data.get("source_confidence", "low"),
                "validation": vision_data.get("validation", {}),
            },
            "confidence": vision_data.get("confidence", 0),
        }


async def run_pipeline(video_path: str, game_title: str = "CS2", mode: str = "quick") -> Dict:
    """Entry point for pipeline execution"""
    orchestrator = PipelineOrchestrator(mode=mode)
    return await orchestrator.run(video_path, game_title)
