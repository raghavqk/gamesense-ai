"""
Video Ingestion Engine with Scene Detection
Stage 1 of Multi-Signal Pipeline
"""
import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Crop regions as (x1_ratio, y1_ratio, x2_ratio, y2_ratio)
HUD_REGIONS = {
    "CS2": {
        "killfeed": (0.63, 0.00, 1.00, 0.22),
        "scoreboard_full": (0.20, 0.05, 0.80, 0.95),
        "round_score": (0.35, 0.00, 0.65, 0.08),
        "map_label": (0.00, 0.00, 0.22, 0.12),
        "weapon_hud": (0.45, 0.75, 0.55, 0.95),
        "ammo": (0.52, 0.82, 0.58, 0.90),
    },
    "VALORANT": {
        "killfeed": (0.62, 0.00, 1.00, 0.24),
        "scoreboard_full": (0.10, 0.05, 0.90, 0.92),
        "round_score": (0.38, 0.00, 0.62, 0.07),
        "map_label": (0.00, 0.00, 0.22, 0.12),
        "weapon_hud": (0.43, 0.78, 0.57, 0.95),
        "ability_hud": (0.30, 0.80, 0.42, 0.95),
    },
}


class SceneDetector:
    """Detects scene changes to identify engagement moments - memory efficient"""
    
    def __init__(self, threshold: float = 30.0):
        self.threshold = threshold
        self.prev_frame = None
        
    def detect(self, frame: np.ndarray) -> bool:
        """Returns True if scene change detected - uses small downsample"""
        # Use very small size for scene detection to save memory
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90))  # Smaller than before
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return False
            
        diff = cv2.absdiff(self.prev_frame, gray)
        mean_diff = np.mean(diff)
        # Release memory explicitly
        del self.prev_frame
        self.prev_frame = gray
        del diff
        
        return mean_diff > self.threshold


