"""
Beatmatching module for tempo synchronization

Uses pyrubberband for high-quality time-stretching without pitch change.
Limits stretching to ±8% to avoid audible artifacts.
"""

from typing import Tuple, List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()

# Maximum allowed tempo change (±8%)
MAX_STRETCH_RATIO = 1.08
MIN_STRETCH_RATIO = 0.92

# Check for pyrubberband availability
_rubberband_available = None


def _check_rubberband() -> bool:
    """Check if pyrubberband is available."""
    global _rubberband_available
    if _rubberband_available is None:
        try:
            import pyrubberband as pyrb
            _rubberband_available = True
            logger.info("pyrubberband available for time-stretching")
        except ImportError:
            _rubberband_available = False
            logger.warning("pyrubberband not available - time-stretching disabled")
    return _rubberband_available


def time_stretch(
    audio: np.ndarray,
    sample_rate: int,
    stretch_ratio: float,
    preserve_pitch: bool = True
) -> np.ndarray:
    """
    Time-stretch audio without changing pitch.

    Args:
        audio: Input audio array
        sample_rate: Sample rate
        stretch_ratio: Ratio to stretch (>1 = faster/shorter, <1 = slower/longer)
        preserve_pitch: Whether to preserve pitch (default True)

    Returns:
        Time-stretched audio
    """
    # Clamp ratio to safe limits
    original_ratio = stretch_ratio
    stretch_ratio = max(MIN_STRETCH_RATIO, min(MAX_STRETCH_RATIO, stretch_ratio))

    if original_ratio != stretch_ratio:
        logger.warning(
            "Stretch ratio clamped to safe limits",
            original=original_ratio,
            clamped=stretch_ratio
        )

    # No change needed
    if abs(stretch_ratio - 1.0) < 0.001:
        return audio

    if not _check_rubberband():
        logger.warning("Time-stretching skipped - pyrubberband not available")
        return audio

    import pyrubberband as pyrb

    logger.debug("Time-stretching audio", ratio=stretch_ratio)

    # pyrubberband expects (samples,) or (samples, channels)
    # rate parameter is the stretch factor
    stretched = pyrb.time_stretch(audio, sample_rate, stretch_ratio)

    return stretched


def pitch_shift(
    audio: np.ndarray,
    sample_rate: int,
    semitones: float
) -> np.ndarray:
    """
    Shift pitch without changing tempo.

    Args:
        audio: Input audio array
        sample_rate: Sample rate
        semitones: Number of semitones to shift (can be fractional)

    Returns:
        Pitch-shifted audio
    """
    if abs(semitones) < 0.01:
        return audio

    if not _check_rubberband():
        logger.warning("Pitch-shifting skipped - pyrubberband not available")
        return audio

    import pyrubberband as pyrb

    logger.debug("Pitch-shifting audio", semitones=semitones)

    shifted = pyrb.pitch_shift(audio, sample_rate, semitones)

    return shifted


def calculate_stretch_ratio(source_bpm: float, target_bpm: float) -> Tuple[float, bool]:
    """
    Calculate the time-stretch ratio needed to match BPMs.

    Also handles half-time and double-time scenarios.

    Args:
        source_bpm: Original BPM of the track
        target_bpm: Target BPM to match

    Returns:
        Tuple of (stretch_ratio, is_within_limits)
        - stretch_ratio: >1 means speed up, <1 means slow down
        - is_within_limits: True if ratio is within ±8%
    """
    ratio = target_bpm / source_bpm

    # Check if half-time or double-time would give better ratio
    half_ratio = (target_bpm / 2) / source_bpm
    double_ratio = (target_bpm * 2) / source_bpm

    # Find the ratio closest to 1.0
    candidates = [
        (ratio, 'normal'),
        (half_ratio, 'half'),
        (double_ratio, 'double')
    ]

    best_ratio, best_mode = min(candidates, key=lambda x: abs(x[0] - 1.0))

    if best_mode != 'normal':
        logger.info(f"Using {best_mode}-time ratio", original=ratio, adjusted=best_ratio)

    is_within_limits = MIN_STRETCH_RATIO <= best_ratio <= MAX_STRETCH_RATIO

    return best_ratio, is_within_limits


