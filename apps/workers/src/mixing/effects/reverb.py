"""
Reverb effects for DJ transitions.

Reverb simulates the acoustic properties of a space.
Essential for:
- Echo out transitions (reverb tail)
- Creating atmosphere and depth
- Dramatic exits from tracks
"""

import numpy as np
from typing import Optional, Tuple


def _generate_impulse_response(
    room_size: float,
    decay: float,
    damping: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Generate a synthetic impulse response for reverb.

    Uses a simplified algorithmic approach combining:
    - Early reflections (discrete echoes)
    - Late reverb (exponential decay noise)

    Args:
        room_size: Size of the simulated room (0-1)
        decay: Reverb time in seconds (RT60)
        damping: High frequency damping (0-1)
        sr: Sample rate

    Returns:
        Impulse response array
    """
    # Calculate IR length based on decay
    ir_length = int(decay * sr)
    ir = np.zeros(ir_length, dtype=np.float32)

    # Early reflections (first 50-100ms)
    early_length = int(0.1 * sr)
    num_early_reflections = int(5 + room_size * 10)

    for i in range(num_early_reflections):
        # Position reflections with increasing spacing
        pos = int((i + 1) * early_length / (num_early_reflections + 1))
        pos = min(pos, ir_length - 1)

        # Amplitude decreases with each reflection
        amplitude = (0.7 ** (i + 1)) * (0.5 + room_size * 0.5)
        ir[pos] = amplitude

    # Late reverb (exponential decay with noise)
    late_start = early_length
    late_length = ir_length - late_start

    if late_length > 0:
        # Generate noise
        noise = np.random.randn(late_length).astype(np.float32)

        # Exponential decay envelope
        t = np.arange(late_length) / sr
        decay_envelope = np.exp(-3.0 * t / decay)

        # Apply damping (low-pass effect on decay)
        if damping > 0:
            # Simple damping: reduce high frequencies over time
            damping_factor = 1.0 - damping * (t / decay)
            damping_factor = np.clip(damping_factor, 0.1, 1.0)
            decay_envelope *= damping_factor

        # Apply envelope to noise
        late_reverb = noise * decay_envelope * room_size * 0.3

        ir[late_start:] += late_reverb

    # Normalize IR
    max_val = np.max(np.abs(ir))
    if max_val > 0:
        ir = ir / max_val

    return ir


def apply_reverb(
    audio: np.ndarray,
    room_size: float = 0.7,
    decay: float = 2.0,
    mix: float = 0.3,
    damping: float = 0.5,
    pre_delay_ms: float = 0.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply reverb effect to audio.

    Args:
        audio: Input audio array
        room_size: Size of simulated room (0-1, larger = more spacious)
        decay: Reverb time in seconds (RT60)
        mix: Wet/dry ratio (0=dry, 1=wet)
        damping: High frequency damping (0-1, higher = darker reverb)
        pre_delay_ms: Delay before reverb starts (creates sense of space)
        sr: Sample rate

    Returns:
        Audio with reverb applied
    """
    # Generate impulse response
    ir = _generate_impulse_response(room_size, decay, damping, sr)

    # Apply pre-delay
    if pre_delay_ms > 0:
        pre_delay_samples = int((pre_delay_ms / 1000.0) * sr)
        ir = np.concatenate([np.zeros(pre_delay_samples), ir])

    # Convolve audio with IR
    # Use FFT convolution for efficiency
    wet = _fft_convolve(audio, ir)

    # Trim wet signal to match original length + some tail
    tail_samples = int(decay * sr * 0.5)  # Keep some reverb tail
    output_length = len(audio) + tail_samples
    wet = wet[:output_length]

    # Create output array
    output = np.zeros(output_length, dtype=np.float32)

    # Normalize Wet signal to unity gain relative to input
    # Convolution drastically changes amplitude depending on IR energy
    # We want wet signal peak roughly equal to input peak
    wet_max = np.max(np.abs(wet))
    input_max = np.max(np.abs(audio))
    
    if wet_max > 0:
        if input_max > 0:
            target_peak = input_max
        else:
            target_peak = 1.0
        
        # Scale wet signal to match input level (approx)
        wet = wet * (target_peak / wet_max)

    # Mix dry and wet
    output[:len(audio)] = audio * (1 - mix)
    output[:len(wet)] += wet * mix
    
    return output


def _fft_convolve(signal: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """
    Perform FFT-based convolution.

    More efficient than direct convolution for longer kernels.
    """
    # Calculate output length
    output_length = len(signal) + len(kernel) - 1

    # Find efficient FFT size (power of 2)
    fft_size = 1
    while fft_size < output_length:
        fft_size *= 2

    # FFT of both signals
    signal_fft = np.fft.rfft(signal, fft_size)
    kernel_fft = np.fft.rfft(kernel, fft_size)

    # Multiply in frequency domain
    result_fft = signal_fft * kernel_fft

    # Inverse FFT
    result = np.fft.irfft(result_fft, fft_size)

    return result[:output_length].astype(np.float32)


def apply_convolution_reverb(
    audio: np.ndarray,
    impulse_response: np.ndarray,
    mix: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply convolution reverb using a real impulse response.

    This provides more realistic reverb than algorithmic methods
    when using quality IR samples.

    Args:
        audio: Input audio array
        impulse_response: Impulse response array (from recorded space)
        mix: Wet/dry ratio (0-1)
        sr: Sample rate

    Returns:
        Audio with convolution reverb applied
    """
    # Normalize IR
    ir_max = np.max(np.abs(impulse_response))
    if ir_max > 0:
        ir_normalized = impulse_response / ir_max
    else:
        ir_normalized = impulse_response

    # Convolve
    wet = _fft_convolve(audio, ir_normalized)

    # Calculate output length (keep reverb tail)
    output_length = len(wet)

    # Create output
    output = np.zeros(output_length, dtype=np.float32)
    output[:len(audio)] = audio * (1 - mix)
    output[:len(wet)] += wet * mix

    return output


def create_reverb_tail(
    audio: np.ndarray,
    tail_start_sample: int,
    room_size: float = 0.8,
    decay: float = 3.0,
    fade_out_duration: float = 1.5,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a reverb tail effect for echo out transitions.

    The dry signal fades out while reverb continues,
    creating a spacious trailing effect.

    Args:
        audio: Input audio array
        tail_start_sample: Sample index where tail effect begins
        room_size: Reverb room size (0-1)
        decay: Reverb decay time in seconds
        fade_out_duration: Duration of dry signal fade out
        sr: Sample rate

    Returns:
        Audio with reverb tail
    """
    if tail_start_sample >= len(audio):
        tail_start_sample = len(audio) - int(sr * 0.5)

    # Create output with room for reverb tail
    reverb_tail_samples = int(decay * sr)
    output_length = len(audio) + reverb_tail_samples
    output = np.zeros(output_length, dtype=np.float32)

    # Copy audio before tail
    output[:tail_start_sample] = audio[:tail_start_sample]

    # Process tail section
    tail_section = audio[tail_start_sample:].copy()
    fade_samples = int(fade_out_duration * sr)
    fade_samples = min(fade_samples, len(tail_section))

    # Create fade out envelope
    if fade_samples > 0:
        # Equal power fade for smoother transition
        fade_curve = np.cos(np.linspace(0, np.pi / 2, fade_samples)) ** 2
        tail_section[:fade_samples] = tail_section[:fade_samples] * fade_curve
        tail_section[fade_samples:] = 0

    # Apply heavy reverb to tail section
    reverbed_tail = apply_reverb(
        audio=tail_section,
        room_size=room_size,
        decay=decay,
        mix=0.85,  # Very wet for tail
        damping=0.3,  # Less damping for brighter tail
        sr=sr
    )

    # Place reverbed tail in output
    end_idx = min(tail_start_sample + len(reverbed_tail), output_length)
    output[tail_start_sample:end_idx] = reverbed_tail[:end_idx - tail_start_sample]

    # Trim silence at end
    threshold = 0.001
    nonzero_indices = np.where(np.abs(output) > threshold)[0]
    if len(nonzero_indices) > 0:
        last_nonzero = nonzero_indices[-1]
        output = output[:last_nonzero + int(0.1 * sr)]

    return output


def apply_shimmer_reverb(
    audio: np.ndarray,
    room_size: float = 0.8,
    decay: float = 3.0,
    shimmer_amount: float = 0.3,
    mix: float = 0.3,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply shimmer reverb (reverb with pitch-shifted feedback).

    Creates an ethereal, ambient effect popular in ambient
    and post-rock music.

    Args:
        audio: Input audio array
        room_size: Reverb room size (0-1)
        decay: Reverb decay time
        shimmer_amount: Amount of octave-up shimmer (0-1)
        mix: Wet/dry ratio
        sr: Sample rate

    Returns:
        Audio with shimmer reverb
    """
    # First, apply normal reverb
    reverbed = apply_reverb(
        audio=audio,
        room_size=room_size,
        decay=decay,
        mix=1.0,  # Full wet for processing
        damping=0.2,
        sr=sr
    )

    # Simple pitch shift up one octave (double playback rate)
    # This is a basic implementation - could use pyrubberband for better quality
    if shimmer_amount > 0:
        # Resample to pitch shift up
        indices = np.arange(0, len(reverbed), 2)
        indices = indices[indices < len(reverbed)]
        pitched_up = reverbed[indices.astype(int)]

        # Stretch back to original length
        if len(pitched_up) > 0:
            x_old = np.linspace(0, 1, len(pitched_up))
            x_new = np.linspace(0, 1, len(reverbed))
            pitched_up_stretched = np.interp(x_new, x_old, pitched_up)

            # Mix shimmer with reverb
            reverbed = reverbed * (1 - shimmer_amount) + pitched_up_stretched * shimmer_amount

    # Final mix with dry signal
    output_length = max(len(audio), len(reverbed))
    output = np.zeros(output_length, dtype=np.float32)
    output[:len(audio)] = audio * (1 - mix)
    output[:len(reverbed)] += reverbed * mix

    return output
