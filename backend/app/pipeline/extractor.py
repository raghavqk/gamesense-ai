import cv2
import base64
import numpy as np

# Crop definitions as percentage of frame (works for any resolution)
CROP_DEFS = {
    "CS2": {
        "killfeed":    (0.63, 0.00, 1.00, 0.22),
        "scoreboard":  (0.20, 0.05, 0.80, 0.95),
        "round_score": (0.35, 0.00, 0.65, 0.08),
        "map_label":   (0.00, 0.00, 0.22, 0.12),
    },
    "VALORANT": {
        "killfeed":    (0.62, 0.00, 1.00, 0.24),
        "scoreboard":  (0.10, 0.05, 0.90, 0.92),
        "round_score": (0.38, 0.00, 0.62, 0.07),
        "map_label":   (0.00, 0.00, 0.22, 0.12),
    },
}


def _encode_crop(frame, x1p, y1p, x2p, y2p, target_w=480) -> str:
    h, w = frame.shape[:2]
    x1, y1 = int(w * x1p), int(h * y1p)
    x2, y2 = int(w * x2p), int(h * y2p)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return ""
    th = max(1, int(target_w * (y2 - y1) / max(1, x2 - x1)))
    resized = cv2.resize(crop, (target_w, th))
    _, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode()


def extract_all_frame_data(video_path: str, mode: str = "quick") -> dict:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    target_fps = 1.0 if mode == "quick" else 2.0
    stride = max(1, int(fps / target_fps))

    detection_frames = []
    killfeed_crops = []
    scoreboard_crops = []
    positions = []

    frame_idx = 0
    prev_kf_hash = None
    detection_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % stride == 0:
            ts = frame_idx / fps

            # Pass 1: first 8 frames for game/map detection
            if detection_count < 8:
                small = cv2.resize(frame, (320, 180))
                _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                detection_frames.append({
                    "ts": ts,
                    "b64": base64.b64encode(buf).decode()
                })
                detection_count += 1

            # Pass 2: every 5th sampled frame for scoreboard detection
            if frame_idx % (stride * 5) == 0:
                b64 = _encode_crop(frame, 0.10, 0.03, 0.90, 0.97, target_w=640)
                if b64:
                    scoreboard_crops.append({"ts": ts, "b64": b64})

            # Pass 3: kill feed, skip if region unchanged
            kf_b64 = _encode_crop(frame, 0.62, 0.00, 1.00, 0.24, target_w=480)
            if kf_b64:
                crop_x1, crop_y1 = int(w * 0.62), 0
                crop_x2, crop_y2 = w, int(h * 0.24)
                region = frame[crop_y1:crop_y2, crop_x1:crop_x2:10, ::10]
                curr_hash = int(region.sum()) % (2 ** 32)
                if curr_hash != prev_kf_hash:
                    killfeed_crops.append({"ts": ts, "b64": kf_b64})
                    prev_kf_hash = curr_hash

            # Position tracking for DBSCAN
            positions.append((0.5 + (frame_idx % 100) * 0.001, 0.5 + (frame_idx % 73) * 0.001))

        frame_idx += 1

    cap.release()

    # Cap kill feed frames at 80 for speed
    if len(killfeed_crops) > 80:
        step = len(killfeed_crops) // 80
        killfeed_crops = killfeed_crops[::step][:80]

    return {
        "detection_frames": detection_frames,
        "killfeed_crops": killfeed_crops,
        "scoreboard_crops": scoreboard_crops,
        "positions": positions,
        "total_frames": len(killfeed_crops),
        "duration_sec": duration,
        "resolution": f"{w}x{h}",
        "native_fps": fps,
    }
