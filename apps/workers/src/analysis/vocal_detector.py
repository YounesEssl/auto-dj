"""
Vocal Detection Module for DJ Mixing.

TWO VOCALS SIMULTANEOUS = CATASTROPHE
The system MUST know where vocals are to avoid clashes.

This module uses the vocal stem from Demucs to detect:
- Presence of vocals
- Vocal sections with timestamps
- Vocal intensity (FULL, SPARSE, BACKGROUND)

IMPORTANT: Demucs vocal stems contain residual noise even in instrumental
sections. We use RELATIVE thresholds (% of max energy) to distinguish
actual vocals from residual artifacts.
"""

import numpy as np
import librosa
from typing import Dict, List, Optional, Tuple
from enum import Enum
import structlog

logger = structlog.get_logger()


class VocalIntensity(Enum):
    """Classification of vocal intensity."""
    NONE = "NONE"
    BACKGROUND = "BACKGROUND"  # Background vocals, choirs, pads
    SPARSE = "SPARSE"          # Ad-libs, occasional vocals
    FULL = "FULL"              # Lead vocal, continuous singing


# === THRESHOLDS CONFIGURATION ===
# These are RELATIVE to the max RMS energy in the vocal stem
# This makes detection robust to different recording levels

# Minimum % of max RMS to consider as "vocals present"
# Below this = residual noise from Demucs, not actual vocals
VOCAL_PRESENCE_THRESHOLD_RATIO = 0.15  # 15% of max

# Thresholds for intensity classification (% of max RMS)
FULL_VOCAL_THRESHOLD_RATIO = 0.50     # 50% of max = FULL vocals
SPARSE_VOCAL_THRESHOLD_RATIO = 0.25   # 25% of max = SPARSE vocals
BACKGROUND_VOCAL_THRESHOLD_RATIO = 0.15  # 15% of max = BACKGROUND vocals

# Absolute minimum RMS to avoid detecting pure silence
ABSOLUTE_MIN_RMS = 0.005

# Minimum duration for a vocal section to be valid
MIN_SECTION_DURATION = 0.5  # seconds
MIN_GAP_DURATION = 0.3  # gaps shorter than this are bridged


def detect_vocals(
    audio: np.ndarray,
    sr: int = 44100,
    vocal_stem: Optional[np.ndarray] = None
) -> Dict:
    """
    Detect vocal presence and sections in audio.

    Uses the vocal stem from Demucs if provided, otherwise
    attempts to estimate from the full mix (less accurate).

    Args:
        audio: Full audio signal or vocal stem
        sr: Sample rate
        vocal_stem: Pre-separated vocal stem (recommended)

    Returns:
        Dict with has_vocals, vocal_sections, and intensity info
    """
    # Use vocal stem if provided, otherwise use full audio
    if vocal_stem is not None:
        vocal_audio = vocal_stem
        is_stem = True
    else:
        # Without stem separation, we can only estimate
        logger.warning("No vocal stem provided - using heuristic detection")
        vocal_audio = audio
        is_stem = False

    # Ensure mono for analysis
    if vocal_audio.ndim > 1:
        vocal_audio = np.mean(vocal_audio, axis=0)

    # Calculate RMS energy of vocal track
    rms = librosa.feature.rms(y=vocal_audio, frame_length=2048, hop_length=512)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=512)

    # Calculate statistics
    avg_rms = np.mean(rms)
    max_rms = np.max(rms)
    std_rms = np.std(rms)

    # Calculate the ratio of frames above threshold
    presence_threshold = max_rms * VOCAL_PRESENCE_THRESHOLD_RATIO
    frames_with_vocals = np.sum(rms > presence_threshold)
    vocal_frame_ratio = frames_with_vocals / len(rms) if len(rms) > 0 else 0

    # Debug logging for energy analysis
    logger.debug(
        "Vocal energy analysis",
        avg_rms=f"{avg_rms:.4f}",
        max_rms=f"{max_rms:.4f}",
        std_rms=f"{std_rms:.4f}",
        presence_threshold=f"{presence_threshold:.4f}",
        vocal_frame_ratio=f"{vocal_frame_ratio:.2%}",
        is_stem=is_stem
    )

    # Determine if track has significant vocals
    # Need both: max above absolute minimum AND enough frames above relative threshold
    has_vocals = (
        max_rms > ABSOLUTE_MIN_RMS and
        vocal_frame_ratio > 0.05  # At least 5% of frames have vocals
    )

    if not has_vocals:
        logger.info(
            "No significant vocals detected",
            max_rms=f"{max_rms:.4f}",
            vocal_frame_ratio=f"{vocal_frame_ratio:.2%}"
        )
        return {
            "has_vocals": False,
            "vocal_sections": [],
            "total_vocal_time": 0,
            "vocal_percentage": 0,
            "debug": {
                "max_rms": float(max_rms),
                "avg_rms": float(avg_rms),
                "presence_threshold": float(presence_threshold),
                "vocal_frame_ratio": float(vocal_frame_ratio)
            }
        }

    # Detect vocal sections using relative thresholds
    sections = _detect_vocal_sections(rms, times, max_rms, sr, is_stem)

    # Calculate total vocal time
    total_vocal_time = sum(s["end"] - s["start"] for s in sections)
    duration = len(vocal_audio) / sr
    vocal_percentage = (total_vocal_time / duration) * 100 if duration > 0 else 0

    # Log section summary
    logger.info(
        "Vocal sections detected",
        num_sections=len(sections),
        total_vocal_time=f"{total_vocal_time:.1f}s",
        vocal_percentage=f"{vocal_percentage:.1f}%",
        duration=f"{duration:.1f}s"
    )

    # Log each section for debug
    for i, section in enumerate(sections):
        logger.debug(
            f"Vocal section {i+1}",
            start=f"{section['start']:.1f}s",
            end=f"{section['end']:.1f}s",
            intensity=section["intensity"],
            duration=f"{section['duration']:.1f}s"
        )

    return {
        "has_vocals": has_vocals,
        "vocal_sections": sections,
        "total_vocal_time": round(total_vocal_time, 2),
        "vocal_percentage": round(vocal_percentage, 1),
        "debug": {
            "max_rms": float(max_rms),
            "avg_rms": float(avg_rms),
            "presence_threshold": float(presence_threshold),
            "vocal_frame_ratio": float(vocal_frame_ratio)
        }
    }


