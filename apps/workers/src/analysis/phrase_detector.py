"""
Phrase Detection Module for DJ Mixing.

A musical phrase is a coherent section of 8, 16, or 32 bars.
In electronic music: typically 8 or 16 bars.

1 bar = 4 beats
8 bars = 32 beats
16 bars = 64 beats

Electronic music is built in powers of 2.
Major changes ALWAYS happen on the first beat of a new phrase.
This is CRITICAL for DJ mixing - transitions must align to phrases.
"""

import numpy as np
import librosa
from typing import List, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()


def detect_phrases(
    audio: np.ndarray,
    bpm: float,
    beats: List[float],
    sr: int = 44100
) -> List[Dict]:
    """
    Detect musical phrases in the audio.

    Args:
        audio: Audio signal array
        bpm: Tempo in BPM
        beats: List of beat timestamps in seconds
        sr: Sample rate

    Returns:
        List of phrase dicts with start_time, end_time, bar_count, etc.
    """
    if not beats or len(beats) < 8:
        return _estimate_phrases_from_duration(len(audio) / sr, bpm)

    duration = len(audio) / sr
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4

    # Detect downbeats (beat 1 of each bar)
    downbeats = detect_downbeats(beats, bpm)

    if len(downbeats) < 2:
        return _estimate_phrases_from_duration(duration, bpm)

    # Calculate energy and spectral features for phrase boundary detection
    phrase_boundaries = _detect_phrase_boundaries(audio, sr, bpm, downbeats)

    # Build phrase list
    phrases = []
    for i in range(len(phrase_boundaries) - 1):
        start = phrase_boundaries[i]
        end = phrase_boundaries[i + 1]

        # Calculate bar count
        phrase_duration = end - start
        bar_count = round(phrase_duration / bar_duration)

        # Snap to standard phrase lengths (8, 16, or 32)
        if bar_count <= 12:
            bar_count = 8
        elif bar_count <= 24:
            bar_count = 16
        else:
            bar_count = 32

        # Find beat index for this phrase
        beat_start_idx = _find_nearest_beat_index(beats, start)

        phrases.append({
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "bar_count": bar_count,
            "beat_start_index": beat_start_idx,
            "is_phrase_boundary": True,
            "phrase_index": i
        })

    return phrases


def detect_downbeats(beats: List[float], bpm: float) -> List[float]:
    """
    Detect downbeats (beat 1 of each bar) from beat list.

    Args:
        beats: List of beat timestamps
        bpm: Tempo

    Returns:
        List of downbeat timestamps
    """
    if not beats or len(beats) < 4:
        return beats

    beat_duration = 60.0 / bpm

    # Group beats into bars (every 4 beats)
    downbeats = []
    for i in range(0, len(beats), 4):
        downbeats.append(beats[i])

    return downbeats


