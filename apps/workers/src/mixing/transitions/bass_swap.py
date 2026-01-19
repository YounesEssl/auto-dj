"""
Bass Swap - THE SACRED RULE of DJ mixing.

RULE: NEVER two bass lines simultaneous for more than 2 beats.

Two bass lines playing together = muddy, confusing, unprofessional sound.
The bass swap solves this by:
1. Track B enters WITHOUT bass (bass at 0, or HPF on lows)
2. Blend the mids and highs of B
3. AT THE SWAP MOMENT (on beat 1 of a phrase):
   - Cut A's bass INSTANTLY
   - Bring B's bass up INSTANTLY
4. Continue blending other elements
5. Fade out A completely

THE SWAP MUST BE CLEAN:
- Instant (ideal)
- Or crossfade of 1 bar MAXIMUM
- NEVER a long crossfade on bass
"""

import numpy as np
from typing import Dict, Tuple, Optional, Literal
import structlog

logger = structlog.get_logger()


def execute_bass_swap(
    bass_a: np.ndarray,
    bass_b: np.ndarray,
    swap_time: float,
    swap_duration: Literal["instant", "1_bar"] = "instant",
    bpm: float = 128.0,
    sr: int = 44100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Execute a bass swap - THE MOST CRITICAL FUNCTION.

    Args:
        bass_a: Bass stem from track A
        bass_b: Bass stem from track B
        swap_time: Time in seconds when swap occurs
        swap_duration: "instant" or "1_bar" crossfade
        bpm: Tempo (needed for 1_bar calculation)
        sr: Sample rate

    Returns:
        Tuple of (modified_bass_a, modified_bass_b)
    """
    swap_sample = int(swap_time * sr)

    # Create copies to avoid modifying originals
    bass_a_modified = bass_a.copy()
    bass_b_modified = bass_b.copy()

    # Validate swap sample is within bounds
    if swap_sample < 0:
        swap_sample = 0
    if swap_sample >= len(bass_a_modified):
        swap_sample = len(bass_a_modified) - 1

    if swap_duration == "instant":
        # INSTANT SWAP - cleanest option
        # A's bass: full until swap, then zero
        # B's bass: zero until swap, then full

        # Small fade (5ms) to avoid click
        fade_samples = int(0.005 * sr)

        # Fade out A
        if swap_sample + fade_samples <= len(bass_a_modified):
            fade_out = np.linspace(1, 0, fade_samples)
            bass_a_modified[swap_sample:swap_sample + fade_samples] *= fade_out
        bass_a_modified[swap_sample + fade_samples:] = 0

        # Fade in B
        if swap_sample - fade_samples >= 0:
            bass_b_modified[:swap_sample - fade_samples] = 0
            fade_in = np.linspace(0, 1, fade_samples)
            bass_b_modified[swap_sample - fade_samples:swap_sample] *= fade_in
        else:
            bass_b_modified[:swap_sample] = 0

    else:  # "1_bar" - maximum allowed crossfade
        # Calculate 1 bar in samples
        bar_samples = int((60.0 / bpm) * 4 * sr)

        # Crossfade over exactly 1 bar
        fade_start = swap_sample - bar_samples // 2
        fade_end = swap_sample + bar_samples // 2

        # Clamp to valid range
        fade_start = max(0, fade_start)
        fade_end = min(len(bass_a_modified), len(bass_b_modified), fade_end)
        actual_fade_samples = fade_end - fade_start

        if actual_fade_samples > 0:
            # Create equal-power crossfade curves
            t = np.linspace(0, 1, actual_fade_samples)
            fade_out = np.cos(t * np.pi / 2)  # 1 -> 0
            fade_in = np.sin(t * np.pi / 2)   # 0 -> 1

            # Apply fades
            bass_a_modified[fade_start:fade_end] *= fade_out
            bass_b_modified[fade_start:fade_end] *= fade_in

        # Zero out the rest
        bass_a_modified[fade_end:] = 0
        bass_b_modified[:fade_start] = 0

    logger.debug(
        "Bass swap executed",
        swap_time=swap_time,
        swap_duration=swap_duration,
        swap_sample=swap_sample
    )

    return bass_a_modified, bass_b_modified


def calculate_bass_swap_time(
    transition_start: float,
    transition_duration_bars: int,
    bpm: float,
    swap_bar: int = None
) -> float:
    """
    Calculate the optimal bass swap time within a transition.

    By default, swap happens at the midpoint of the transition.

    Args:
        transition_start: Start of transition in seconds
        transition_duration_bars: Total transition duration in bars
        bpm: Tempo
        swap_bar: Specific bar number for swap (1-indexed, default=middle)

    Returns:
        Swap time in seconds
    """
    bar_duration = (60.0 / bpm) * 4

    if swap_bar is None:
        # Default to middle of transition
        swap_bar = transition_duration_bars // 2

    # Clamp to valid range
    swap_bar = max(1, min(swap_bar, transition_duration_bars))

    swap_time = transition_start + (swap_bar - 1) * bar_duration

    return swap_time


def validate_bass_swap(
    bass_a: np.ndarray,
    bass_b: np.ndarray,
    sr: int = 44100,
    bpm: float = 128.0,
    max_overlap_beats: float = 2.0
) -> Dict:
    """
    Validate that bass swap is clean (no overlap > 2 beats).

    Args:
        bass_a: Bass stem from track A (after swap applied)
        bass_b: Bass stem from track B (after swap applied)
        sr: Sample rate
        bpm: Tempo
        max_overlap_beats: Maximum allowed overlap in beats

    Returns:
        Dict with validation result and details
    """
    # Calculate threshold for "bass present"
    # Use RMS to detect significant bass
    window_size = int(0.1 * sr)  # 100ms windows

    # Calculate RMS for both tracks
    def calculate_rms_windows(audio, window_size):
        num_windows = len(audio) // window_size
        rms = np.zeros(num_windows)
        for i in range(num_windows):
            start = i * window_size
            end = start + window_size
            rms[i] = np.sqrt(np.mean(audio[start:end] ** 2))
        return rms

    rms_a = calculate_rms_windows(bass_a, window_size)
    rms_b = calculate_rms_windows(bass_b, window_size)

    # Normalize
    max_rms = max(np.max(rms_a), np.max(rms_b), 0.001)
    rms_a_norm = rms_a / max_rms
    rms_b_norm = rms_b / max_rms

    # Threshold for "bass present"
    threshold = 0.1

    # Find overlap regions
    bass_a_present = rms_a_norm > threshold
    bass_b_present = rms_b_norm > threshold

    min_len = min(len(bass_a_present), len(bass_b_present))
    overlap = bass_a_present[:min_len] & bass_b_present[:min_len]

    # Calculate overlap duration
    overlap_windows = np.sum(overlap)
    overlap_seconds = overlap_windows * window_size / sr
    overlap_beats = overlap_seconds / (60.0 / bpm)

    is_valid = overlap_beats <= max_overlap_beats

    result = {
        "valid": is_valid,
        "overlap_beats": round(overlap_beats, 2),
        "overlap_seconds": round(overlap_seconds, 3),
        "max_allowed_beats": max_overlap_beats,
    }

    if not is_valid:
        result["error"] = f"Bass overlap of {overlap_beats:.1f} beats exceeds maximum of {max_overlap_beats} beats"
        logger.warning("Bass swap validation failed", **result)
    else:
        logger.debug("Bass swap validation passed", **result)

    return result


def apply_bass_swap_to_stems(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    swap_time: float,
    swap_duration: Literal["instant", "1_bar"] = "instant",
    bpm: float = 128.0,
    sr: int = 44100
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Apply bass swap to full stem dictionaries.

    Modifies only the bass stems, leaving others unchanged.

    Args:
        stems_a: Stems from track A {drums, bass, vocals, other}
        stems_b: Stems from track B
        swap_time: Swap time in seconds
        swap_duration: "instant" or "1_bar"
        bpm: Tempo
        sr: Sample rate

    Returns:
        Tuple of (modified_stems_a, modified_stems_b)
    """
    # Copy stems to avoid modifying originals
    stems_a_modified = {k: v.copy() if v is not None else None for k, v in stems_a.items()}
    stems_b_modified = {k: v.copy() if v is not None else None for k, v in stems_b.items()}

    # Execute bass swap
    if stems_a_modified.get("bass") is not None and stems_b_modified.get("bass") is not None:
        bass_a_swapped, bass_b_swapped = execute_bass_swap(
            stems_a_modified["bass"],
            stems_b_modified["bass"],
            swap_time,
            swap_duration,
            bpm,
            sr
        )
        stems_a_modified["bass"] = bass_a_swapped
        stems_b_modified["bass"] = bass_b_swapped

    return stems_a_modified, stems_b_modified


def prepare_stems_for_blend(
    stems_b: Dict[str, np.ndarray],
    swap_time: float,
    sr: int = 44100
) -> Dict[str, np.ndarray]:
    """
    Prepare incoming track stems for blending by zeroing bass before swap.

    This ensures track B enters without bass until the swap point.

    Args:
        stems_b: Stems from incoming track
        swap_time: When the bass swap will occur
        sr: Sample rate

    Returns:
        Modified stems with bass zeroed before swap
    """
    stems_modified = {k: v.copy() if v is not None else None for k, v in stems_b.items()}

    swap_sample = int(swap_time * sr)

    if stems_modified.get("bass") is not None:
        # Zero bass before swap point
        if swap_sample > 0:
            stems_modified["bass"][:swap_sample] = 0

        # Small fade in at swap point (5ms)
        fade_samples = int(0.005 * sr)
        if swap_sample + fade_samples <= len(stems_modified["bass"]):
            fade_in = np.linspace(0, 1, fade_samples)
            stems_modified["bass"][swap_sample:swap_sample + fade_samples] *= fade_in

    return stems_modified
