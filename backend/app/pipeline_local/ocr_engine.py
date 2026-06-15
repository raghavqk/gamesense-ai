"""
OCR Engine for GameSense AI Local Pipeline  (v2 – High-Accuracy)
================================================================
Improvements over v1:
 • Heavy image pre-processing:  CLAHE contrast enhancement, bilateral
   de-noise, adaptive threshold, 2× upscale before OCR.
 • Multi-pass EasyOCR:  paragraph mode + line mode combined, results
   merged by confidence.
 • Comprehensive weapon name list for both CS2 and Valorant.
 • Colour-histogram fallback weapon classification.
 • Kill-event regex parser that handles common kill-feed text patterns.
 • SimpleOCRFallback uses pixel brightness / edge-density heuristics
   on the kill-feed strip to estimate a kill count without EasyOCR.

Target accuracy for well-lit kill-feed crops: ~70–80 % recall.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Weapon knowledge bases
# ──────────────────────────────────────────────────────────────────────────────

CS2_WEAPONS: List[str] = [
    # Rifles
    "AK-47", "AK47", "M4A4", "M4A1-S", "M4A1S", "FAMAS", "Galil AR", "Galil",
    "AUG", "SG 553", "SG553", "SSG 08", "SSG08", "AWP", "SCAR-20", "G3SG1",
    # Pistols
    "Desert Eagle", "Deagle", "Glock-18", "Glock", "USP-S", "USP",
    "P250", "P2000", "Five-SeveN", "CZ75", "CZ75-Auto", "Tec-9",
    "Dual Berettas", "R8 Revolver",
    # SMGs
    "MP9", "MP5-SD", "MP5", "UMP-45", "UMP45", "P90", "MAC-10", "MAC10",
    "PP-Bizon", "Bizon",
    # Heavy
    "M249", "Negev", "Nova", "XM1014", "MAG-7", "Sawed-Off",
    # Other
    "Knife", "Zeus", "Bomb", "HE Grenade", "Flashbang", "Smoke",
    "Incendiary", "Molotov", "Decoy",
]

VALORANT_WEAPONS: List[str] = [
    # Rifles
    "Vandal", "Phantom", "Bulldog", "Guardian", "Outlaw",
    # Snipers
    "Operator", "Marshal",
    # Machine guns
    "Ares", "Odin",
    # SMGs
    "Spectre", "Stinger",
    # Pistols / Sidearms
    "Ghost", "Sheriff", "Frenzy", "Classic", "Shorty",
    # Shotguns
    "Judge", "Bucky",
    # Other
    "Knife", "Ability", "Spike",
]

_ALL_WEAPONS = sorted(
    set(w.lower() for w in CS2_WEAPONS + VALORANT_WEAPONS),
    key=len,
    reverse=True,   # longest match first
)

# Headshot indicator tokens
_HS_TOKENS = {"hs", "headshot", "head", "💀", "⚡", "🎯"}

# Regex helpers
_RE_PCT   = re.compile(r"\b(\d{1,3})\s*%")
_RE_KD_SL = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\b")    # "14 / 7"
_RE_KD_KD = re.compile(r"\bk[:\s]*(\d{1,2})[,\s]+d[:\s]*(\d{1,2})\b", re.I)
_RE_INT   = re.compile(r"\b(\d{1,3})\b")

# Kill-event line patterns  (killer) [weapon] (victim)
# We look for either a weapon name or a headshot indicator per text fragment
_KILL_LINE = re.compile(
    r"(?i)(" + "|".join(re.escape(w) for w in CS2_WEAPONS + VALORANT_WEAPONS) + r")"
)


# ──────────────────────────────────────────────────────────────────────────────
# Image pre-processing helpers
# ──────────────────────────────────────────────────────────────────────────────

def _upscale(img: np.ndarray, scale: float = 2.0) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)),
                      interpolation=cv2.INTER_CUBIC)


def _preprocess_killfeed(img: np.ndarray) -> np.ndarray:
    """
    Pre-process a kill-feed crop for maximum OCR accuracy.
    Steps:
      1. Upscale 2× (improves small-font legibility)
      2. Convert to grayscale
      3. Bilateral filter (preserve edges, reduce noise)
      4. CLAHE (adaptive contrast enhancement)
      5. Otsu threshold → inverted binary (dark text on white)
      6. Morphological closing to join broken character strokes
    """
    img = _upscale(img, 2.0)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise while preserving edges
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # Adaptive contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Otsu global threshold  → binary
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Close small gaps in strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Convert back to BGR for EasyOCR
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def _preprocess_scoreboard(img: np.ndarray) -> np.ndarray:
    """Lighter pre-processing for scoreboard (larger text, less noise)."""
    img = _upscale(img, 1.5)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 50, 50)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


# ──────────────────────────────────────────────────────────────────────────────
# Text parsing helpers
# ──────────────────────────────────────────────────────────────────────────────

def _best_weapon_match(text: str) -> Optional[str]:
    """Return the longest weapon name found in *text* (case-insensitive)."""
    tl = text.lower()
    for w in _ALL_WEAPONS:
        if w in tl:
            # Return the properly-cased original name
            for original in CS2_WEAPONS + VALORANT_WEAPONS:
                if original.lower() == w:
                    return original
            return w.title()
    return None


def _has_headshot(text: str) -> bool:
    tl = text.lower()
    return any(tok in tl for tok in _HS_TOKENS)


def _parse_kill_events(fragments: List[Tuple[str, float]]) -> List[Dict]:
    """
    From a list of (text, confidence) tuples produced by EasyOCR on a
    kill-feed crop, build kill event dicts.

    Strategy:
    • Each line in the kill feed = one kill.
    • We look for weapon names and headshot tokens per fragment.
    • We group nearby fragments by y-coordinate (not available here, so
      we treat each high-confidence fragment as a potential kill row).
    • Conservative: require either a weapon name OR a clear headshot token.
    """
    events: List[Dict] = []

    for text, conf in fragments:
        if conf < 0.30:
            continue

        weapon  = _best_weapon_match(text)
        is_hs   = _has_headshot(text)

        if weapon or is_hs:
            events.append({
                "weapon":     weapon or "Unknown",
                "headshot":   is_hs,
                "confidence": float(conf),
                "raw_text":   text,
            })

    return events


# ──────────────────────────────────────────────────────────────────────────────
# Heuristic kill-count estimator (no OCR library required)
# ──────────────────────────────────────────────────────────────────────────────

def _heuristic_kill_count(frame: np.ndarray) -> int:
    """
    Estimate number of kill-feed rows in *frame* using edge density.

    Kill-feed rows are horizontal bands of high-contrast text.  We
    count horizontal runs of edges to approximate row count.

    Returns an integer 0–6 (reasonable kill-feed entry count).
    """
    if frame is None or frame.size == 0:
        return 0

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Detect horizontal edges (text rows produce these)
    edges = cv2.Canny(gray, 40, 120)

    # Project onto Y axis
    row_energy = edges.sum(axis=1).astype(float)

    # Smooth
    kernel = np.ones(5) / 5
    row_energy = np.convolve(row_energy, kernel, mode="same")

    # Peak detection: find rows with energy > 20% of max
    threshold = row_energy.max() * 0.20
    above = (row_energy > threshold).astype(int)

    # Count rising edges (transitions 0→1)
    transitions = np.diff(above, prepend=0)
    num_rows = int((transitions == 1).sum())

    return min(num_rows, 6)  # cap at 6


# ──────────────────────────────────────────────────────────────────────────────
# SimpleOCRFallback
# ──────────────────────────────────────────────────────────────────────────────

class SimpleOCRFallback:
    """
    Heuristic-only fallback used when EasyOCR is not installed.
    Uses edge-density row counting to estimate kill count.
    Returns dummy weapon names but correct headshot=False.
    """

    def extract_kill_feed(self, frame: np.ndarray) -> List[Dict]:
        count = _heuristic_kill_count(frame)
        events = []
        for _ in range(count):
            events.append({
                "weapon":     "Unknown",
                "headshot":   False,
                "confidence": 0.40,
                "raw_text":   "",
            })
        return events

    def extract_scoreboard_stats(self, frame: np.ndarray) -> Dict:  # noqa: ARG002
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# OCREngine  (EasyOCR-backed)
# ──────────────────────────────────────────────────────────────────────────────

class OCREngine:
    """
    High-accuracy OCR engine backed by EasyOCR.

    Pipeline per frame:
      1. Image pre-processing (contrast, denoise, threshold, upscale)
      2. Multi-pass EasyOCR  (paragraph + line modes combined)
      3. Result de-duplication and confidence filtering
      4. Weapon-name and headshot-token parsing

    Gracefully degrades to a no-op if EasyOCR is not installed.
    """

    def __init__(self, use_gpu: bool = False):
        self.reader = None
        try:
            import easyocr  # type: ignore
            # ['en'] is sufficient for game HUDs
            self.reader = easyocr.Reader(
                ["en"],
                gpu=use_gpu,
                verbose=False,
                # Recognizer optimised for single-line game text
                recog_network="standard",
            )
            logger.info("EasyOCR v2 engine initialised (gpu=%s)", use_gpu)
        except ImportError:
            logger.warning(
                "EasyOCR not installed – OCR features disabled. "
                "Run:  pip install easyocr"
            )
        except Exception as exc:
            logger.warning("EasyOCR failed to initialise: %s", exc)

    # ── Public interface ────────────────────────────────────────────────────

    def extract_kill_feed(self, frame: np.ndarray) -> List[Dict]:
        """
        Extract kill events from a kill-feed crop.

        Returns a list of dicts:
            { weapon, headshot, confidence, raw_text }
        """
        if frame is None or frame.size == 0:
            return []

        if self.reader is None:
            return SimpleOCRFallback().extract_kill_feed(frame)

        processed = _preprocess_killfeed(frame)
        fragments  = self._multi_pass_ocr(processed)

        # Parse weapon / headshot events
        events = _parse_kill_events(fragments)

        # If no events but we have significant text, try raw frame too
        if not events:
            raw_frags = self._multi_pass_ocr(frame)
            events = _parse_kill_events(raw_frags)

        # Final heuristic guard: if OCR produced 0 events but the image
        # has enough edge density to suggest ≥1 kill row, synthesise one
        if not events:
            est = _heuristic_kill_count(frame)
            for _ in range(est):
                events.append({
                    "weapon":     "Unknown",
                    "headshot":   False,
                    "confidence": 0.38,
                    "raw_text":   "",
                })

        return events

    def extract_scoreboard_stats(self, frame: np.ndarray) -> Dict:
        """
        Extract K/D/A and headshot-% from a scoreboard crop.

        Returns a dict with any subset of:
            kills (int), deaths (int), assists (int), headshot_pct (float)
        """
        if frame is None or frame.size == 0:
            return {}

        if self.reader is None:
            return {}

        processed  = _preprocess_scoreboard(frame)
        fragments  = self._multi_pass_ocr(processed)
        full_text  = " ".join(t for t, _ in fragments if _ >= 0.25)

        # Try raw frame too and merge
        raw_frags  = self._multi_pass_ocr(frame)
        full_text2 = " ".join(t for t, _ in raw_frags if _ >= 0.25)
        full_text  = full_text + " " + full_text2

        return _parse_scoreboard_text(full_text)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _multi_pass_ocr(
        self, img: np.ndarray
    ) -> List[Tuple[str, float]]:
        """
        Run EasyOCR in two passes (paragraph=True and False) and merge.
        Returns list of (text, confidence) with duplicates removed.
        """
        seen: Dict[str, float] = {}

        for paragraph in (False, True):
            try:
                results = self.reader.readtext(
                    img,
                    detail=1,
                    paragraph=paragraph,
                    width_ths=0.7,
                    ycenter_ths=0.5,
                    height_ths=0.5,
                    add_margin=0.05,
                    min_size=10,
                )
                for _bbox, text, conf in results:
                    text = text.strip()
                    if not text:
                        continue
                    tl = text.lower()
                    # Keep highest-confidence version of each unique text
                    if tl not in seen or conf > seen[tl]:
                        seen[tl] = conf
            except Exception as exc:
                logger.debug("EasyOCR pass failed (paragraph=%s): %s", paragraph, exc)

        return list(seen.items())  # (text_lower, conf)


# ──────────────────────────────────────────────────────────────────────────────
# Scoreboard text parser  (pure regex, no OCR dependency)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_scoreboard_text(text: str) -> Dict:
    """
    Parse OCR text from a scoreboard region into numeric stats.
    Handles common scoreboard layouts for CS2 and Valorant.
    """
    stats: Dict = {}

    # --- K/D/A as slash-separated numbers  e.g. "14 / 7 / 3" ---
    kda_match = re.search(
        r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})\b", text
    )
    if kda_match:
        stats["kills"]   = int(kda_match.group(1))
        stats["deaths"]  = int(kda_match.group(2))
        stats["assists"] = int(kda_match.group(3))

    # --- K/D without assists ---
    if "kills" not in stats:
        kd_match = _RE_KD_SL.search(text)
        if kd_match:
            stats["kills"]  = int(kd_match.group(1))
            stats["deaths"] = int(kd_match.group(2))

    # --- "K: 14  D: 7" style ---
    if "kills" not in stats:
        kd_kw = _RE_KD_KD.search(text)
        if kd_kw:
            stats["kills"]  = int(kd_kw.group(1))
            stats["deaths"] = int(kd_kw.group(2))

    # --- Headshot percentage ---
    for pct in _RE_PCT.finditer(text):
        val = int(pct.group(1))
        if 0 <= val <= 100:
            stats["headshot_pct"] = float(val)
            break

    # --- Fallback: grab first 2–3 bare integers if nothing else found ---
    if "kills" not in stats:
        ints = [int(v) for v in _RE_INT.findall(text) if 0 < int(v) < 100]
        if len(ints) >= 2:
            stats["kills"]  = ints[0]
            stats["deaths"] = ints[1]
        if len(ints) >= 3:
            stats["assists"] = ints[2]

    return stats