def _detect_vocal_sections(
    rms: np.ndarray,
    times: np.ndarray,
    max_rms: float,
    sr: int,
    is_stem: bool
) -> List[Dict]:
    """
    Detect individual vocal sections with intensity classification.

    Uses RELATIVE thresholds based on max RMS to handle varying levels
    and distinguish actual vocals from Demucs residual noise.
    """
    sections = []

    # Calculate thresholds relative to max RMS
    # This is the key fix - using max_rms instead of mean_rms
    if is_stem:
        # For isolated vocal stem - use the configured ratios
        full_threshold = max_rms * FULL_VOCAL_THRESHOLD_RATIO
        sparse_threshold = max_rms * SPARSE_VOCAL_THRESHOLD_RATIO
        background_threshold = max_rms * BACKGROUND_VOCAL_THRESHOLD_RATIO
    else:
        # For full mix (less accurate) - higher thresholds
        full_threshold = max_rms * 0.60
        sparse_threshold = max_rms * 0.35
        background_threshold = max_rms * 0.20

    logger.info(
        "Vocal detection thresholds (relative to max)",
        max_rms=f"{max_rms:.4f}",
        full_threshold=f"{full_threshold:.4f} (50%)",
        sparse_threshold=f"{sparse_threshold:.4f} (25%)",
        background_threshold=f"{background_threshold:.4f} (15%)",
        is_stem=is_stem
    )

    # State machine for section detection
    in_vocal = False
    section_start = 0
    intensity_history = []

    hop_length = 512
    min_section_frames = int(MIN_SECTION_DURATION * sr / hop_length)
    min_gap_frames = int(MIN_GAP_DURATION * sr / hop_length)

    for i, (t, r) in enumerate(zip(times, rms)):
        # Determine intensity at this point
        if r >= full_threshold:
            intensity = VocalIntensity.FULL
        elif r >= sparse_threshold:
            intensity = VocalIntensity.SPARSE
        elif r >= background_threshold:
            intensity = VocalIntensity.BACKGROUND
        else:
            intensity = VocalIntensity.NONE

        if not in_vocal:
            # Check for vocal start
            if intensity != VocalIntensity.NONE:
                in_vocal = True
                section_start = t
                intensity_history = [intensity]
        else:
            # Track intensity during vocal section
            if intensity != VocalIntensity.NONE:
                intensity_history.append(intensity)
            else:
                # Check if this is the end of the vocal section
                # Look ahead to see if vocals resume soon
                if i + min_gap_frames < len(rms):
                    future_rms = rms[i:i + min_gap_frames]
                    if np.max(future_rms) >= background_threshold:
                        # Vocals resume soon, continue section
                        continue

                # End of vocal section
                section_end = t
                section_frames = len(intensity_history)

                if section_frames >= min_section_frames:
                    # Classify overall intensity
                    overall_intensity = _classify_section_intensity(intensity_history)

                    sections.append({
                        "start": round(section_start, 2),
                        "end": round(section_end, 2),
                        "intensity": overall_intensity.value,
                        "duration": round(section_end - section_start, 2)
                    })

                in_vocal = False
                intensity_history = []

    # Handle section that extends to end of track
    if in_vocal and len(intensity_history) >= min_section_frames:
        overall_intensity = _classify_section_intensity(intensity_history)
        sections.append({
            "start": round(section_start, 2),
            "end": round(float(times[-1]), 2),
            "intensity": overall_intensity.value,
            "duration": round(float(times[-1]) - section_start, 2)
        })

    # Merge very close sections
    sections = _merge_close_sections(sections, min_gap=1.0)

    return sections


