"""
Hard Cut Transition - Instant track change.

Instant passage from one track to another on the first beat of a phrase.
Popular in hip-hop, drum & bass, and for moments of surprise.

EXECUTION:
1. Identify cut point on A (end of phrase)
2. Identify entry point on B (start of strong phrase, often the drop)
3. Cut A exactly on beat 1
4. Start B simultaneously

OPTIONS:
- Dry: Direct cut without effect
- Reverb tail: Activate reverb on A before cut, let it fade
- Delay tail: Same principle with delay
- With buildup: Crescendo/riser before cut for maximum impact
"""

import numpy as np
from typing import Dict, Optional, Literal
from ..effects.reverb import apply_reverb, create_reverb_tail
from ..effects.delay import apply_delay_bpm_sync, create_delay_tail
import structlog

logger = structlog.get_logger()


def create_cut_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    cut_point_a: float,
    entry_point_b: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a simple hard cut transition.

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        cut_point_a: Cut time in track A (seconds)
        entry_point_b: Entry time in track B (seconds)
        sr: Sample rate

    Returns:
        Concatenated transition audio
    """
    cut_sample_a = int(cut_point_a * sr)
    entry_sample_b = int(entry_point_b * sr)

    # Validate bounds
    cut_sample_a = min(cut_sample_a, len(audio_a))
    entry_sample_b = min(entry_sample_b, len(audio_b))

    # Extract segments
    segment_a = audio_a[:cut_sample_a]
    segment_b = audio_b[entry_sample_b:]

    # Add tiny fade at cut point to avoid click (2ms)
    fade_samples = int(0.002 * sr)
    if len(segment_a) > fade_samples:
        fade_out = np.linspace(1, 0, fade_samples)
        segment_a[-fade_samples:] *= fade_out

    if len(segment_b) > fade_samples:
        fade_in = np.linspace(0, 1, fade_samples)
        segment_b[:fade_samples] *= fade_in

    # Concatenate
    result = np.concatenate([segment_a, segment_b])

    return result


def create_cut_with_effect(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    cut_point_a: float,
    entry_point_b: float,
    effect: Literal["none", "reverb_tail", "delay_tail"],
    effect_params: Optional[Dict] = None,
    bpm: float = 128.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a hard cut with optional effect tail.

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        cut_point_a: Cut time in track A (seconds)
        entry_point_b: Entry time in track B (seconds)
        effect: Type of effect ("none", "reverb_tail", "delay_tail")
        effect_params: Parameters for the effect
        bpm: Tempo (for delay sync)
        sr: Sample rate

    Returns:
        Transition audio with effect
    """
    if effect_params is None:
        effect_params = {}

    cut_sample_a = int(cut_point_a * sr)
    entry_sample_b = int(entry_point_b * sr)

    # Get segment A up to cut point
    segment_a = audio_a[:cut_sample_a].copy()

    if effect == "reverb_tail":
        # Apply reverb tail effect
        room_size = effect_params.get("room_size", 0.8)
        decay = effect_params.get("decay", 2.0)
        fade_duration = effect_params.get("fade_duration", 1.5)

        # Start reverb effect before the cut
        tail_start = max(0, cut_point_a - fade_duration)
        tail_start_sample = int(tail_start * sr)

        # Apply reverb tail
        segment_a_with_tail = create_reverb_tail(
            audio=segment_a,
            tail_start_sample=tail_start_sample,
            room_size=room_size,
            decay=decay,
            fade_out_duration=fade_duration,
            sr=sr
        )
        segment_a = segment_a_with_tail

    elif effect == "delay_tail":
        # Apply delay tail effect
        beat_fraction = effect_params.get("beat_fraction", 0.5)
        feedback = effect_params.get("feedback", 0.5)
        fade_duration = effect_params.get("fade_duration", 1.5)

        # Start delay effect before the cut
        tail_start = max(0, cut_point_a - fade_duration)
        tail_start_sample = int(tail_start * sr)

        # Apply delay tail
        segment_a_with_tail = create_delay_tail(
            audio=segment_a,
            tail_start_sample=tail_start_sample,
            bpm=bpm,
            beat_fraction=beat_fraction,
            feedback=feedback,
            fade_out_duration=fade_duration,
            sr=sr
        )
        segment_a = segment_a_with_tail

    # Get segment B from entry point
    segment_b = audio_b[entry_sample_b:].copy()

    # Calculate overlap if there's a tail
    if effect != "none":
        # The tail extends beyond the cut point
        # Track B should start during the tail
        tail_duration = effect_params.get("decay", effect_params.get("fade_duration", 1.5))
        tail_samples = int(tail_duration * sr * 0.5)  # Overlap for half the tail

        # Ensure segment_a is long enough
        if len(segment_a) > cut_sample_a:
            # There's a tail - create overlap
            overlap_samples = min(tail_samples, len(segment_a) - cut_sample_a, len(segment_b))

            if overlap_samples > 0:
                # Extract overlapping portions
                tail_portion = segment_a[cut_sample_a:cut_sample_a + overlap_samples]
                b_start_portion = segment_b[:overlap_samples]

                # Create crossfade in overlap
                fade_out = np.linspace(1, 0, overlap_samples)
                fade_in = np.linspace(0, 1, overlap_samples)

                mixed_overlap = tail_portion * fade_out + b_start_portion * fade_in

                # Build result
                result = np.concatenate([
                    segment_a[:cut_sample_a],
                    mixed_overlap,
                    segment_b[overlap_samples:]
                ])

                return result

    # No overlap - simple concatenation
    # Add tiny fade at boundary
    fade_samples = int(0.002 * sr)
    if len(segment_a) > fade_samples:
        fade_out = np.linspace(1, 0, fade_samples)
        segment_a[-fade_samples:] *= fade_out

    if len(segment_b) > fade_samples:
        fade_in = np.linspace(0, 1, fade_samples)
        segment_b[:fade_samples] *= fade_in

    return np.concatenate([segment_a, segment_b])


