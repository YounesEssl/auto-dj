"""
Blend / Crossfade Transition - Standard House/Techno technique.

Progressive superposition over 16-64 bars.
The audience should not perceive where one track ends and another begins.

RECOMMENDED DURATIONS:
- Warmup: 32-64 bars (long, smooth)
- Build: 16-32 bars
- Peak: 8-16 bars (shorter, punchier)
- Cooldown: 32-64 bars

CRITICAL RULE:
Never two basses simultaneously > 2 beats → use bass swap
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from .bass_swap import execute_bass_swap, apply_bass_swap_to_stems
import structlog

logger = structlog.get_logger()


def create_blend_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    transition_duration: float,
    crossfade_type: str = "equal_power",
    sr: int = 44100
) -> np.ndarray:
    """
    Create a simple volume crossfade transition (without stems).

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        transition_duration: Duration in seconds
        crossfade_type: "linear" or "equal_power"
        sr: Sample rate

    Returns:
        Blended transition audio
    """
    trans_samples = int(transition_duration * sr)
    trans_samples = min(trans_samples, len(audio_a), len(audio_b))

    # Create crossfade curves
    if crossfade_type == "equal_power":
        # Equal power crossfade (maintains perceived volume)
        t = np.linspace(0, np.pi / 2, trans_samples)
        fade_out = np.cos(t)
        fade_in = np.sin(t)
    else:
        # Linear crossfade
        fade_out = np.linspace(1, 0, trans_samples)
        fade_in = np.linspace(0, 1, trans_samples)

    # Apply fades
    segment_a = audio_a[-trans_samples:] * fade_out
    segment_b = audio_b[:trans_samples] * fade_in

    # Mix together
    blended = segment_a + segment_b

    # Prevent clipping
    max_val = np.max(np.abs(blended))
    if max_val > 1.0:
        blended = blended / max_val * 0.95

    return blended


def create_stem_blend(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    transition_duration_bars: int,
    bpm: float,
    bass_swap_bar: int,
    bass_swap_style: str = "instant",
    phases: Optional[List[Dict]] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a professional stem-based blend transition.

    This is the main function for professional DJ-quality transitions.
    Introduces elements of B progressively while removing elements of A.

    Args:
        stems_a: Stems from track A {drums, bass, vocals, other}
        stems_b: Stems from track B
        transition_duration_bars: Duration in bars
        bpm: Tempo
        bass_swap_bar: Bar number for bass swap (1-indexed)
        bass_swap_style: "instant" or "1_bar"
        phases: Optional custom phase definitions
        sr: Sample rate

    Returns:
        Blended transition audio
    """
    bar_duration = (60.0 / bpm) * 4
    trans_duration = transition_duration_bars * bar_duration
    trans_samples = int(trans_duration * sr)

    # Use default phases if not provided
    if phases is None:
        phases = get_default_phases(transition_duration_bars)

    # Calculate bass swap time
    bass_swap_time = (bass_swap_bar - 1) * bar_duration

    # Apply bass swap to stems
    stems_a_swapped, stems_b_swapped = apply_bass_swap_to_stems(
        stems_a, stems_b,
        swap_time=bass_swap_time,
        swap_duration=bass_swap_style,
        bpm=bpm,
        sr=sr
    )

    # Initialize output
    output = np.zeros(trans_samples, dtype=np.float32)

    # Process each phase
    for phase in phases:
        bar_start = phase["bars"][0] - 1  # Convert to 0-indexed
        bar_end = phase["bars"][1]

        phase_start_sample = int(bar_start * bar_duration * sr)
        phase_end_sample = int(bar_end * bar_duration * sr)
        phase_end_sample = min(phase_end_sample, trans_samples)

        if phase_start_sample >= phase_end_sample:
            continue

        phase_length = phase_end_sample - phase_start_sample

        # Mix stems for this phase
        for stem_name in ["drums", "bass", "other", "vocals"]:
            level_a = phase["a"].get(stem_name, 0)
            level_b = phase["b"].get(stem_name, 0)

            stem_a = stems_a_swapped.get(stem_name)
            stem_b = stems_b_swapped.get(stem_name)

            # Get segments from stems
            if stem_a is not None and len(stem_a) >= phase_end_sample:
                segment_a = stem_a[phase_start_sample:phase_end_sample] * level_a
                output[phase_start_sample:phase_end_sample] += segment_a

            if stem_b is not None and len(stem_b) >= phase_end_sample:
                segment_b = stem_b[phase_start_sample:phase_end_sample] * level_b
                output[phase_start_sample:phase_end_sample] += segment_b

    # Normalize to prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val * 0.95

    return output


