"""
Filter Transition - Creative filter-based mixing.

Filters sculpt the sound musically:
- HPF (High Pass Filter): Removes bass → airy, distant sound
- LPF (Low Pass Filter): Removes highs → muffled, underwater sound

TECHNIQUES:
1. Filter sweep OUT on A:
   - HPF from 20Hz → 2000Hz+ on A
   - Sound "moves away", becomes airy
   - Perfect for exiting a track

2. Filter sweep IN on B:
   - LPF from 200Hz → 20000Hz on B
   - Sound "arrives from afar", reveals progressively
   - Perfect for introducing a track with tension

3. Combined:
   - HPF sweep up on A + LPF sweep up on B
   - Creative and dynamic transition
"""

import numpy as np
from typing import Dict, Optional, Literal
from ..effects.filters import apply_filter, create_filter_sweep, create_combined_filter_sweep
import structlog

logger = structlog.get_logger()


def create_filter_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    transition_duration: float,
    filter_a: Dict,
    filter_b: Dict,
    crossfade: bool = True,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a filter sweep transition.

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        transition_duration: Duration in seconds
        filter_a: Config for track A {"type": "hpf", "start": 20, "end": 2000}
        filter_b: Config for track B {"type": "lpf", "start": 200, "end": 20000}
        crossfade: Whether to also apply volume crossfade
        sr: Sample rate

    Returns:
        Transition audio with filter sweeps
    """
    trans_samples = int(transition_duration * sr)
    trans_samples = min(trans_samples, len(audio_a), len(audio_b))

    # Extract transition segments
    segment_a = audio_a[-trans_samples:].copy()
    segment_b = audio_b[:trans_samples].copy()

    # Apply filter sweep to A
    if filter_a.get("type"):
        segment_a = create_filter_sweep(
            segment_a,
            filter_type=filter_a["type"],
            start_freq=filter_a.get("start", 20),
            end_freq=filter_a.get("end", 2000),
            curve=filter_a.get("curve", "exponential"),
            sr=sr
        )

    # Apply filter sweep to B
    if filter_b.get("type"):
        segment_b = create_filter_sweep(
            segment_b,
            filter_type=filter_b["type"],
            start_freq=filter_b.get("start", 200),
            end_freq=filter_b.get("end", 20000),
            curve=filter_b.get("curve", "exponential"),
            sr=sr
        )

    # Apply volume crossfade if requested
    if crossfade:
        # Equal power crossfade
        t = np.linspace(0, np.pi / 2, trans_samples)
        fade_out = np.cos(t)
        fade_in = np.sin(t)

        segment_a = segment_a * fade_out
        segment_b = segment_b * fade_in

    # Mix together
    output = segment_a + segment_b

    # Prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val * 0.95

    return output


def create_hpf_exit(
    audio: np.ndarray,
    start_time: float,
    duration: float,
    start_freq: float = 20,
    end_freq: float = 2000,
    volume_fade: bool = True,
    sr: int = 44100
) -> np.ndarray:
    """
    Create an HPF sweep exit effect.

    The track "fades into the distance" as the bass is removed.

    Args:
        audio: Track audio
        start_time: When to start the sweep
        duration: Duration of sweep
        start_freq: Starting HPF frequency
        end_freq: Ending HPF frequency
        volume_fade: Whether to also fade volume
        sr: Sample rate

    Returns:
        Audio with HPF exit applied
    """
    start_sample = int(start_time * sr)
    duration_samples = int(duration * sr)

    output = audio.copy()

    # Get the section to filter
    end_sample = min(start_sample + duration_samples, len(audio))
    section = audio[start_sample:end_sample].copy()

    # Apply HPF sweep
    filtered_section = create_filter_sweep(
        section,
        filter_type="hpf",
        start_freq=start_freq,
        end_freq=end_freq,
        curve="exponential",
        sr=sr
    )

    # Apply volume fade if requested
    if volume_fade:
        fade_out = np.linspace(1, 0.2, len(filtered_section))
        filtered_section = filtered_section * fade_out

    # Replace section in output
    output[start_sample:end_sample] = filtered_section

    # Fade to silence after the sweep
    if end_sample < len(output):
        remaining = len(output) - end_sample
        fade_samples = min(remaining, int(0.5 * sr))
        fade_out = np.linspace(0.2, 0, fade_samples)
        output[end_sample:end_sample + fade_samples] *= fade_out
        output[end_sample + fade_samples:] = 0

    return output


def create_lpf_entry(
    audio: np.ndarray,
    entry_duration: float,
    start_freq: float = 200,
    end_freq: float = 20000,
    volume_fade: bool = True,
    sr: int = 44100
) -> np.ndarray:
    """
    Create an LPF sweep entry effect.

    The track "emerges from underwater" as highs are revealed.

    Args:
        audio: Track audio
        entry_duration: Duration of sweep
        start_freq: Starting LPF frequency
        end_freq: Ending LPF frequency
        volume_fade: Whether to also fade volume in
        sr: Sample rate

    Returns:
        Audio with LPF entry applied
    """
    duration_samples = int(entry_duration * sr)
    duration_samples = min(duration_samples, len(audio))

    output = audio.copy()

    # Get the section to filter
    section = audio[:duration_samples].copy()

    # Apply LPF sweep
    filtered_section = create_filter_sweep(
        section,
        filter_type="lpf",
        start_freq=start_freq,
        end_freq=end_freq,
        curve="exponential",
        sr=sr
    )

    # Apply volume fade if requested
    if volume_fade:
        fade_in = np.linspace(0.2, 1, len(filtered_section))
        filtered_section = filtered_section * fade_in

    # Replace section in output
    output[:duration_samples] = filtered_section

    return output


def create_filter_swap_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    transition_duration: float,
    swap_point: float = 0.5,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a filter swap transition.

    Instead of gradual sweeps, this swaps the filter states:
    - A starts normal, B starts filtered
    - At swap point, A becomes filtered, B becomes normal

    Args:
        audio_a: Outgoing track
        audio_b: Incoming track
        transition_duration: Total duration
        swap_point: Relative position of swap (0-1)
        sr: Sample rate

    Returns:
        Transition with filter swap
    """
    trans_samples = int(transition_duration * sr)
    trans_samples = min(trans_samples, len(audio_a), len(audio_b))
    swap_sample = int(trans_samples * swap_point)

    # Extract segments
    segment_a = audio_a[-trans_samples:].copy()
    segment_b = audio_b[:trans_samples].copy()

    # Before swap: A normal, B filtered
    if swap_sample > 0:
        segment_b_pre = apply_filter(segment_b[:swap_sample], "lpf", 500, sr=sr)
        segment_b[:swap_sample] = segment_b_pre

    # After swap: A filtered, B normal
    if swap_sample < trans_samples:
        segment_a_post = apply_filter(segment_a[swap_sample:], "hpf", 1000, sr=sr)
        segment_a[swap_sample:] = segment_a_post

    # Apply volume crossfade
    t = np.linspace(0, np.pi / 2, trans_samples)
    fade_out = np.cos(t)
    fade_in = np.sin(t)

    segment_a = segment_a * fade_out
    segment_b = segment_b * fade_in

    # Mix
    output = segment_a + segment_b

    # Normalize
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val * 0.95

    return output


def get_filter_transition_presets() -> Dict:
    """
    Get preset filter configurations for common transitions.
    """
    return {
        "standard_exit": {
            "a": {"type": "hpf", "start": 20, "end": 2000, "curve": "exponential"},
            "b": {"type": "lpf", "start": 500, "end": 20000, "curve": "exponential"},
            "crossfade": True
        },
        "dramatic_exit": {
            "a": {"type": "hpf", "start": 20, "end": 4000, "curve": "exponential"},
            "b": {"type": None},
            "crossfade": True
        },
        "underwater_reveal": {
            "a": {"type": None},
            "b": {"type": "lpf", "start": 200, "end": 20000, "curve": "linear"},
            "crossfade": True
        },
        "high_energy_swap": {
            "a": {"type": "hpf", "start": 20, "end": 1500, "curve": "linear"},
            "b": {"type": "lpf", "start": 1000, "end": 20000, "curve": "linear"},
            "crossfade": False
        }
    }
