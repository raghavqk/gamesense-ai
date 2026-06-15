"""
Stats Reconciler and Validation Engine
Stage 7 - Cross-validation and auto-correction
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Report of validation results"""
    is_valid: bool
    issues: List[str]
    corrections: Dict
    confidence: float
    

class StatsReconciler:
    """
    Cross-validates all statistics and ensures consistency.
    
    Validation Rules:
    1. total_kills == sum(weapon_stats.count)
    2. headshot_count <= total_kills
    3. headshot_percentage == headshot_count / total_kills * 100
    4. multi_kill total <= total_kills / 2
    5. timeline sum == total_kills
    """
    
    def __init__(self):
        self.corrections_applied = []
        
    def validate_and_reconcile(self, data: Dict) -> Tuple[Dict, ValidationReport]:
        """
        Validate and auto-correct statistics.
        Returns (corrected_data, validation_report)
        """
        issues = []
        corrections = {}
        
        # Extract base values
        total_kills = data.get("total_kills", 0) or data.get("kills", 0)
        weapon_stats = data.get("weapon_stats", {})
        headshot_pct = data.get("headshot_percentage", 0)
        headshot_count = data.get("headshot_count", 0)
        timeline = data.get("timeline", [])
        multi_kills = data.get("multi_kills", {"2k": 0, "3k": 0, "4k+": 0})
        
        corrected_data = dict(data)
        
        # Rule 1: Weapon stats sum must equal total kills
        weapon_sum = sum(w.get("count", 0) for w in weapon_stats.values())
        if weapon_sum != total_kills and total_kills > 0:
            issues.append(f"Weapon sum mismatch: {weapon_sum} vs kills {total_kills}")
            
            if weapon_sum > 0:
                # Scale weapons to match kills
                scale = total_kills / weapon_sum
                for weapon, stats in weapon_stats.items():
                    stats["count"] = round(stats["count"] * scale)
                    stats["percentage"] = round(stats["count"] / total_kills * 100, 1)
                    
                corrections["weapon_stats_scaled"] = scale
            else:
                # No weapon data but have kills - distribute evenly
                if total_kills > 0:
                    weapon_stats = {"Unknown": {
                        "count": total_kills,
                        "headshots": headshot_count,
                        "percentage": 100.0,
                        "hs_rate": round(headshot_count / total_kills * 100, 1) if total_kills else 0,
                    }}
                    corrections["weapon_stats_inferred"] = True
                    
            corrected_data["weapon_stats"] = weapon_stats
        
        # Rule 2: Headshot count <= total kills
        if headshot_count > total_kills:
            issues.append(f"Headshot count {headshot_count} > kills {total_kills}")
            headshot_count = total_kills
            headshot_pct = 100.0
            corrections["headshots_clamped"] = True
            corrected_data["headshot_count"] = headshot_count
            corrected_data["headshot_percentage"] = headshot_pct
            
        # Rule 3: Headshot percentage consistency
        if total_kills > 0:
            expected_hs_pct = round(headshot_count / total_kills * 100, 1)
            if abs(expected_hs_pct - headshot_pct) > 1:
                issues.append(f"HS% mismatch: stored {headshot_pct}% vs calculated {expected_hs_pct}%")
                headshot_pct = expected_hs_pct
                corrections["hs_pct_corrected"] = headshot_pct
                corrected_data["headshot_percentage"] = headshot_pct
        
        # Rule 4: Multi-kill sanity check
        mk_total = sum(multi_kills.values())
        # Multi-kill kills = 2*2k + 3*3k + 4*4k+
        mk_kills = 2 * multi_kills.get("2k", 0) + 3 * multi_kills.get("3k", 0) + 4 * multi_kills.get("4k+", 0)
        
        if mk_kills > total_kills:
            issues.append(f"Multi-kill kills {mk_kills} > total kills {total_kills}")
            # Scale down multi-kills proportionally
            if total_kills > 0:
                scale = total_kills / max(1, mk_kills)
                multi_kills = {
                    "2k": int(multi_kills.get("2k", 0) * scale),
                    "3k": int(multi_kills.get("3k", 0) * scale),
                    "4k+": int(multi_kills.get("4k+", 0) * scale),
                }
                corrections["multi_kills_scaled"] = scale
                corrected_data["multi_kills"] = multi_kills
        
        # Rule 5: Timeline sum check
        timeline_sum = sum(t.get("kills", 0) for t in timeline)
        if timeline_sum != total_kills and total_kills > 0:
            issues.append(f"Timeline sum {timeline_sum} != kills {total_kills}")
            # Don't auto-correct timeline, just flag it
            corrections["timeline_mismatch"] = {"expected": total_kills, "actual": timeline_sum}
        
        # Recompute weapon headshot rates to ensure consistency
        if weapon_stats and total_kills > 0:
            total_weapon_headshots = sum(w.get("headshots", 0) for w in weapon_stats.values())
            
            if total_weapon_headshots != headshot_count:
                issues.append(f"Weapon headshots sum {total_weapon_headshots} != total {headshot_count}")
                
                # Distribute headshots proportionally if mismatch
                if headshot_count > 0 and total_weapon_headshots > 0:
                    scale = headshot_count / total_weapon_headshots
                    for weapon, stats in weapon_stats.items():
                        stats["headshots"] = round(stats.get("headshots", 0) * scale)
                        stats["hs_rate"] = round(stats["headshots"] / stats["count"] * 100, 1) if stats["count"] else 0
                    corrections["weapon_headshots_scaled"] = scale
                    corrected_data["weapon_stats"] = weapon_stats
        
        # Calculate confidence based on issues
        confidence = max(0.3, 1.0 - len(issues) * 0.15)
        
        is_valid = len(issues) == 0
        
        report = ValidationReport(
            is_valid=is_valid,
            issues=issues,
            corrections=corrections,
            confidence=round(confidence, 2)
        )
        
        if issues:
            logger.warning(f"Validation issues: {issues}")
            logger.info(f"Corrections applied: {corrections}")
        
        return corrected_data, report