def get_default_phases(transition_duration_bars: int) -> List[Dict]:
    """
    Get default 4-phase mixing configuration.

    Default progression:
    - Phase 1: B drums enter quietly
    - Phase 2: B other enters, A starts fading
    - Phase 3: BASS SWAP - B bass full, A bass gone
    - Phase 4: A fades out completely, B at full

    Args:
        transition_duration_bars: Total transition duration

    Returns:
        List of phase configurations
    """
    # Calculate bar ranges for 4 phases
    phase_length = transition_duration_bars // 4

    phases = [
        {
            "bars": [1, phase_length],
            "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0},
            "b": {"drums": 0.3, "bass": 0.0, "other": 0.0, "vocals": 0.0}
        },
        {
            "bars": [phase_length + 1, phase_length * 2],
            "a": {"drums": 1.0, "bass": 1.0, "other": 0.7, "vocals": 0.7},
            "b": {"drums": 0.5, "bass": 0.0, "other": 0.3, "vocals": 0.0}
        },
        {
            "bars": [phase_length * 2 + 1, phase_length * 3],
            "a": {"drums": 0.6, "bass": 0.0, "other": 0.4, "vocals": 0.3},
            "b": {"drums": 0.7, "bass": 1.0, "other": 0.6, "vocals": 0.3}
        },
        {
            "bars": [phase_length * 3 + 1, transition_duration_bars],
            "a": {"drums": 0.2, "bass": 0.0, "other": 0.0, "vocals": 0.0},
            "b": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}
        }
    ]

    return phases


def apply_stem_automation(
    stem: np.ndarray,
    automation_points: List[Dict],
    bar_duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply volume automation to a stem based on bar-level control points.

    Args:
        stem: Stem audio array
        automation_points: List of {"bar": int, "level": float}
        bar_duration: Duration of one bar in seconds
        sr: Sample rate

    Returns:
        Stem with automation applied
    """
    if not automation_points or len(automation_points) < 2:
        return stem

    output = stem.copy()

    # Sort points by bar
    sorted_points = sorted(automation_points, key=lambda x: x["bar"])

    # Create automation envelope
    for i in range(len(sorted_points) - 1):
        start_bar = sorted_points[i]["bar"] - 1  # 0-indexed
        end_bar = sorted_points[i + 1]["bar"] - 1
        start_level = sorted_points[i]["level"]
        end_level = sorted_points[i + 1]["level"]

        start_sample = int(start_bar * bar_duration * sr)
        end_sample = int(end_bar * bar_duration * sr)
        end_sample = min(end_sample, len(output))

        if start_sample >= end_sample:
            continue

        # Create linear interpolation
        num_samples = end_sample - start_sample
        envelope = np.linspace(start_level, end_level, num_samples)

        # Apply envelope
        output[start_sample:end_sample] *= envelope

    return output


def create_smooth_transition_curve(
    length: int,
    curve_type: str = "equal_power"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create smooth fade curves for transitions.

    Args:
        length: Length in samples
        curve_type: "linear", "equal_power", "cosine", "exponential"

    Returns:
        Tuple of (fade_out, fade_in) curves
    """
    if curve_type == "equal_power":
        t = np.linspace(0, np.pi / 2, length)
        fade_out = np.cos(t)
        fade_in = np.sin(t)

    elif curve_type == "cosine":
        t = np.linspace(0, np.pi, length)
        fade_out = (np.cos(t) + 1) / 2
        fade_in = 1 - fade_out

    elif curve_type == "exponential":
        fade_out = np.exp(-3 * np.linspace(0, 1, length))
        fade_in = 1 - np.exp(-3 * np.linspace(0, 1, length))

    else:  # linear
        fade_out = np.linspace(1, 0, length)
        fade_in = np.linspace(0, 1, length)

    return fade_out.astype(np.float32), fade_in.astype(np.float32)


def mix_stems_with_levels(
    stems: Dict[str, np.ndarray],
    levels: Dict[str, float],
    start_sample: int = 0,
    end_sample: Optional[int] = None
) -> np.ndarray:
    """
    Mix stems together with specified levels.

    Args:
        stems: Dict of stem arrays
        levels: Dict of stem levels (0-1)
        start_sample: Start position
        end_sample: End position (None = full length)

    Returns:
        Mixed audio
    """
    # Find minimum length
    lengths = [len(s) for s in stems.values() if s is not None]
    if not lengths:
        return np.array([])

    max_len = max(lengths)
    if end_sample is None:
        end_sample = max_len

    output_length = end_sample - start_sample
    output = np.zeros(output_length, dtype=np.float32)

    for stem_name, stem_audio in stems.items():
        if stem_audio is None:
            continue

        level = levels.get(stem_name, 0)
        if level <= 0:
            continue

        # Extract segment
        seg_start = start_sample
        seg_end = min(end_sample, len(stem_audio))

        if seg_start < seg_end:
            segment = stem_audio[seg_start:seg_end] * level
            output[:len(segment)] += segment

    return output
