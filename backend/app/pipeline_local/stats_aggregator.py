"""
Stats Aggregation and Accuracy Evaluation
Combines detections from multiple frames and evaluates accuracy vs ground truth
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class KillEvent:
    """Single kill event detected from video"""
    timestamp: float  # Video timestamp in seconds
    weapon: str
    headshot: bool
    confidence: float
    source_frame: int
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'weapon': self.weapon,
            'headshot': self.headshot,
            'confidence': self.confidence,
        }


@dataclass
class WeaponStats:
    """Statistics for a weapon"""
    weapon: str
    kills: int = 0
    headshots: int = 0
    
    @property
    def headshot_percentage(self) -> float:
        if self.kills == 0:
            return 0.0
        return (self.headshots / self.kills) * 100


@dataclass
class AccuracyReport:
    """Accuracy metrics comparing detected vs ground truth"""
    # Detection metrics
    detected_kills: int
    ground_truth_kills: int
    true_positives: int  # Correctly detected kills
    false_positives: int  # False detections
    false_negatives: int  # Missed kills
    
    # Derived metrics
    precision: float = field(init=False)  # TP / (TP + FP)
    recall: float = field(init=False)  # TP / (TP + FN)
    f1_score: float = field(init=False)
    
    # Stat accuracy
    kill_error: int = field(init=False)  # Detected - Ground Truth
    kill_accuracy_pct: float = field(init=False)
    
    # Overall
    overall_score: float = field(init=False)
    
    def __post_init__(self):
        # Calculate precision
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)
        else:
            self.precision = 0.0
        
        # Calculate recall
        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)
        else:
            self.recall = 0.0
        
        # Calculate F1 score
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0
        
        # Kill accuracy
        self.kill_error = self.detected_kills - self.ground_truth_kills
        if self.ground_truth_kills > 0:
            self.kill_accuracy_pct = (1 - abs(self.kill_error) / self.ground_truth_kills) * 100
        else:
            self.kill_accuracy_pct = 0.0
        
        # Overall score (weighted F1)
        self.overall_score = self.f1_score * 100


class StatsAggregator:
    """
    Aggregates stats from multiple frame detections.
    Handles multi-frame validation and deduplication.
    """
    
    # Time window for considering kills as duplicates (seconds)
    DEDUPLICATION_WINDOW = 2.0
    
    # Minimum confidence for accepting a detection
    # Lowered to 0.30 to accept pre-processed OCR results (typically 0.35–0.45)
    MIN_CONFIDENCE = 0.30
    
    def __init__(self):
        self.kill_events: List[KillEvent] = []
        self.weapon_stats: Dict[str, WeaponStats] = defaultdict(
            lambda: WeaponStats(weapon="Unknown")
        )
        
    def add_detection(self, timestamp: float, weapon: str, headshot: bool, 
                     confidence: float, source_frame: int):
        """Add a single kill detection from a frame."""
        if confidence < self.MIN_CONFIDENCE:
            return
        
        event = KillEvent(
            timestamp=timestamp,
            weapon=weapon,
            headshot=headshot,
            confidence=confidence,
            source_frame=source_frame
        )
        self.kill_events.append(event)
    
    def add_ocr_stats(self, kills: Optional[int] = None,
                     deaths: Optional[int] = None,
                     assists: Optional[int] = None,
                     headshot_pct: Optional[float] = None):
        """Add stats extracted via OCR from scoreboard."""
        if kills   is not None: self.ocr_kills       = kills
        if deaths  is not None: self.ocr_deaths      = deaths
        if assists is not None: self.ocr_assists      = assists
        if headshot_pct is not None: self.ocr_headshot_pct = headshot_pct
    
    def aggregate(self) -> Dict:
        """
        Aggregate all detections into final stats.
        
        Process:
        1. Deduplicate kills (same weapon within time window)
        2. Count weapons
        3. Calculate headshot percentage
        4. Merge with OCR stats if available
        
        Returns:
            Dictionary with aggregated stats
        """
        logger.info(f"Aggregating {len(self.kill_events)} raw detections...")
        
        # Deduplicate kills
        deduplicated = self._deduplicate_kills()
        logger.info(f"After deduplication: {len(deduplicated)} unique kills")
        
        # Calculate weapon stats
        weapon_stats = self._calculate_weapon_stats(deduplicated)
        
        # Find most used weapon
        most_used = max(
            weapon_stats.items(),
            key=lambda x: x[1].kills,
            default=("Unknown", WeaponStats("Unknown"))
        )[0]
        
        # Calculate totals
        total_kills = len(deduplicated)
        total_headshots = sum(1 for k in deduplicated if k.headshot)
        headshot_pct = (total_headshots / total_kills * 100) if total_kills > 0 else 0
        
        # Use OCR stats for deaths/assists if available
        deaths = getattr(self, 'ocr_deaths', None)
        assists = getattr(self, 'ocr_assists', None)
        
        # If OCR kills available and more reliable, use that
        if hasattr(self, 'ocr_kills') and self.ocr_kills is not None:
            # Weighted average: 70% OCR, 30% detections (OCR from scoreboard is usually more accurate)
            weighted_kills = int(0.7 * self.ocr_kills + 0.3 * total_kills)
            logger.info(f"Using weighted kills: {weighted_kills} (OCR: {self.ocr_kills}, Detected: {total_kills})")
            total_kills = weighted_kills
        
        # Calculate multi-kills
        multi_kills = self._detect_multikills(deduplicated)
        
        # Generate timeline
        timeline = self._generate_timeline(deduplicated)
        
        # Calculate average confidence
        avg_confidence = sum(k.confidence for k in deduplicated) / len(deduplicated) if deduplicated else 0
        
        # Create weapon usage dict for frontend compatibility
        weapon_usage = {
            w: {
                'count': s.kills,
                'headshots': s.headshots,
                'hs_rate': round(s.headshot_percentage, 1)
            }
            for w, s in weapon_stats.items()
        }
        
        return {
            'kills': total_kills,
            'deaths': deaths or 0,
            'assists': assists or 0,
            'headshot_percentage': round(headshot_pct, 1),
            'kd_ratio': round(total_kills / max(deaths, 1), 2) if deaths else round(total_kills, 2),
            'most_used_weapon': most_used,
            'weapon_usage': weapon_usage,  # Frontend expects this — plain dict only (JSON-serializable)
            # weapon_stats omitted — contains non-JSON-serializable WeaponStats dataclass objects
            'multi_kills': multi_kills,
            'timeline': timeline,
            'kill_events': [k.to_dict() for k in deduplicated],
            'detection_confidence': round(avg_confidence, 2),
            'data_source': 'local_ml_pipeline',
        }
    
    def _deduplicate_kills(self) -> List[KillEvent]:
        """
        Remove duplicate kills based on temporal proximity.
        
        Two kills are considered duplicates if:
        - Same weapon
        - Within DEDUPLICATION_WINDOW seconds
        """
        if not self.kill_events:
            return []
        
        # Sort by timestamp
        sorted_events = sorted(self.kill_events, key=lambda k: k.timestamp)
        
        deduplicated = []
        last_kill_times: Dict[str, float] = {}  # weapon -> last timestamp
        
        for event in sorted_events:
            weapon = event.weapon
            last_time = last_kill_times.get(weapon, -1000)
            
            if event.timestamp - last_time >= self.DEDUPLICATION_WINDOW:
                # New kill
                deduplicated.append(event)
                last_kill_times[weapon] = event.timestamp
            else:
                # Duplicate - keep the one with higher confidence
                existing_idx = next(
                    (i for i, k in enumerate(deduplicated) 
                     if k.weapon == weapon and abs(k.timestamp - event.timestamp) < self.DEDUPLICATION_WINDOW),
                    None
                )
                if existing_idx is not None and event.confidence > deduplicated[existing_idx].confidence:
                    deduplicated[existing_idx] = event
        
        return deduplicated
    
    def _calculate_weapon_stats(self, kills: List[KillEvent]) -> Dict[str, WeaponStats]:
        """Calculate statistics per weapon."""
        stats: Dict[str, WeaponStats] = {}
        
        for kill in kills:
            weapon = kill.weapon
            if weapon not in stats:
                stats[weapon] = WeaponStats(weapon=weapon)
            
            stats[weapon].kills += 1
            if kill.headshot:
                stats[weapon].headshots += 1
        
        return stats
    
    def _detect_multikills(self, kills: List[KillEvent]) -> Dict[str, int]:
        """
        Detect multi-kill events (2K, 3K, 4K+) based on kill timing.
        
        A multi-kill is multiple kills within 5 seconds.
        """
        if not kills:
            return {'2k': 0, '3k': 0, '4k+': 0}
        
        sorted_kills = sorted(kills, key=lambda k: k.timestamp)
        timestamps = [k.timestamp for k in sorted_kills]
        
        multi_kills = {'2k': 0, '3k': 0, '4k+': 0}
        used = set()
        
        for i, t in enumerate(timestamps):
            if i in used:
                continue
            
            # Find kills within 5 seconds
            window = [j for j, t2 in enumerate(timestamps) 
                     if t <= t2 <= t + 5 and j not in used]
            
            n = len(window)
            if n == 2:
                multi_kills['2k'] += 1
                used.update(window)
            elif n == 3:
                multi_kills['3k'] += 1
                used.update(window)
            elif n >= 4:
                multi_kills['4k+'] += 1
                used.update(window)
        
        return multi_kills
    
    def _generate_timeline(self, kills: List[KillEvent], interval: int = 30) -> List[Dict]:
        """
        Generate kill timeline aggregated by time intervals.
        
        Args:
            kills: List of kill events
            interval: Time bucket size in seconds
            
        Returns:
            List of {time_sec, kills} dicts
        """
        if not kills:
            return []
        
        buckets: Dict[int, int] = defaultdict(int)
        
        for kill in kills:
            bucket = int(kill.timestamp // interval) * interval
            buckets[bucket] += 1
        
        timeline = [
            {'time_sec': t, 'kills': c}
            for t, c in sorted(buckets.items())
        ]
        
        return timeline


class AccuracyEvaluator:
    """
    Evaluates detection accuracy by comparing with ground truth.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, detected_stats: Dict, ground_truth: Dict) -> AccuracyReport:
        """
        Compare detected stats with ground truth and generate accuracy report.
        
        Args:
            detected_stats: Stats from ML pipeline
            ground_truth: Actual stats from scoreboard
            
        Returns:
            AccuracyReport with precision, recall, F1 scores
        """
        det_kills = detected_stats.get('kills', 0)
        gt_kills = ground_truth.get('kills', 0)
        
        # For now, use simple comparison
        # In a full implementation, match individual kill events
        
        # Estimate TP, FP, FN
        if det_kills <= gt_kills:
            # We detected fewer kills than actual
            tp = det_kills  # Assume all detected are correct
            fp = 0
            fn = gt_kills - det_kills  # Missed kills
        else:
            # We detected more kills than actual
            tp = gt_kills  # Assume we got all real kills
            fp = det_kills - gt_kills  # False detections
            fn = 0
        
        report = AccuracyReport(
            detected_kills=det_kills,
            ground_truth_kills=gt_kills,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn
        )
        
        logger.info(f"Accuracy Report: Precision={report.precision:.2f}, "
                   f"Recall={report.recall:.2f}, F1={report.f1_score:.2f}")
        
        return report
    
    def generate_summary(self, detected: Dict, ground_truth: Dict, report: AccuracyReport) -> str:
        """Generate human-readable accuracy summary."""
        lines = [
            "=== DETECTION ACCURACY REPORT ===",
            "",
            f"Detected Kills:     {report.detected_kills}",
            f"Actual Kills:       {report.ground_truth_kills}",
            f"Difference:         {report.kill_error:+d}",
            "",
            f"Precision:          {report.precision:.1%} (correct detections / total detections)",
            f"Recall:             {report.recall:.1%} (detected kills / actual kills)",
            f"F1 Score:           {report.f1_score:.2f}",
            "",
            f"Weapon Detection:   {detected.get('most_used_weapon', 'Unknown')}",
            f"Headshot %:         {detected.get('headshot_percentage', 0):.1f}%",
        ]
        
        return "\n".join(lines)
