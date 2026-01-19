"""
Filter effects for DJ transitions.

Filters are essential for DJ mixing:
- HPF (High Pass Filter): Removes bass, creates airy/distant sound
- LPF (Low Pass Filter): Removes highs, creates muffled/underwater sound
- Filter sweeps: Gradual frequency changes for smooth transitions

Common uses:
- HPF sweep up on outgoing track (track "fades into distance")
- LPF sweep up on incoming track (track "reveals itself")
- Combined sweeps for creative transitions
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt
from typing import Literal, Optional


def apply_filter(
    audio: np.ndarray,
    filter_type: Literal["hpf", "lpf", "bandpass"],
    cutoff_freq: float,
    resonance: float = 0.707,
    order: int = 4,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a filter to audio.

    Args:
        audio: Input audio array
        filter_type: "hpf" (high-pass), "lpf" (low-pass), or "bandpass"
        cutoff_freq: Filter cutoff frequency in Hz
        resonance: Q factor / resonance (0.5-2.0, 0.707 = Butterworth)
        order: Filter order (higher = steeper rolloff)
        sr: Sample rate

    Returns:
        Filtered audio
    """
    nyquist = sr / 2

    # Clamp cutoff to valid range
    cutoff_freq = max(20, min(cutoff_freq, nyquist - 100))
    normalized_cutoff = cutoff_freq / nyquist

    try:
        if filter_type == "hpf":
            sos = butter(order, normalized_cutoff, btype='high', output='sos')
        elif filter_type == "lpf":
            sos = butter(order, normalized_cutoff, btype='low', output='sos')
        elif filter_type == "bandpass":
            # For bandpass, cutoff_freq is center, use resonance to set bandwidth
            low = cutoff_freq / (1 + resonance)
            high = cutoff_freq * (1 + resonance)
            low_norm = max(0.001, low / nyquist)
            high_norm = min(0.999, high / nyquist)
            sos = butter(order, [low_norm, high_norm], btype='band', output='sos')
        else:
            return audio

        # Apply filter (forward-backward for zero phase delay)
        filtered = sosfiltfilt(sos, audio)
        return filtered.astype(np.float32)

    except Exception:
        # Return original if filter fails
        return audio