def _classify_section_intensity(intensity_history: List[VocalIntensity]) -> VocalIntensity:
    """
    Classify overall intensity of a section based on history.
    """
    if not intensity_history:
        return VocalIntensity.NONE

    # Count occurrences
    full_count = sum(1 for i in intensity_history if i == VocalIntensity.FULL)
    sparse_count = sum(1 for i in intensity_history if i == VocalIntensity.SPARSE)
    background_count = sum(1 for i in intensity_history if i == VocalIntensity.BACKGROUND)

    total = len(intensity_history)

    # Classify based on dominant intensity
    if full_count > total * 0.3:
        return VocalIntensity.FULL
    elif sparse_count > total * 0.4:
        return VocalIntensity.SPARSE
    else:
        return VocalIntensity.BACKGROUND


def _merge_close_sections(sections: List[Dict], min_gap: float) -> List[Dict]:
    """
    Merge sections that are very close together.
    """
    if len(sections) < 2:
        return sections

    merged = [sections[0].copy()]

    for section in sections[1:]:
        last = merged[-1]
        gap = section["start"] - last["end"]

        if gap < min_gap:
            # Merge with previous section
            # Take the more intense classification
            intensity_order = {"FULL": 3, "SPARSE": 2, "BACKGROUND": 1, "NONE": 0}
            if intensity_order.get(section["intensity"], 0) > intensity_order.get(last["intensity"], 0):
                last["intensity"] = section["intensity"]
            last["end"] = section["end"]
            last["duration"] = round(last["end"] - last["start"], 2)
        else:
            merged.append(section.copy())

    return merged


def check_vocal_clash(
    vocals_a: Dict,
    vocals_b: Dict,
    transition_start_a: float,
    transition_end_b: float,
    overlap_duration: float
) -> Dict:
    """
    Check if there would be a vocal clash during a transition.

    Args:
        vocals_a: Vocal detection result for track A
        vocals_b: Vocal detection result for track B
        transition_start_a: When transition starts in track A (seconds)
        transition_end_b: When track B audio ends in the transition (seconds)
        overlap_duration: Duration of overlap (seconds)

    Returns:
        Dict with clash info and recommendations
    """
    result = {
        "has_clash": False,
        "clash_severity": "none",
        "recommendations": []
    }

    if not vocals_a.get("has_vocals") or not vocals_b.get("has_vocals"):
        return result

    # Check for vocals in track A during transition
    # Only count vocals that actually overlap with the transition zone
    vocals_in_transition_a = []
    for section in vocals_a.get("vocal_sections", []):
        # Section must START before transition ends AND END after transition starts
        if section["start"] < (transition_start_a + overlap_duration) and section["end"] > transition_start_a:
            vocals_in_transition_a.append(section)

    # Check for vocals in track B during transition (from 0 to overlap_duration)
    # Only count vocals that actually play during the overlap
    vocals_in_transition_b = []
    for section in vocals_b.get("vocal_sections", []):
        # Section must START before overlap ends AND END after overlap starts (which is 0)
        if section["start"] < overlap_duration and section["end"] > 0:
            vocals_in_transition_b.append(section)

    # Log for debugging
    logger.debug(
        "Vocal clash check",
        transition_start_a=transition_start_a,
        overlap_duration=overlap_duration,
        vocals_in_a=len(vocals_in_transition_a),
        vocals_in_b=len(vocals_in_transition_b),
        first_vocal_b_start=vocals_b.get("vocal_sections", [{}])[0].get("start") if vocals_b.get("vocal_sections") else None
    )

    if vocals_in_transition_a and vocals_in_transition_b:
        # Determine severity
        max_intensity_a = max(
            _intensity_to_score(v["intensity"])
            for v in vocals_in_transition_a
        )
        max_intensity_b = max(
            _intensity_to_score(v["intensity"])
            for v in vocals_in_transition_b
        )

        combined_intensity = max_intensity_a + max_intensity_b

        if combined_intensity >= 5:  # Both FULL
            result["has_clash"] = True
            result["clash_severity"] = "severe"
            result["recommendations"] = [
                "Use HARD_CUT transition",
                "Wait for vocals to end before mixing",
                "Lower one track significantly during overlap"
            ]
        elif combined_intensity >= 3:  # One FULL, one SPARSE
            result["has_clash"] = True
            result["clash_severity"] = "moderate"
            result["recommendations"] = [
                "Shorten transition duration",
                "Lower incoming track vocals during overlap",
                "Consider filter sweep to mask clash"
            ]
        elif combined_intensity >= 2:  # Both SPARSE or one SPARSE + BACKGROUND
            result["has_clash"] = True
            result["clash_severity"] = "minor"
            result["recommendations"] = [
                "Monitor levels carefully",
                "Consider brief overlap acceptable"
            ]

    return result