class VideoProcessor:
    """Extracts frames with adaptive sampling based on scene activity"""
    
    def __init__(self, mode: str = "quick"):
        self.mode = mode
        self.target_fps = 2.0 if mode == "full" else 1.0
        self.scene_detector = SceneDetector()
        
    def process(self, video_path: str) -> Dict:
        """
        Memory-efficient video processing.
        Only stores base64 strings, not raw frame arrays.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Adaptive sampling based on video size
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if file_size_mb > 500:
            # Large file - reduce sampling rate
            self.target_fps = 0.5 if self.mode == "quick" else 1.0
            logger.info(f"Large file detected ({file_size_mb:.0f}MB), reducing sampling to {self.target_fps} FPS")
        
        base_stride = max(1, int(fps / self.target_fps))
        
        # Frame storage - only metadata and base64, no raw frames
        frames = {
            "detection": [],      # For game/map detection
            "killfeed": [],       # Kill feed region crops
            "scoreboard": [],     # Scoreboard detection
            "scene_changes": [],  # Scene change timestamps
        }
        
        # Hash tracking for deduplication
        prev_hashes = {
            "killfeed": None,
            "scoreboard": None,
        }
        
        frame_idx = 0
        detection_count = 0
        scene_boost = 0
        processed_count = 0
        
        logger.info(f"Processing video: {width}x{height} @ {fps:.1f}fps, duration={duration:.1f}s, frames={total_frames}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            timestamp = frame_idx / fps
            
            # Scene change detection - uses memory-efficient approach
            is_scene_change = self.scene_detector.detect(frame)
            if is_scene_change:
                frames["scene_changes"].append(timestamp)
                scene_boost = int(fps / 4)  # Reduced boost for memory
                
            # Determine if we should sample this frame
            should_sample = (frame_idx % base_stride == 0) or (scene_boost > 0)
            
            if should_sample:
                processed_count += 1
                
                # Detection frames (first 8 frames for game/map) - encode immediately, don't store raw
                if detection_count < 8:
                    small = cv2.resize(frame, (320, 180))
                    frames["detection"].append({
                        "timestamp": timestamp,
                        "frame_idx": frame_idx,
                        "b64": self._encode_frame(small, quality=70)
                    })
                    detection_count += 1
                    del small  # Free memory
                
                # Kill feed extraction - encode immediately
                killfeed_crop = self._extract_region(frame, "killfeed", width, height)
                if killfeed_crop is not None:
                    killfeed_hash = self._compute_region_hash(killfeed_crop)
                    if killfeed_hash != prev_hashes["killfeed"]:
                        frames["killfeed"].append({
                            "timestamp": timestamp,
                            "frame_idx": frame_idx,
                            "b64": self._encode_frame(killfeed_crop, quality=85),
                            "hash": killfeed_hash,
                        })
                        prev_hashes["killfeed"] = killfeed_hash
                    del killfeed_crop  # Free memory
                
                # Scoreboard extraction (every 5th sampled frame)
                if frame_idx % (base_stride * 5) == 0:
                    scoreboard_crop = self._extract_region(frame, "scoreboard_full", width, height)
                    if scoreboard_crop is not None:
                        scoreboard_hash = self._compute_region_hash(scoreboard_crop)
                        if scoreboard_hash != prev_hashes["scoreboard"]:
                            frames["scoreboard"].append({
                                "timestamp": timestamp,
                                "frame_idx": frame_idx,
                                "b64": self._encode_frame(scoreboard_crop, quality=80),
                                "hash": scoreboard_hash,
                            })
                            prev_hashes["scoreboard"] = scoreboard_hash
                        del scoreboard_crop  # Free memory
                
                if scene_boost > 0:
                    scene_boost -= 1
                
                # Periodic memory cleanup for large videos
                if processed_count % 1000 == 0:
                    import gc
                    gc.collect()
                    logger.debug(f"Processed {processed_count} frames, cleaned up memory")
                    
            frame_idx += 1
            
            # Early termination for very long videos - cap at 10k frames analyzed
            if processed_count >= 10000:
                logger.warning(f"Reached max frame analysis limit (10000), stopping early")
                break
            
        cap.release()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Cap kill feed frames to prevent API overload and memory issues
        max_killfeed = 80 if self.mode == "full" else 50
        if len(frames["killfeed"]) > max_killfeed:
            # Sample evenly across video duration
            step = len(frames["killfeed"]) / max_killfeed
            indices = [int(i * step) for i in range(max_killfeed)]
            frames["killfeed"] = [frames["killfeed"][i] for i in indices]
        
        logger.info(f"Extracted: {len(frames['killfeed'])} killfeed, "
                   f"{len(frames['scoreboard'])} scoreboard frames")
        
        return {
            "video_info": {
                "path": video_path,
                "width": width,
                "height": height,
                "fps": fps,
                "total_frames": total_frames,
                "duration_sec": duration,
            },
            "frames": frames,
            "processing": {
                "mode": self.mode,
                "target_fps": self.target_fps,
                "scene_changes": len(frames["scene_changes"]),
            }
        }
    
    def _extract_region(self, frame: np.ndarray, region: str, 
                        width: int, height: int, game: str = "CS2") -> Optional[np.ndarray]:
        """Extract a HUD region from frame - memory efficient"""
        regions = HUD_REGIONS.get(game, HUD_REGIONS.get("CS2", {}))
        if region not in regions:
            return None
            
        x1r, y1r, x2r, y2r = regions[region]
        x1, y1 = int(width * x1r), int(height * y1r)
        x2, y2 = int(width * x2r), int(height * y2r)
        
        # Ensure bounds are valid
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)
        
        if x2 <= x1 or y2 <= y1:
            return None
            
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None
            
        # Downsample large crops to save memory
        h, w = crop.shape[:2]
        if w > 640:
            scale = 640 / w
            new_h, new_w = int(h * scale), 640
            crop = cv2.resize(crop, (new_w, new_h))
            
        return crop
    
    def _encode_frame(self, frame: np.ndarray, quality: int = 85) -> str:
        """Encode frame to base64 JPEG"""
        import base64
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buf).decode()
    
    def _compute_region_hash(self, region: np.ndarray) -> int:
        """Compute quick hash for region deduplication"""
        # Downsample and compute sum-based hash
        small = cv2.resize(region, (64, 36))
        return int(small.sum()) % (2 ** 32)


def extract_all_frame_data(video_path: str, mode: str = "quick") -> Dict:
    """Main entry point - backwards compatible with old API"""
    import os
    # Check file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    processor = VideoProcessor(mode=mode)
    return processor.process(video_path)
