"""
Delay / Echo effects for DJ transitions.

Delay repeats the sound at regular intervals, creating echo effects.
Essential for:
- Echo out transitions (let track fade with delay tail)
- Rhythmic effects during transitions
- Creating space and depth
"""

import numpy as np
from typing import Optional


def apply_delay(
    audio: np.ndarray,
    delay_ms: float,
    feedback: float = 0.4,
    mix: float = 0.3,
    num_taps: int = 8,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a delay effect to audio.

    Args:
        audio: Input audio array
        delay_ms: Delay time in milliseconds
        feedback: Amount of signal fed back (0-1, typically 0.3-0.5)
        mix: Wet/dry ratio (0=dry, 1=wet, typically 0.3-0.5)
        num_taps: Maximum number of delay repetitions
        sr: Sample rate

    Returns:
        Audio with delay applied
    """
    delay_samples = int((delay_ms / 1000.0) * sr)

    if delay_samples <= 0 or delay_samples >= len(audio):
        return audio

    # Create output buffer
    output_length = len(audio) + delay_samples * num_taps
    output = np.zeros(output_length, dtype=audio.dtype)
    output[:len(audio)] = audio.copy()

    # Apply delay taps
    delayed = np.zeros(output_length, dtype=audio.dtype)

    for tap in range(1, num_taps + 1):
        level = feedback ** tap
        if level < 0.01:  # Stop if level is negligible
            break

        offset = delay_samples * tap
        if offset < output_length:
            end_idx = min(len(audio), output_length - offset)
            delayed[offset:offset + end_idx] += audio[:end_idx] * level

    # Mix dry and wet signals
    result = output * (1 - mix) + delayed * mix

    # Trim to reasonable length (original + some tail)
    tail_samples = int(2.0 * sr)  # 2 second tail max
    final_length = min(len(audio) + tail_samples, len(result))

    return result[:final_length]


def apply_delay_bpm_sync(
    audio: np.ndarray,
    bpm: float,
    beat_fraction: float = 0.5,
    feedback: float = 0.4,
    mix: float = 0.3,
    num_taps: int = 8,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a BPM-synchronized delay effect.

    Common beat fractions:
    - 0.25: 1/4 beat (fast, rhythmic)
    - 0.5: 1/2 beat (medium, groovy)
    - 1.0: 1 beat (standard echo)
    - 0.75: 3/4 beat (syncopated, interesting)
    - 1.5: dotted quarter (triplet feel)

    Args:
        audio: Input audio array
        bpm: Tempo in beats per minute
        beat_fraction: Delay time as fraction of a beat
        feedback: Amount of signal fed back (0-1)
        mix: Wet/dry ratio (0-1)
        num_taps: Maximum number of delay repetitions
        sr: Sample rate

    Returns:
        Audio with BPM-synced delay applied
    """
    # Calculate delay time in milliseconds
    beat_ms = 60000.0 / bpm  # Duration of one beat in ms
    delay_ms = beat_ms * beat_fraction

    return apply_delay(
        audio=audio,
        delay_ms=delay_ms,
        feedback=feedback,
        mix=mix,
        num_taps=num_taps,
        sr=sr
    )


def create_delay_tail(
    audio: np.ndarray,
    tail_start_sample: int,
    bpm: float,
    beat_fraction: float = 0.5,
    feedback: float = 0.5,
    fade_out_duration: float = 2.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a delay tail effect for echo out transitions.

    The audio fades to silence while the delay continues,
    creating a trailing echo effect.

    Args:
        audio: Input audio array
        tail_start_sample: Sample index where tail effect begins
        bpm: Tempo for synced delay
        beat_fraction: Delay time as beat fraction
        fade_out_duration: Duration of dry signal fade out in seconds
        sr: Sample rate

    Returns:
        Audio with delay tail applied
    """
    if tail_start_sample >= len(audio):
        tail_start_sample = len(audio) - int(sr * 0.5)  # Start 0.5s before end

    # Calculate delay in samples
    beat_samples = int((60.0 / bpm) * sr)
    delay_samples = int(beat_samples * beat_fraction)

    # Create output with extra room for tail
    tail_duration_samples = int(fade_out_duration * sr) + delay_samples * 8
    output_length = len(audio) + tail_duration_samples
    output = np.zeros(output_length, dtype=np.float32)

    # Copy audio before tail
    output[:tail_start_sample] = audio[:tail_start_sample]

    # Process tail section
    tail_section = audio[tail_start_sample:]
    fade_samples = int(fade_out_duration * sr)
    fade_samples = min(fade_samples, len(tail_section))

    # Create fade out envelope for dry signal
    if fade_samples > 0:
        fade_envelope = np.linspace(1.0, 0.0, fade_samples)
        tail_section[:fade_samples] = tail_section[:fade_samples] * fade_envelope
        tail_section[fade_samples:] = 0  # Complete silence after fade

    # Apply delay to tail section with high mix (more wet)
    delayed_tail = apply_delay_bpm_sync(
        audio=tail_section,
        bpm=bpm,
        beat_fraction=beat_fraction,
        feedback=feedback,
        mix=0.8,  # High wet mix for tail
        num_taps=12,  # More taps for longer tail
        sr=sr
    )

    # Place delayed tail in output
    end_idx = min(tail_start_sample + len(delayed_tail), output_length)
    output[tail_start_sample:end_idx] = delayed_tail[:end_idx - tail_start_sample]

    # Trim silence at end
    nonzero_indices = np.where(np.abs(output) > 0.001)[0]
    if len(nonzero_indices) > 0:
        last_nonzero = nonzero_indices[-1]
        # Add a small buffer after last sound
        output = output[:last_nonzero + int(0.1 * sr)]

    return output


def apply_ping_pong_delay(
    audio: np.ndarray,
    delay_ms: float,
    feedback: float = 0.4,
    mix: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a stereo ping-pong delay (alternating left/right).

    Note: This returns stereo output even if input is mono.

    Args:
        audio: Input audio array (mono or stereo)
        delay_ms: Delay time in milliseconds
        feedback: Amount of signal fed back (0-1)
        mix: Wet/dry ratio (0-1)
        sr: Sample rate

    Returns:
        Stereo audio with ping-pong delay
    """
    # Ensure mono for processing
    if len(audio.shape) > 1:
        mono = np.mean(audio, axis=1)
    else:
        mono = audio

    delay_samples = int((delay_ms / 1000.0) * sr)

    # Create stereo output
    output_length = len(mono) + delay_samples * 10
    left = np.zeros(output_length, dtype=np.float32)
    right = np.zeros(output_length, dtype=np.float32)

    # Dry signal in center
    left[:len(mono)] = mono * (1 - mix)
    right[:len(mono)] = mono * (1 - mix)

    # Ping-pong delays
    for tap in range(1, 11):
        level = feedback ** tap * mix
        if level < 0.01:
            break

        offset = delay_samples * tap
        if offset >= output_length:
            break

        end_idx = min(len(mono), output_length - offset)

        if tap % 2 == 1:  # Odd taps go right
            right[offset:offset + end_idx] += mono[:end_idx] * level
        else:  # Even taps go left
            left[offset:offset + end_idx] += mono[:end_idx] * level

    # Combine to stereo
    stereo = np.column_stack([left[:len(mono)], right[:len(mono)]])

    return stereo