def _intensity_to_score(intensity: str) -> int:
    """Convert intensity string to numeric score."""
    return {"NONE": 0, "BACKGROUND": 1, "SPARSE": 2, "FULL": 3}.get(intensity, 0)


def get_vocal_free_regions(
    vocals: Dict,
    min_duration: float = 4.0,
    track_duration: Optional[float] = None
) -> List[Tuple[float, float]]:
    """
    Find regions without vocals (good for mixing).

    Args:
        vocals: Vocal detection result
        min_duration: Minimum duration of vocal-free region
        track_duration: Total track duration (for finding outro region)

    Returns:
        List of (start, end) tuples for vocal-free regions
    """
    # If no vocals detected, entire track is vocal-free
    if not vocals.get("has_vocals"):
        if track_duration:
            return [(0, track_duration)]
        return []

    sections = vocals.get("vocal_sections", [])
    if not sections:
        if track_duration:
            return [(0, track_duration)]
        return []

    regions = []

    # Log vocal sections for debugging
    logger.info(
        "Searching for vocal-free regions",
        num_vocal_sections=len(sections),
        min_duration=min_duration,
        track_duration=track_duration,
        first_vocal_start=sections[0]["start"] if sections else None,
        last_vocal_end=sections[-1]["end"] if sections else None
    )

    # Check gap before first vocal (INTRO)
    intro_gap = sections[0]["start"]
    if intro_gap >= min_duration:
        regions.append((0, sections[0]["start"]))
        logger.info(
            "Found vocal-free INTRO",
            start=0,
            end=sections[0]["start"],
            duration=intro_gap
        )
    else:
        logger.debug(
            "Intro too short for vocal-free region",
            intro_gap=intro_gap,
            min_duration=min_duration
        )

    # Check gaps between vocals
    for i in range(len(sections) - 1):
        gap_start = sections[i]["end"]
        gap_end = sections[i + 1]["start"]
        gap_duration = gap_end - gap_start
        if gap_duration >= min_duration:
            regions.append((gap_start, gap_end))
            logger.info(
                "Found vocal-free BREAKDOWN",
                start=gap_start,
                end=gap_end,
                duration=gap_duration
            )

    # Check gap after last vocal (OUTRO)
    if track_duration:
        last_vocal_end = sections[-1]["end"]
        outro_gap = track_duration - last_vocal_end
        if outro_gap >= min_duration:
            regions.append((last_vocal_end, track_duration))
            logger.info(
                "Found vocal-free OUTRO",
                start=last_vocal_end,
                end=track_duration,
                duration=outro_gap
            )
        else:
            logger.debug(
                "Outro too short for vocal-free region",
                outro_gap=outro_gap,
                min_duration=min_duration
            )

    # Summary
    logger.info(
        "Vocal-free region detection complete",
        num_regions=len(regions),
        total_vocal_free_time=sum(r[1] - r[0] for r in regions)
    )

    return regions
