"""
Pipeline package for GameSense AI
"""
from app.pipeline.video_processor import VideoProcessor, extract_all_frame_data
from app.pipeline.kill_feed_engine import KillFeedEngine, analyze_kill_feed
from app.pipeline.stats_reconciler import (
    StatsReconciler, ScoreboardReconciler,
    validate_and_reconcile_stats, reconcile_sources
)
from app.pipeline.orchestrator import run_pipeline
from app.pipeline.safe_api import safe_groq_call, safe_groq_call_batch
from app.pipeline.batched_processors import (
    BatchedGameDetector, BatchedScoreboardDetector,
    BATCH_SIZE, MAX_FRAMES_PER_STAGE
)

__all__ = [
    'VideoProcessor',
    'KillFeedEngine',
    'StatsReconciler',
    'ScoreboardReconciler',
    'run_pipeline',
    'extract_all_frame_data',
    'analyze_kill_feed',
    'validate_and_reconcile_stats',
    'reconcile_sources',
    'safe_groq_call',
    'safe_groq_call_batch',
    'BatchedGameDetector',
    'BatchedScoreboardDetector',
    'BATCH_SIZE',
    'MAX_FRAMES_PER_STAGE',
]
