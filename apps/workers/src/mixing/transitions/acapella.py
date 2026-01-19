"""
Acapella Mixing - Live mashup technique.

Overlay vocal from one track on the instrumental of another.

PREREQUISITES:
- Compatible keys (vocal must sound in tune on instrumental)
- Compatible BPM (vocal can be time-stretched)
- Compatible styles (R&B vocal on hard techno = weird)

TECHNIQUE:
1. Extract vocal stem from track A with Demucs
2. Time-stretch to match track B BPM if needed
3. Pitch-shift if needed for harmonic compatibility
4. Overlay on instrumental of B
5. Mix levels so vocal is audible but integrated
"""

import numpy as np
from typing import Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()

# Try to import pyrubberband for high-quality time-stretching
try:
    import pyrubberband as pyrb
    PYRUBBERBAND_AVAILABLE = True
except ImportError:
    PYRUBBERBAND_AVAILABLE = False
    logger.warning("pyrubberband not available - using basic time-stretch")


def create_acapella_mix(
    vocal_stem: np.ndarray,
    instrumental_audio: np.ndarray,
    vocal_bpm: float,
    instrumental_bpm: float,
    vocal_key: Optional[str] = None,
    instrumental_key: Optional[str] = None,
    vocal_level: float = 0.8,
    instrumental_level: float = 1.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create an acapella mix (vocal over different instrumental).

    Args:
        vocal_stem: Isolated vocal from source track
        instrumental_audio: Instrumental from target track (or full mix minus vocals)
        vocal_bpm: BPM of the vocal source
        instrumental_bpm: BPM of the instrumental
        vocal_key: Key of the vocal (for pitch adjustment)
        instrumental_key: Key of the instrumental
        vocal_level: Volume level for vocal (0-1)
        instrumental_level: Volume level for instrumental (0-1)
        sr: Sample rate

    Returns:
        Mixed acapella audio
    """
    # Time-stretch vocal to match instrumental BPM
    if abs(vocal_bpm - instrumental_bpm) > 0.5:
        stretched_vocal = time_stretch_vocal(
            vocal_stem,
            vocal_bpm,
            instrumental_bpm,
            sr
        )
    else:
        stretched_vocal = vocal_stem.copy()

    # Pitch-shift if keys don't match
    if vocal_key and instrumental_key:
        semitones = calculate_pitch_shift(vocal_key, instrumental_key)
        if abs(semitones) > 0:
            stretched_vocal = pitch_shift_vocal(stretched_vocal, semitones, sr)

    # Determine mix length
    mix_length = min(len(stretched_vocal), len(instrumental_audio))

    # Create mix
    vocal_segment = stretched_vocal[:mix_length] * vocal_level
    instrumental_segment = instrumental_audio[:mix_length] * instrumental_level

    mix = vocal_segment + instrumental_segment

    # Normalize to prevent clipping
    max_val = np.max(np.abs(mix))
    if max_val > 1.0:
        mix = mix / max_val * 0.95

    # Append remaining instrumental if longer
    if len(instrumental_audio) > mix_length:
        remaining = instrumental_audio[mix_length:] * instrumental_level
        mix = np.concatenate([mix, remaining])

    return mix


def prepare_vocal_for_mix(
    vocal_stem: np.ndarray,
    source_bpm: float,
    target_bpm: float,
    source_key: Optional[str] = None,
    target_key: Optional[str] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Prepare a vocal stem for mixing over a different track.

    Applies necessary time-stretching and pitch-shifting.

    Args:
        vocal_stem: Isolated vocal audio
        source_bpm: Original BPM of vocal
        target_bpm: Target BPM to match
        source_key: Original key of vocal
        target_key: Target key to match
        sr: Sample rate

    Returns:
        Processed vocal ready for mixing
    """
    processed = vocal_stem.copy()

    # Time-stretch to target BPM
    if abs(source_bpm - target_bpm) > 0.5:
        processed = time_stretch_vocal(processed, source_bpm, target_bpm, sr)

    # Pitch-shift to target key
    if source_key and target_key:
        semitones = calculate_pitch_shift(source_key, target_key)
        if abs(semitones) > 0:
            processed = pitch_shift_vocal(processed, semitones, sr)

    return processed


def time_stretch_vocal(
    audio: np.ndarray,
    source_bpm: float,
    target_bpm: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Time-stretch audio to match target BPM.

    Args:
        audio: Input audio
        source_bpm: Original BPM
        target_bpm: Target BPM
        sr: Sample rate

    Returns:
        Time-stretched audio
    """
    ratio = source_bpm / target_bpm

    if PYRUBBERBAND_AVAILABLE:
        # High-quality time-stretch
        try:
            stretched = pyrb.time_stretch(audio.astype(np.float32), sr, ratio)
            return stretched
        except Exception as e:
            logger.warning(f"pyrubberband stretch failed: {e}")

    # Fallback: simple resampling (lower quality)
    import librosa
    target_length = int(len(audio) / ratio)
    stretched = librosa.resample(
        audio,
        orig_sr=len(audio),
        target_sr=target_length
    )
    return stretched


def pitch_shift_vocal(
    audio: np.ndarray,
    semitones: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Pitch-shift audio by a number of semitones.

    Args:
        audio: Input audio
        semitones: Number of semitones to shift (positive = higher)
        sr: Sample rate

    Returns:
        Pitch-shifted audio
    """
    if abs(semitones) < 0.1:
        return audio

    if PYRUBBERBAND_AVAILABLE:
        try:
            shifted = pyrb.pitch_shift(audio.astype(np.float32), sr, semitones)
            return shifted
        except Exception as e:
            logger.warning(f"pyrubberband pitch shift failed: {e}")

    # Fallback: FFT-based pitch shift (lower quality)
    import librosa
    shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones)
    return shifted


def calculate_pitch_shift(source_key: str, target_key: str) -> float:
    """
    Calculate pitch shift needed to go from source key to target key.

    Args:
        source_key: Source key (e.g., "Am", "8A")
        target_key: Target key

    Returns:
        Number of semitones to shift
    """
    from ...theory.camelot import get_camelot_from_key, get_key_from_camelot

    # Convert to Camelot if needed
    source_camelot = get_camelot_from_key(source_key)
    target_camelot = get_camelot_from_key(target_key)

    if not source_camelot or not target_camelot:
        return 0

    # Parse Camelot
    source_num = int(source_camelot[:-1])
    source_mode = source_camelot[-1]
    target_num = int(target_camelot[:-1])
    target_mode = target_camelot[-1]

    # If same mode, calculate semitone difference
    # Moving 1 position on Camelot = 5 semitones (circle of fifths)
    if source_mode == target_mode:
        position_diff = target_num - source_num
        # Handle wrap-around
        if position_diff > 6:
            position_diff -= 12
        elif position_diff < -6:
            position_diff += 12

        # Each position = 7 semitones (perfect fifth)
        # But we want the shorter path, so could also be -5 semitones
        semitones = position_diff * 7 % 12
        if semitones > 6:
            semitones -= 12

        return semitones

    else:
        # Different modes - relative major/minor is 3 semitones apart
        # First align to relative, then shift
        if source_mode == "A":
            # Minor to major: +3 semitones
            mode_shift = 3
        else:
            # Major to minor: -3 semitones
            mode_shift = -3

        position_diff = target_num - source_num
        if position_diff > 6:
            position_diff -= 12
        elif position_diff < -6:
            position_diff += 12

        semitones = (position_diff * 7 + mode_shift) % 12
        if semitones > 6:
            semitones -= 12

        return semitones


def create_acapella_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    vocal_stem_a: np.ndarray,
    transition_start: float,
    transition_duration: float,
    bpm_a: float,
    bpm_b: float,
    key_a: Optional[str] = None,
    key_b: Optional[str] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a transition using vocal from A over instrumental of B.

    Args:
        audio_a: Track A full audio
        audio_b: Track B full audio
        vocal_stem_a: Isolated vocal from track A
        transition_start: When to start the acapella mix
        transition_duration: How long to keep the vocal over B
        bpm_a: BPM of track A (vocal source)
        bpm_b: BPM of track B (instrumental destination)
        key_a: Key of track A
        key_b: Key of track B
        sr: Sample rate

    Returns:
        Transition audio
    """
    trans_start_sample = int(transition_start * sr)
    trans_duration_samples = int(transition_duration * sr)

    # Prepare vocal for mixing
    prepared_vocal = prepare_vocal_for_mix(
        vocal_stem_a,
        source_bpm=bpm_a,
        target_bpm=bpm_b,
        source_key=key_a,
        target_key=key_b,
        sr=sr
    )

    # Get track A before transition
    before_transition = audio_a[:trans_start_sample]

    # Get instrumental from B (ideally use stems, but can use full audio)
    instrumental_b = audio_b  # In practice, this should be audio_b without vocals

    # Create the acapella section
    vocal_section = prepared_vocal[:trans_duration_samples] if len(prepared_vocal) >= trans_duration_samples else prepared_vocal
    instrumental_section = instrumental_b[:trans_duration_samples] if len(instrumental_b) >= trans_duration_samples else instrumental_b

    # Mix vocal over instrumental
    mix_length = min(len(vocal_section), len(instrumental_section))
    acapella_mix = vocal_section[:mix_length] * 0.8 + instrumental_section[:mix_length] * 1.0

    # Normalize
    max_val = np.max(np.abs(acapella_mix))
    if max_val > 1.0:
        acapella_mix = acapella_mix / max_val * 0.95

    # Crossfade from A to acapella
    fade_samples = int(2.0 * sr)  # 2 second crossfade
    fade_samples = min(fade_samples, len(before_transition), len(acapella_mix))

    if fade_samples > 0:
        t = np.linspace(0, np.pi / 2, fade_samples)
        fade_out = np.cos(t)
        fade_in = np.sin(t)

        before_transition[-fade_samples:] *= fade_out
        acapella_mix[:fade_samples] *= fade_in

    # Get remainder of B after acapella section
    remainder_start = trans_duration_samples
    if remainder_start < len(instrumental_b):
        remainder = instrumental_b[remainder_start:]
    else:
        remainder = np.array([])

    # Crossfade from acapella to B remainder
    if len(acapella_mix) >= fade_samples and len(remainder) >= fade_samples:
        acapella_mix[-fade_samples:] *= np.cos(np.linspace(0, np.pi / 2, fade_samples))
        remainder[:fade_samples] *= np.sin(np.linspace(0, np.pi / 2, fade_samples))

    # Combine all parts
    result = np.concatenate([before_transition, acapella_mix, remainder])

    return result