def apply_hpf(
    audio: np.ndarray,
    cutoff_freq: float,
    order: int = 4,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a high-pass filter.

    HPF removes low frequencies below the cutoff.
    - 20 Hz: No effect (off)
    - 100-200 Hz: Light bass reduction
    - 500-1000 Hz: Strong bass cut, thin sound
    - 2000+ Hz: Extreme, very tinny/airy sound

    Args:
        audio: Input audio array
        cutoff_freq: Cutoff frequency in Hz
        order: Filter order
        sr: Sample rate

    Returns:
        High-pass filtered audio
    """
    return apply_filter(audio, "hpf", cutoff_freq, order=order, sr=sr)


def apply_lpf(
    audio: np.ndarray,
    cutoff_freq: float,
    order: int = 4,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a low-pass filter.

    LPF removes high frequencies above the cutoff.
    - 20000 Hz: No effect (off)
    - 5000-10000 Hz: Light high reduction
    - 1000-2000 Hz: Muffled, distant sound
    - 200-500 Hz: Very muffled, underwater sound

    Args:
        audio: Input audio array
        cutoff_freq: Cutoff frequency in Hz
        order: Filter order
        sr: Sample rate

    Returns:
        Low-pass filtered audio
    """
    return apply_filter(audio, "lpf", cutoff_freq, order=order, sr=sr)


def apply_bandpass(
    audio: np.ndarray,
    center_freq: float,
    bandwidth: float = 1.0,
    order: int = 2,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a bandpass filter.

    Bandpass allows only frequencies around the center to pass.
    Useful for isolating specific frequency ranges.

    Args:
        audio: Input audio array
        center_freq: Center frequency in Hz
        bandwidth: Width of the pass band (Q factor)
        order: Filter order
        sr: Sample rate

    Returns:
        Bandpass filtered audio
    """
    return apply_filter(audio, "bandpass", center_freq, resonance=bandwidth, order=order, sr=sr)


def create_filter_sweep(
    audio: np.ndarray,
    filter_type: Literal["hpf", "lpf"],
    start_freq: float,
    end_freq: float,
    duration: Optional[float] = None,
    curve: Literal["linear", "exponential"] = "exponential",
    order: int = 4,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a filter sweep (gradually changing cutoff frequency).

    Common DJ transitions:
    - HPF sweep up (20 -> 2000 Hz): Outgoing track "fades away"
    - LPF sweep up (200 -> 20000 Hz): Incoming track "reveals itself"
    - HPF sweep down (2000 -> 20 Hz): "Bass drop" effect
    - LPF sweep down (20000 -> 200 Hz): "Underwater" effect

    Args:
        audio: Input audio array
        filter_type: "hpf" or "lpf"
        start_freq: Starting cutoff frequency
        end_freq: Ending cutoff frequency
        duration: Sweep duration in seconds (None = full audio length)
        curve: "linear" or "exponential" (exponential sounds more natural)
        order: Filter order
        sr: Sample rate

    Returns:
        Audio with filter sweep applied
    """
    num_samples = len(audio)
    sweep_samples = num_samples if duration is None else int(duration * sr)
    sweep_samples = min(sweep_samples, num_samples)

    # Generate frequency curve
    if curve == "exponential":
        # Exponential feels more natural for frequency sweeps
        freqs = np.geomspace(start_freq, end_freq, sweep_samples)
    else:
        freqs = np.linspace(start_freq, end_freq, sweep_samples)

    # Extend to full audio length if needed
    if sweep_samples < num_samples:
        freqs = np.concatenate([
            freqs,
            np.full(num_samples - sweep_samples, end_freq)
        ])

    # Process in chunks for smooth automation
    chunk_size = int(sr * 0.05)  # 50ms chunks
    num_chunks = int(np.ceil(num_samples / chunk_size))

    output = np.zeros_like(audio)

    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, num_samples)

        # Get average frequency for this chunk
        chunk_freq = np.mean(freqs[start_idx:end_idx])

        # Apply filter to chunk
        chunk = audio[start_idx:end_idx]
        filtered_chunk = apply_filter(
            chunk,
            filter_type=filter_type,
            cutoff_freq=chunk_freq,
            order=order,
            sr=sr
        )

        # Apply short crossfade at chunk boundaries to avoid clicks
        if i > 0 and start_idx < num_samples:
            fade_len = min(64, len(filtered_chunk))
            fade_in = np.linspace(0, 1, fade_len)
            fade_out = np.linspace(1, 0, fade_len)

            filtered_chunk[:fade_len] *= fade_in
            output[start_idx:start_idx + fade_len] *= fade_out

        output[start_idx:end_idx] += filtered_chunk

    return output


def create_combined_filter_sweep(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    hpf_start_a: float = 20,
    hpf_end_a: float = 2000,
    lpf_start_b: float = 200,
    lpf_end_b: float = 20000,
    duration: Optional[float] = None,
    curve: Literal["linear", "exponential"] = "exponential",
    crossfade: bool = True,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a combined filter sweep transition.

    This applies:
    - HPF sweep up on track A (A "fades away")
    - LPF sweep up on track B (B "reveals itself")
    - Optional volume crossfade

    Args:
        audio_a: Outgoing track audio
        audio_b: Incoming track audio
        hpf_start_a: Starting HPF cutoff for track A
        hpf_end_a: Ending HPF cutoff for track A
        lpf_start_b: Starting LPF cutoff for track B
        lpf_end_b: Ending LPF cutoff for track B
        duration: Sweep duration in seconds
        curve: "linear" or "exponential"
        crossfade: Whether to also apply volume crossfade
        sr: Sample rate

    Returns:
        Mixed transition audio
    """
    # Determine transition length
    trans_length = min(len(audio_a), len(audio_b))
    if duration is not None:
        trans_length = min(trans_length, int(duration * sr))

    # Trim audio to transition length
    audio_a = audio_a[:trans_length]
    audio_b = audio_b[:trans_length]

    # Apply filter sweeps
    filtered_a = create_filter_sweep(
        audio_a,
        filter_type="hpf",
        start_freq=hpf_start_a,
        end_freq=hpf_end_a,
        curve=curve,
        sr=sr
    )

    filtered_b = create_filter_sweep(
        audio_b,
        filter_type="lpf",
        start_freq=lpf_start_b,
        end_freq=lpf_end_b,
        curve=curve,
        sr=sr
    )

    # Apply volume crossfade if requested
    if crossfade:
        fade_out = np.linspace(1, 0, trans_length).astype(np.float32)
        fade_in = np.linspace(0, 1, trans_length).astype(np.float32)

        # Equal power crossfade
        fade_out = np.sqrt(fade_out)
        fade_in = np.sqrt(fade_in)

        filtered_a = filtered_a * fade_out
        filtered_b = filtered_b * fade_in

    # Mix together
    output = filtered_a + filtered_b

    # Prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val

    return output


def apply_resonant_filter(
    audio: np.ndarray,
    filter_type: Literal["hpf", "lpf"],
    cutoff_freq: float,
    resonance: float = 2.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Apply a resonant filter with emphasized frequencies at cutoff.

    Higher resonance creates a "peak" at the cutoff frequency,
    giving the classic DJ filter sound.

    Args:
        audio: Input audio array
        filter_type: "hpf" or "lpf"
        cutoff_freq: Cutoff frequency in Hz
        resonance: Resonance amount (1-10, higher = more peak)
        sr: Sample rate

    Returns:
        Resonant filtered audio
    """
    # Basic filter
    filtered = apply_filter(audio, filter_type, cutoff_freq, sr=sr)

    # Add resonance peak using a narrow bandpass at cutoff
    if resonance > 1.0:
        bandwidth = 1.0 / resonance  # Narrower = more resonant
        resonant = apply_bandpass(audio, cutoff_freq, bandwidth, order=2, sr=sr)

        # Mix in resonance
        resonance_amount = (resonance - 1.0) / 9.0  # Scale 1-10 to 0-1
        filtered = filtered + resonant * resonance_amount * 0.5

        # Prevent clipping
        max_val = np.max(np.abs(filtered))
        if max_val > 1.0:
            filtered = filtered / max_val

    return filtered
