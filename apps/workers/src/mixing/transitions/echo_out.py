"""
Echo Out Transition - Exit with delay/reverb tail.

Elegant technique for ending a track:
1. Activate effect (delay or reverb) on A
2. Progressively cut the DRY signal
3. Let the WET (effect) signal fade naturally
4. During this time, B can enter

DELAY PARAMETERS:
- Time: Synced to BPM (1/4, 1/2, 1 beat)
- Feedback: 30-50% for natural decay
- Mix: Progressively increase from 0% to 100% wet

REVERB PARAMETERS:
- Size: Large for dramatic effect
- Decay: 2-4 seconds
- Mix: Progressively increase
"""

import numpy as np
from typing import Dict, Optional, Literal
from ..effects.delay import apply_delay_bpm_sync, create_delay_tail
from ..effects.reverb import apply_reverb, create_reverb_tail
import structlog

logger = structlog.get_logger()


def create_echo_out_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    echo_start: float,
    echo_duration: float,
    effect_type: Literal["delay", "reverb"] = "delay",
    effect_params: Optional[Dict] = None,
    track_b_entry: Optional[float] = None,
    bpm: float = 128.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create an echo out transition.

    Args:
        audio_a: Outgoing track
        audio_b: Incoming track
        echo_start: When to start the echo effect (seconds in A)
        echo_duration: Duration of the echo tail
        effect_type: "delay" or "reverb"
        effect_params: Parameters for the effect
        track_b_entry: When B enters (seconds into the transition, None = during tail)
        bpm: Tempo for delay sync
        sr: Sample rate

    Returns:
        Transition audio
    """
    if effect_params is None:
        effect_params = {}

    echo_start_sample = int(echo_start * sr)
    echo_duration_samples = int(echo_duration * sr)

    # Create segment A with echo tail
    segment_a = audio_a[:echo_start_sample + echo_duration_samples].copy()

    if effect_type == "delay":
        segment_a = create_delay_tail(
            audio=segment_a,
            tail_start_sample=echo_start_sample,
            bpm=bpm,
            beat_fraction=effect_params.get("beat_fraction", 0.5),
            feedback=effect_params.get("feedback", 0.5),
            fade_out_duration=effect_params.get("fade_duration", echo_duration * 0.5),
            sr=sr
        )
    else:  # reverb
        segment_a = create_reverb_tail(
            audio=segment_a,
            tail_start_sample=echo_start_sample,
            room_size=effect_params.get("room_size", 0.8),
            decay=effect_params.get("decay", echo_duration * 0.8),
            fade_out_duration=effect_params.get("fade_duration", echo_duration * 0.5),
            sr=sr
        )

    # Determine when B enters
    if track_b_entry is None:
        # Default: B enters halfway through the tail
        b_entry_time = echo_duration * 0.5
    else:
        b_entry_time = track_b_entry

    b_entry_sample = int(b_entry_time * sr)

    # Calculate overlap region
    # Segment A tail continues from echo_start
    # Segment B starts at b_entry_time relative to echo_start
    a_tail_length = len(segment_a) - echo_start_sample
    overlap_start = echo_start_sample + b_entry_sample
    overlap_length = a_tail_length - b_entry_sample

    if overlap_length > 0 and overlap_length <= len(audio_b):
        # Create output with proper length
        output_length = echo_start_sample + b_entry_sample + len(audio_b)
        output = np.zeros(output_length, dtype=np.float32)

        # Place A (including tail)
        output[:len(segment_a)] = segment_a

        # Place B with overlap
        b_start_in_output = overlap_start
        output[b_start_in_output:b_start_in_output + len(audio_b)] += audio_b

        # Apply crossfade in overlap region
        if overlap_length > 0:
            # Fade A's tail during overlap
            fade_samples = min(overlap_length, int(1.0 * sr))
            fade_out = np.linspace(1, 0, fade_samples)
            output[overlap_start:overlap_start + fade_samples] *= 0.7  # Reduce overlap volume

    else:
        # No overlap - concatenate
        output = np.concatenate([segment_a, audio_b])

    # Normalize
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val * 0.95

    return output


def create_reverb_out_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    reverb_start: float,
    reverb_duration: float = 3.0,
    room_size: float = 0.85,
    track_b_overlap: float = 1.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a reverb out transition (shorthand for echo_out with reverb).

    Args:
        audio_a: Outgoing track
        audio_b: Incoming track
        reverb_start: When to start reverb effect
        reverb_duration: Total reverb tail duration
        room_size: Reverb size (0-1)
        track_b_overlap: How much B overlaps with reverb tail
        sr: Sample rate

    Returns:
        Transition audio
    """
    return create_echo_out_transition(
        audio_a=audio_a,
        audio_b=audio_b,
        echo_start=reverb_start,
        echo_duration=reverb_duration,
        effect_type="reverb",
        effect_params={
            "room_size": room_size,
            "decay": reverb_duration * 0.7,
            "fade_duration": reverb_duration * 0.4
        },
        track_b_entry=reverb_duration - track_b_overlap,
        sr=sr
    )