def create_dramatic_cut(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    cut_point_a: float,
    entry_point_b: float,
    buildup_duration: float = 4.0,
    silence_duration: float = 0.5,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a dramatic cut with buildup and brief silence.

    This creates maximum impact by:
    1. Building tension before the cut
    2. Brief moment of silence/reduction
    3. Track B drops in with full force

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        cut_point_a: Cut time in track A (seconds)
        entry_point_b: Entry time in track B (seconds)
        buildup_duration: Duration of energy buildup before cut
        silence_duration: Duration of silence/reduction
        sr: Sample rate

    Returns:
        Transition with dramatic effect
    """
    cut_sample_a = int(cut_point_a * sr)
    entry_sample_b = int(entry_point_b * sr)
    buildup_samples = int(buildup_duration * sr)
    silence_samples = int(silence_duration * sr)

    # Get segment A
    segment_a = audio_a[:cut_sample_a].copy()

    # Apply buildup effect (volume/filter rise) to end of A
    buildup_start = max(0, cut_sample_a - buildup_samples)
    buildup_length = cut_sample_a - buildup_start

    if buildup_length > 0:
        # Volume rise
        buildup_curve = np.linspace(0.8, 1.2, buildup_length)
        segment_a[buildup_start:cut_sample_a] *= buildup_curve

        # Quick fade at very end
        fade_samples = int(0.05 * sr)  # 50ms
        if fade_samples < buildup_length:
            fade_out = np.linspace(1, 0, fade_samples)
            segment_a[-fade_samples:] *= fade_out

    # Create silence gap
    silence = np.zeros(silence_samples, dtype=np.float32)

    # Get segment B with quick fade in
    segment_b = audio_b[entry_sample_b:].copy()
    fade_in_samples = int(0.005 * sr)  # 5ms
    if len(segment_b) > fade_in_samples:
        fade_in = np.linspace(0, 1, fade_in_samples)
        segment_b[:fade_in_samples] *= fade_in

    # Combine
    result = np.concatenate([segment_a, silence, segment_b])

    # Normalize to prevent clipping
    max_val = np.max(np.abs(result))
    if max_val > 1.0:
        result = result / max_val * 0.95

    return result


def calculate_cut_point(
    beats: list,
    target_time: float,
    snap_to: Literal["beat", "bar", "phrase"] = "bar",
    beats_per_bar: int = 4,
    bars_per_phrase: int = 8
) -> float:
    """
    Calculate the best cut point near a target time.

    Args:
        beats: List of beat timestamps
        target_time: Desired cut time
        snap_to: What to snap to ("beat", "bar", "phrase")
        beats_per_bar: Beats per bar (usually 4)
        bars_per_phrase: Bars per phrase (usually 8)

    Returns:
        Snapped cut time
    """
    if not beats:
        return target_time

    beats_array = np.array(beats)

    if snap_to == "beat":
        idx = np.argmin(np.abs(beats_array - target_time))
        return float(beats_array[idx])

    elif snap_to == "bar":
        bar_beats = beats_array[::beats_per_bar]
        idx = np.argmin(np.abs(bar_beats - target_time))
        return float(bar_beats[idx])

    else:  # phrase
        phrase_beats = beats_array[::beats_per_bar * bars_per_phrase]
        idx = np.argmin(np.abs(phrase_beats - target_time))
        return float(phrase_beats[idx])