class ScoreboardReconciler:
    """
    Reconciles scoreboard data with kill feed data.
    Scoreboard is authoritative when available.
    """
    
    def __init__(self):
        self.trust_scoreboard = True
        
    def reconcile(self, killfeed_data: Dict, scoreboard_data: Optional[Dict]) -> Dict:
        """
        Merge kill feed and scoreboard data.
        Strategy: Use scoreboard for totals, kill feed for weapon breakdown.
        """
        if not scoreboard_data or not scoreboard_data.get("found"):
            # No scoreboard, trust kill feed
            return {
                **killfeed_data,
                "data_source": "kill_feed",
                "source_confidence": "medium",
            }
        
        sb_kills = scoreboard_data.get("kills", 0)
        sb_deaths = scoreboard_data.get("deaths", 0)
        sb_headshot_pct = scoreboard_data.get("headshot_pct", 0)
        sb_assists = scoreboard_data.get("assists", 0)
        
        kf_kills = killfeed_data.get("total_kills", 0)
        kf_headshots = killfeed_data.get("headshot_count", 0)
        kf_weapon_stats = killfeed_data.get("weapon_stats", {})
        
        result = dict(killfeed_data)
        
        # Decision logic
        if sb_kills > 0:
            # Scoreboard available - use it as authoritative
            result["total_kills"] = sb_kills
            result["kills"] = sb_kills
            result["deaths"] = sb_deaths
            result["headshot_percentage"] = sb_headshot_pct
            result["headshot_count"] = round(sb_kills * sb_headshot_pct / 100) if sb_headshot_pct else 0
            result["assists"] = sb_assists
            result["data_source"] = "scoreboard_authoritative"
            result["source_confidence"] = "high"
            
            # Scale weapon stats to match scoreboard kills
            if kf_kills > 0 and kf_weapon_stats:
                scale = sb_kills / kf_kills
                if 0.5 <= scale <= 2.0:  # Reasonable scaling range
                    scaled_stats = {}
                    for weapon, stats in kf_weapon_stats.items():
                        scaled_count = round(stats["count"] * scale)
                        # Scale headshots proportionally
                        scaled_headshots = round(stats["headshots"] * scale)
                        scaled_stats[weapon] = {
                            "count": scaled_count,
                            "headshots": scaled_headshots,
                            "percentage": round(scaled_count / sb_kills * 100, 1),
                            "hs_rate": round(scaled_headshots / scaled_count * 100, 1) if scaled_count else 0,
                        }
                    result["weapon_stats"] = scaled_stats
                    result["weapon_scaling_applied"] = scale
            else:
                # No kill feed weapon data - create placeholder
                result["weapon_stats"] = {
                    "Unknown": {
                        "count": sb_kills,
                        "headshots": round(sb_kills * sb_headshot_pct / 100) if sb_headshot_pct else 0,
                        "percentage": 100.0,
                        "hs_rate": sb_headshot_pct,
                    }
                }
        else:
            # Scoreboard shows 0 kills, but kill feed has kills
            # Trust kill feed (scoreboard might be from early round)
            result["data_source"] = "kill_feed"
            result["source_confidence"] = "medium"
            
        return result


def validate_and_reconcile_stats(data: Dict) -> Tuple[Dict, ValidationReport]:
    """Entry point for stats validation"""
    reconciler = StatsReconciler()
    return reconciler.validate_and_reconcile(data)


def reconcile_sources(killfeed_data: Dict, scoreboard_data: Optional[Dict]) -> Dict:
    """Entry point for source reconciliation"""
    reconciler = ScoreboardReconciler()
    return reconciler.reconcile(killfeed_data, scoreboard_data)
