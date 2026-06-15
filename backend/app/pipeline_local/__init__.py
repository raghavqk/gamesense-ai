"""
Local ML Pipeline - No API Required
Uses YOLOv8 + EasyOCR for gameplay video analysis
"""
from app.pipeline_local.yolo_detector import YOLODetector
from app.pipeline_local.ocr_engine import OCREngine
from app.pipeline_local.stats_aggregator import StatsAggregator, AccuracyEvaluator
from app.pipeline_local.orchestrator_local import LocalPipelineOrchestrator

__all__ = [
    'YOLODetector',
    'OCREngine', 
    'StatsAggregator',
    'AccuracyEvaluator',
    'LocalPipelineOrchestrator',
]