def create_delay_out_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    delay_start: float,
    delay_duration: float = 2.0,
    bpm: float = 128.0,
    beat_fraction: float = 0.5,
    feedback: float = 0.5,
    track_b_overlap: float = 0.5,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a delay out transition (shorthand for echo_out with delay).

    Args:
        audio_a: Outgoing track
        audio_b: Incoming track
        delay_start: When to start delay effect
        delay_duration: Total delay tail duration
        bpm: Tempo for sync
        beat_fraction: Delay time as beat fraction
        feedback: Delay feedback amount
        track_b_overlap: How much B overlaps with delay tail
        sr: Sample rate

    Returns:
        Transition audio
    """
    return create_echo_out_transition(
        audio_a=audio_a,
        audio_b=audio_b,
        echo_start=delay_start,
        echo_duration=delay_duration,
        effect_type="delay",
        effect_params={
            "beat_fraction": beat_fraction,
            "feedback": feedback,
            "fade_duration": delay_duration * 0.4
        },
        track_b_entry=delay_duration - track_b_overlap,
        bpm=bpm,
        sr=sr
    )


def create_wash_out(
    audio: np.ndarray,
    wash_start: float,
    wash_duration: float = 4.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a "wash out" effect combining reverb and delay.

    Creates a dreamy, ethereal fade out.

    Args:
        audio: Track to apply wash to
        wash_start: When to start the wash
        wash_duration: Duration of the wash
        sr: Sample rate

    Returns:
        Audio with wash effect
    """
    wash_start_sample = int(wash_start * sr)

    output = audio.copy()

    # Get section to wash
    if wash_start_sample < len(audio):
        section = audio[wash_start_sample:].copy()

        # Apply reverb
        reverbed = apply_reverb(
            section,
            room_size=0.9,
            decay=wash_duration,
            mix=0.7,
            damping=0.3,
            sr=sr
        )

        # Apply delay on top
        delayed = apply_delay_bpm_sync(
            reverbed,
            bpm=120,  # Approximate
            beat_fraction=0.75,
            feedback=0.6,
            mix=0.5,
            sr=sr
        )

        # Fade out the dry signal
        fade_samples = int(wash_duration * 0.5 * sr)
        fade_samples = min(fade_samples, len(section))
        if fade_samples > 0:
            fade_out = np.linspace(1, 0, fade_samples)
            section[:fade_samples] *= fade_out
            section[fade_samples:] = 0

        # Mix dry fade with wet effect
        mix_length = min(len(section), len(delayed))
        mixed = np.zeros(len(delayed), dtype=np.float32)
        mixed[:mix_length] = section[:mix_length] * 0.3 + delayed[:mix_length] * 0.7
        mixed[mix_length:] = delayed[mix_length:] * 0.7

        # Apply final envelope
        final_fade = np.linspace(1, 0, len(mixed))
        mixed *= final_fade

        # Place in output
        output_length = wash_start_sample + len(mixed)
        result = np.zeros(output_length, dtype=np.float32)
        result[:wash_start_sample] = audio[:wash_start_sample]
        result[wash_start_sample:] = mixed

        return result

    return output
