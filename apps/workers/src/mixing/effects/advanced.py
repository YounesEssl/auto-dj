"""
Advanced audio effects for creative DJ transitions.

These effects are used for more creative mixing:
- Flanger: Jet/swoosh sound
- Phaser: Sweeping, psychedelic effect
- Beat Repeat: Stutter/glitch effects
- Gater: Rhythmic chopping
- Bitcrusher: Lo-fi degradation
- Spiral: Infinite rising/falling effect
"""

import numpy as np
from typing import List, Optional, Literal


def apply_flanger(
    audio: np.ndarray,
    rate: float = 0.5,
    depth: float = 0.7,
    mix: float = 0.5,
    feedback: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a flanger effect.

    Flanger creates a sweeping, jet-like sound by mixing
    the signal with a delayed copy where the delay time
    oscillates.

    Args:
        audio: Input audio array
        rate: LFO rate in Hz (speed of sweep, 0.1-5 Hz)
        depth: Modulation depth (0-1)
        mix: Wet/dry ratio (0-1)
        feedback: Amount of output fed back (0-0.9)
        sr: Sample rate

    Returns:
        Audio with flanger effect
    """
    num_samples = len(audio)

    # Flanger parameters
    min_delay_samples = int(0.001 * sr)  # 1ms
    max_delay_samples = int(0.010 * sr)  # 10ms
    delay_range = max_delay_samples - min_delay_samples

    # Generate LFO (sine wave)
    t = np.arange(num_samples) / sr
    lfo = (np.sin(2 * np.pi * rate * t) + 1) / 2  # 0-1 range

    # Calculate delay times
    delay_samples = min_delay_samples + (lfo * delay_range * depth).astype(int)

    # Create output
    output = np.zeros(num_samples, dtype=np.float32)
    feedback_buffer = np.zeros(num_samples, dtype=np.float32)

    for i in range(num_samples):
        delay = delay_samples[i]

        if i >= delay:
            delayed_sample = audio[i - delay] + feedback_buffer[i - delay] * feedback
            output[i] = audio[i] * (1 - mix) + delayed_sample * mix
            feedback_buffer[i] = delayed_sample
        else:
            output[i] = audio[i]

    return output


def apply_phaser(
    audio: np.ndarray,
    rate: float = 0.3,
    stages: int = 4,
    depth: float = 0.7,
    mix: float = 0.5,
    feedback: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a phaser effect.

    Phaser creates a sweeping, psychedelic sound by passing
    the signal through multiple all-pass filters whose
    frequencies are modulated.

    Args:
        audio: Input audio array
        rate: LFO rate in Hz (0.1-5)
        stages: Number of all-pass stages (2-12, even numbers)
        depth: Modulation depth (0-1)
        mix: Wet/dry ratio (0-1)
        feedback: Amount of output fed back (0-0.9)
        sr: Sample rate

    Returns:
        Audio with phaser effect
    """
    num_samples = len(audio)
    stages = max(2, min(stages, 12))
    if stages % 2 != 0:
        stages += 1

    # LFO for modulating filter frequencies
    t = np.arange(num_samples) / sr
    lfo = (np.sin(2 * np.pi * rate * t) + 1) / 2 * depth

    # Frequency range for all-pass filters (typically 200Hz - 2000Hz)
    min_freq = 200
    max_freq = 2000

    # Initialize all-pass filter states
    ap_states = [0.0] * stages

    output = np.zeros(num_samples, dtype=np.float32)
    feedback_signal = 0.0

    for i in range(num_samples):
        # Current modulation
        mod = lfo[i]
        freq = min_freq + mod * (max_freq - min_freq)

        # All-pass filter coefficient
        # Simplified: coefficient based on frequency
        coefficient = (1 - np.tan(np.pi * freq / sr)) / (1 + np.tan(np.pi * freq / sr))

        # Input with feedback
        input_sample = audio[i] + feedback_signal * feedback

        # Process through all-pass stages
        processed = input_sample
        for stage in range(stages):
            # Simple all-pass: y[n] = -a*x[n] + x[n-1] + a*y[n-1]
            new_state = -coefficient * processed + ap_states[stage]
            processed = coefficient * new_state + processed
            ap_states[stage] = new_state

        # Store feedback
        feedback_signal = processed

        # Mix dry and wet
        output[i] = audio[i] * (1 - mix) + processed * mix

    return output


def apply_beat_repeat(
    audio: np.ndarray,
    bpm: float,
    repeat_length_beats: float = 0.25,
    repeats: int = 4,
    start_time: Optional[float] = None,
    decay: float = 0.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a beat repeat (stutter) effect.

    Captures a segment and repeats it multiple times,
    creating a stutter/glitch effect. Great for buildups.

    Args:
        audio: Input audio array
        bpm: Track tempo
        repeat_length_beats: Length of segment to repeat (0.125-1.0)
        repeats: Number of repetitions (2-16)
        start_time: When to start the effect (seconds, None = entire audio)
        decay: Volume decay per repeat (0-0.5)
        sr: Sample rate

    Returns:
        Audio with beat repeat effect
    """
    # Calculate segment length in samples
    beat_samples = int((60.0 / bpm) * sr)
    segment_samples = int(beat_samples * repeat_length_beats)

    if segment_samples < 100:
        return audio

    # Create output
    output = audio.copy()

    # Determine start position
    if start_time is not None:
        start_sample = int(start_time * sr)
    else:
        start_sample = 0

    # Find segment to repeat
    if start_sample + segment_samples > len(audio):
        return audio

    segment = audio[start_sample:start_sample + segment_samples].copy()

    # Create repeated section
    total_repeat_samples = segment_samples * repeats
    repeated = np.zeros(total_repeat_samples, dtype=np.float32)

    for r in range(repeats):
        level = 1.0 - (decay * r)
        level = max(0.1, level)
        pos = r * segment_samples
        repeated[pos:pos + segment_samples] = segment * level

    # Replace original section with repeated
    end_pos = min(start_sample + total_repeat_samples, len(output))
    output[start_sample:end_pos] = repeated[:end_pos - start_sample]

    return output


def apply_gater(
    audio: np.ndarray,
    bpm: float,
    pattern: List[int] = [1, 0, 1, 0, 1, 1, 0, 1],
    smoothing_ms: float = 5.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a rhythmic gate effect.

    Gates the audio on/off in a rhythmic pattern,
    creating a choppy, staccato effect.

    Args:
        audio: Input audio array
        bpm: Track tempo
        pattern: Gate pattern (1=open, 0=closed), one per 1/8 note
        smoothing_ms: Gate attack/release time in ms (to avoid clicks)
        sr: Sample rate

    Returns:
        Gated audio
    """
    if not pattern:
        pattern = [1, 0, 1, 0, 1, 1, 0, 1]

    # Calculate step duration (pattern is per 1/8 note by default)
    beat_samples = int((60.0 / bpm) * sr)
    step_samples = beat_samples // 2  # 1/8 note

    # Create gate envelope
    num_samples = len(audio)
    envelope = np.zeros(num_samples, dtype=np.float32)

    pattern_length = len(pattern)
    for i in range(num_samples):
        pattern_idx = (i // step_samples) % pattern_length
        envelope[i] = pattern[pattern_idx]

    # Apply smoothing to avoid clicks
    smoothing_samples = int((smoothing_ms / 1000.0) * sr)
    if smoothing_samples > 1:
        # Simple smoothing with running average
        kernel = np.ones(smoothing_samples) / smoothing_samples
        envelope = np.convolve(envelope, kernel, mode='same')

    # Apply envelope
    return audio * envelope


def apply_bitcrusher(
    audio: np.ndarray,
    bit_depth: int = 8,
    sample_rate_reduction: int = 4
) -> np.ndarray:
    """
    Apply a bitcrusher effect.

    Reduces bit depth and sample rate for a lo-fi,
    digital degradation effect.

    Args:
        audio: Input audio array
        bit_depth: Target bit depth (1-16, lower = more crushed)
        sample_rate_reduction: Sample rate divisor (1-16)

    Returns:
        Bitcrushed audio
    """
    # Clamp parameters
    bit_depth = max(1, min(bit_depth, 16))
    sample_rate_reduction = max(1, min(sample_rate_reduction, 16))

    output = audio.copy()

    # Reduce bit depth
    # Quantize to fewer levels
    levels = 2 ** bit_depth
    output = np.round(output * (levels / 2)) / (levels / 2)

    # Reduce sample rate (sample and hold)
    if sample_rate_reduction > 1:
        for i in range(0, len(output), sample_rate_reduction):
            end = min(i + sample_rate_reduction, len(output))
            output[i:end] = output[i]  # Hold the value

    return output


def apply_spiral(
    audio: np.ndarray,
    pitch_shift_semitones: float = 12.0,
    reverb_size: float = 0.95,
    feedback: float = 0.8,
    duration: float = 5.0,
    direction: Literal["up", "down"] = "up",
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a spiral effect (Shepard tone-like infinite rise/fall).

    Creates an ethereal effect where the sound appears to
    continuously rise or fall in pitch. Great for transitions
    and atmospheric effects.

    Args:
        audio: Input audio array
        pitch_shift_semitones: Total pitch shift range
        reverb_size: Reverb amount (0-1)
        feedback: How much of the effect feeds back
        duration: Effect duration in seconds
        direction: "up" for rising, "down" for falling
        sr: Sample rate

    Returns:
        Audio with spiral effect
    """
    num_samples = len(audio)
    effect_samples = int(duration * sr)
    effect_samples = min(effect_samples, num_samples)

    # Create output with extra room for tail
    output = np.zeros(num_samples + int(2 * sr), dtype=np.float32)
    output[:num_samples] = audio

    # Simple pitch shift simulation (basic, would use pyrubberband for quality)
    # This creates a rising/falling effect by modulating playback speed
    shift_factor = 2 ** (pitch_shift_semitones / 12.0)

    if direction == "down":
        shift_factor = 1.0 / shift_factor

    # Create modulated version
    t = np.linspace(0, 1, effect_samples)
    speed_curve = 1.0 + (shift_factor - 1.0) * t

    # Resample based on speed curve (simplified)
    # This is a basic implementation
    modulated = np.zeros(effect_samples, dtype=np.float32)
    read_pos = 0.0

    for i in range(effect_samples):
        if int(read_pos) < len(audio):
            modulated[i] = audio[int(read_pos)]
            read_pos += speed_curve[i]
        else:
            break

    # Apply reverb-like decay
    decay = np.exp(-3.0 * t / duration) * reverb_size

    modulated = modulated * decay

    # Mix with original using feedback
    for i in range(effect_samples):
        output[i] = output[i] * (1 - feedback) + modulated[i] * feedback

    # Trim silence
    threshold = 0.001
    nonzero = np.where(np.abs(output) > threshold)[0]
    if len(nonzero) > 0:
        output = output[:nonzero[-1] + int(0.1 * sr)]

    return output


def apply_tape_stop(
    audio: np.ndarray,
    duration: float = 1.0,
    start_time: Optional[float] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a tape stop effect.

    Simulates a turntable/tape machine stopping,
    with the audio slowing down and pitch dropping.

    Args:
        audio: Input audio array
        duration: How long the stop takes in seconds
        start_time: When to start the effect (None = end of audio)
        sr: Sample rate

    Returns:
        Audio with tape stop effect
    """
    num_samples = len(audio)
    stop_samples = int(duration * sr)

    # Determine start position
    if start_time is not None:
        start_sample = int(start_time * sr)
    else:
        start_sample = max(0, num_samples - stop_samples)

    output = audio[:start_sample].copy() if start_sample > 0 else np.array([], dtype=np.float32)

    # Create the tape stop section
    if start_sample < num_samples:
        stop_section = audio[start_sample:].copy()
        stop_length = len(stop_section)

        # Speed curve: starts at 1.0, ends at 0
        # Use quadratic for realistic deceleration
        t = np.linspace(0, 1, stop_length)
        speed = 1.0 - t ** 2

        # Resample based on speed
        stretched = []
        read_pos = 0.0

        while read_pos < stop_length and speed[int(read_pos)] > 0.01:
            idx = int(read_pos)
            if idx < stop_length:
                stretched.append(stop_section[idx])
                # Slower speed = smaller step = stretched audio
                read_pos += max(0.01, speed[idx])
            else:
                break

        if stretched:
            output = np.concatenate([output, np.array(stretched, dtype=np.float32)])

    return output


def apply_vinyl_brake(
    audio: np.ndarray,
    duration: float = 0.5,
    start_time: Optional[float] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a vinyl brake effect (faster version of tape stop).

    Like a DJ stopping a turntable with their hand.

    Args:
        audio: Input audio array
        duration: Brake duration in seconds (typically 0.3-1.0)
        start_time: When to start the effect
        sr: Sample rate

    Returns:
        Audio with vinyl brake effect
    """
    return apply_tape_stop(audio, duration, start_time, sr)