def _detect_phrase_boundaries(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    downbeats: List[float]
) -> List[float]:
    """
    Detect phrase boundaries using spectral and energy analysis.

    Phrase boundaries are marked by:
    - Significant energy changes
    - Spectral changes (new instruments entering/leaving)
    - Harmonic changes
    """
    bar_duration = (60.0 / bpm) * 4
    duration = len(audio) / sr

    # Calculate features
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
    rms_times = librosa.times_like(rms, sr=sr, hop_length=512)

    # Spectral centroid for timbre changes
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr, hop_length=512)[0]

    # Spectral contrast for fullness changes
    contrast = librosa.feature.spectral_contrast(y=audio, sr=sr, hop_length=512)
    contrast_mean = np.mean(contrast, axis=0)

    # Combine features
    features = np.column_stack([
        rms / (np.max(rms) + 1e-6),
        centroid / (np.max(centroid) + 1e-6),
        contrast_mean / (np.max(contrast_mean) + 1e-6)
    ])

    # Calculate feature changes
    feature_diff = np.sum(np.abs(np.diff(features, axis=0)), axis=1)

    # Smooth the difference signal
    kernel_size = max(5, len(feature_diff) // 100)
    smoothed_diff = np.convolve(feature_diff, np.ones(kernel_size) / kernel_size, mode='same')

    # Find peaks in feature changes
    threshold = np.mean(smoothed_diff) + np.std(smoothed_diff)
    change_indices = np.where(smoothed_diff > threshold)[0]

    # Convert to times and snap to downbeats
    boundaries = [0.0]  # Always start at 0

    # Check every 8 bars if there's a significant change
    for i, downbeat in enumerate(downbeats):
        if i % 2 == 0:  # Every 8 bars (every 2nd downbeat = 8 bars)
            # Check if there's a feature change near this downbeat
            downbeat_frame = int(downbeat * sr / 512)

            # Look in a window around this position
            window = int(bar_duration * sr / 512)
            start_frame = max(0, downbeat_frame - window)
            end_frame = min(len(smoothed_diff), downbeat_frame + window)

            # Check if any change points fall in this window
            relevant_changes = [c for c in change_indices if start_frame <= c <= end_frame]

            if relevant_changes or i % 4 == 0:  # Every 16 bars or at change points
                if downbeat - boundaries[-1] >= bar_duration * 6:  # At least 6 bars since last boundary
                    boundaries.append(downbeat)

    # Ensure we have the end
    if duration - boundaries[-1] > bar_duration * 4:
        boundaries.append(duration)

    return boundaries


def _estimate_phrases_from_duration(duration: float, bpm: float) -> List[Dict]:
    """
    Estimate phrases when beat detection fails.
    """
    bar_duration = (60.0 / bpm) * 4
    phrase_duration = bar_duration * 16  # Assume 16-bar phrases

    phrases = []
    current_time = 0
    phrase_idx = 0

    while current_time < duration:
        end_time = min(current_time + phrase_duration, duration)
        phrases.append({
            "start_time": round(current_time, 3),
            "end_time": round(end_time, 3),
            "bar_count": 16,
            "beat_start_index": int(current_time / (60.0 / bpm)),
            "is_phrase_boundary": True,
            "phrase_index": phrase_idx
        })
        current_time = end_time
        phrase_idx += 1

    return phrases


def _find_nearest_beat_index(beats: List[float], time: float) -> int:
    """Find the index of the beat nearest to the given time."""
    if not beats:
        return 0

    beats_array = np.array(beats)
    idx = np.argmin(np.abs(beats_array - time))
    return int(idx)


def get_phrase_at_time(phrases: List[Dict], time: float) -> Optional[Dict]:
    """
    Get the phrase that contains the given time.

    Args:
        phrases: List of phrase dicts
        time: Time in seconds

    Returns:
        Phrase dict or None
    """
    for phrase in phrases:
        if phrase["start_time"] <= time < phrase["end_time"]:
            return phrase
    return None


def find_nearest_phrase_boundary(
    phrases: List[Dict],
    time: float,
    direction: str = "nearest"
) -> Optional[float]:
    """
    Find the nearest phrase boundary to a given time.

    Args:
        phrases: List of phrase dicts
        time: Time in seconds
        direction: "nearest", "before", or "after"

    Returns:
        Time of nearest phrase boundary
    """
    boundaries = []
    for phrase in phrases:
        boundaries.append(phrase["start_time"])
    if phrases:
        boundaries.append(phrases[-1]["end_time"])

    if not boundaries:
        return None

    boundaries = np.array(boundaries)

    if direction == "before":
        valid = boundaries[boundaries <= time]
        return float(valid[-1]) if len(valid) > 0 else None
    elif direction == "after":
        valid = boundaries[boundaries >= time]
        return float(valid[0]) if len(valid) > 0 else None
    else:  # nearest
        idx = np.argmin(np.abs(boundaries - time))
        return float(boundaries[idx])


def calculate_bars_from_time(time_seconds: float, bpm: float) -> float:
    """
    Calculate the number of bars for a given time duration.

    Args:
        time_seconds: Duration in seconds
        bpm: Tempo

    Returns:
        Number of bars
    """
    bar_duration = (60.0 / bpm) * 4
    return time_seconds / bar_duration


def calculate_time_from_bars(bars: int, bpm: float) -> float:
    """
    Calculate time duration for a given number of bars.

    Args:
        bars: Number of bars
        bpm: Tempo

    Returns:
        Duration in seconds
    """
    bar_duration = (60.0 / bpm) * 4
    return bars * bar_duration