def stretch_to_bpm(
    audio: np.ndarray,
    sample_rate: int,
    source_bpm: float,
    target_bpm: float
) -> Tuple[np.ndarray, float]:
    """
    Stretch audio to match a target BPM.

    Args:
        audio: Input audio
        sample_rate: Sample rate
        source_bpm: Original BPM of the audio
        target_bpm: Target BPM to achieve

    Returns:
        Tuple of (stretched_audio, actual_bpm)
        - actual_bpm may differ from target if stretch was clamped
    """
    ratio, is_within_limits = calculate_stretch_ratio(source_bpm, target_bpm)

    if not is_within_limits:
        logger.warning(
            "BPM difference too large for clean stretching",
            source_bpm=source_bpm,
            target_bpm=target_bpm,
            ratio=ratio
        )

    # Clamp ratio
    clamped_ratio = max(MIN_STRETCH_RATIO, min(MAX_STRETCH_RATIO, ratio))

    # Stretch audio
    stretched = time_stretch(audio, sample_rate, clamped_ratio)

    # Calculate actual achieved BPM
    actual_bpm = source_bpm * clamped_ratio

    logger.info(
        "Stretched audio to BPM",
        source_bpm=source_bpm,
        target_bpm=target_bpm,
        actual_bpm=actual_bpm,
        stretch_ratio=clamped_ratio
    )

    return stretched, actual_bpm


def find_nearest_beat(
    time_position: float,
    beats: List[float],
    direction: str = 'nearest'
) -> Tuple[float, int]:
    """
    Find the nearest beat to a given time position.

    Args:
        time_position: Time in seconds
        beats: List of beat timestamps in seconds
        direction: 'nearest', 'before', or 'after'

    Returns:
        Tuple of (beat_time, beat_index)
    """
    if not beats:
        return time_position, -1

    beats_array = np.array(beats)

    if direction == 'before':
        # Find last beat before position
        valid_beats = beats_array[beats_array <= time_position]
        if len(valid_beats) == 0:
            return beats[0], 0
        beat_time = valid_beats[-1]
        beat_idx = np.where(beats_array == beat_time)[0][0]
    elif direction == 'after':
        # Find first beat after position
        valid_beats = beats_array[beats_array >= time_position]
        if len(valid_beats) == 0:
            return beats[-1], len(beats) - 1
        beat_time = valid_beats[0]
        beat_idx = np.where(beats_array == beat_time)[0][0]
    else:
        # Find nearest beat
        distances = np.abs(beats_array - time_position)
        beat_idx = int(np.argmin(distances))
        beat_time = float(beats[beat_idx])

    return beat_time, beat_idx


def find_downbeat(
    start_beat_idx: int,
    beats: List[float],
    beats_per_bar: int = 4
) -> Tuple[float, int]:
    """
    Find the next downbeat (first beat of a bar) from a given beat index.

    Args:
        start_beat_idx: Starting beat index
        beats: List of beat timestamps
        beats_per_bar: Number of beats per bar (usually 4)

    Returns:
        Tuple of (downbeat_time, downbeat_index)
    """
    # Find next beat that's on a bar boundary
    # Assumes first beat in the list is a downbeat
    next_downbeat_idx = start_beat_idx
    while next_downbeat_idx % beats_per_bar != 0:
        next_downbeat_idx += 1
        if next_downbeat_idx >= len(beats):
            # Wrap around or use last available
            next_downbeat_idx = len(beats) - 1
            break

    return beats[next_downbeat_idx], next_downbeat_idx


def align_to_beat(
    audio: np.ndarray,
    sample_rate: int,
    current_beat_time: float,
    target_beat_time: float
) -> np.ndarray:
    """
    Align audio so a beat lands at a specific time position.

    Args:
        audio: Audio array
        sample_rate: Sample rate
        current_beat_time: Current time of the beat in the audio
        target_beat_time: Desired time for the beat

    Returns:
        Shifted audio with aligned beat
    """
    shift_seconds = target_beat_time - current_beat_time
    shift_samples = int(shift_seconds * sample_rate)

    if shift_samples > 0:
        # Need to delay audio (add silence at start)
        silence = np.zeros(shift_samples, dtype=audio.dtype)
        return np.concatenate([silence, audio])
    elif shift_samples < 0:
        # Need to advance audio (trim from start)
        trim_samples = abs(shift_samples)
        if trim_samples >= len(audio):
            logger.warning("Trim amount exceeds audio length")
            return audio
        return audio[trim_samples:]
    else:
        return audio


def get_beat_at_time(
    time_position: float,
    beats: List[float],
    tolerance: float = 0.05
) -> Optional[int]:
    """
    Check if there's a beat at the given time position.

    Args:
        time_position: Time in seconds
        beats: List of beat timestamps
        tolerance: Time tolerance in seconds

    Returns:
        Beat index if found, None otherwise
    """
    for i, beat_time in enumerate(beats):
        if abs(beat_time - time_position) <= tolerance:
            return i
    return None
