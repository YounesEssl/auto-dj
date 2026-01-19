"""
Double Drop - Advanced risky technique.

Play the drops of two tracks SIMULTANEOUSLY.
Creates maximum intensity moment.

ABSOLUTE PREREQUISITES:
- Keys PERFECTLY compatible (same key or ±1)
- BPM identical (or <1% difference)
- Compatible structures (drops of same length)
- Complementary elements (not two identical leads)

EXECUTION:
1. Identify drops in both tracks
2. Align perfectly on beat 1
3. Mix stems intelligently:
   - Drums: Can overlay (adds power)
   - Bass: CAUTION - choose one bass or alternate
   - Leads/Melody: Must be complementary, not conflicting
4. Typical duration: 8-16 bars then transition to single track
"""

import numpy as np
from typing import Dict, Optional, Tuple
from ...theory.camelot import calculate_harmonic_compatibility
import structlog

logger = structlog.get_logger()


def validate_double_drop_compatibility(
    track_a: Dict,
    track_b: Dict,
    max_bpm_diff_percent: float = 1.0,
    min_harmonic_score: int = 90
) -> Dict:
    """
    Validate if two tracks are compatible for a double drop.

    Double drops are RISKY - only use when conditions are PERFECT.

    Args:
        track_a: Track A metadata (bpm, key, energy, etc.)
        track_b: Track B metadata
        max_bpm_diff_percent: Maximum allowed BPM difference
        min_harmonic_score: Minimum required harmonic score

    Returns:
        Dict with compatibility result and warnings
    """
    result = {
        "compatible": False,
        "risk_level": "high",
        "warnings": [],
        "recommendations": []
    }

    # Check BPM compatibility
    bpm_a = track_a.get("bpm", 128)
    bpm_b = track_b.get("bpm", 128)
    bpm_diff_percent = abs(bpm_a - bpm_b) / ((bpm_a + bpm_b) / 2) * 100

    if bpm_diff_percent > max_bpm_diff_percent:
        result["warnings"].append(f"BPM difference too large: {bpm_diff_percent:.1f}%")
        result["recommendations"].append("Use standard blend or hard cut instead")
        return result

    # Check harmonic compatibility
    key_a = track_a.get("key") or track_a.get("camelot")
    key_b = track_b.get("key") or track_b.get("camelot")

    harmonic = calculate_harmonic_compatibility(key_a, key_b)

    if harmonic["score"] < min_harmonic_score:
        result["warnings"].append(f"Harmonic score too low: {harmonic['score']} ({harmonic['type']})")
        result["recommendations"].append("Double drop requires near-perfect harmony")
        return result

    # Check energy levels
    energy_a = track_a.get("energy", 0.5)
    energy_b = track_b.get("energy", 0.5)

    if energy_a < 0.7 or energy_b < 0.7:
        result["warnings"].append("One or both tracks have low energy")
        result["recommendations"].append("Double drops work best with high-energy tracks")

    # If we got here, it's compatible
    result["compatible"] = True
    result["risk_level"] = "medium" if harmonic["score"] == 100 else "high"
    result["harmonic_score"] = harmonic["score"]
    result["bpm_diff_percent"] = bpm_diff_percent

    if harmonic["score"] == 100:
        result["recommendations"].append("Perfect key match - ideal for double drop")
    else:
        result["recommendations"].append(f"Good harmony ({harmonic['type']}) - proceed with caution")

    return result


def create_double_drop(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    drop_start_a: float,
    drop_start_b: float,
    drop_duration_bars: int,
    bpm: float,
    stem_mix: Optional[Dict] = None,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a double drop transition.

    USE WITH EXTREME CAUTION - Only if conditions are perfect.

    Args:
        stems_a: Stems from track A {drums, bass, vocals, other}
        stems_b: Stems from track B
        drop_start_a: Drop start time in track A (seconds)
        drop_start_b: Drop start time in track B (seconds)
        drop_duration_bars: How many bars to play the double drop
        bpm: Tempo
        stem_mix: Level mixing {stem_name: [level_a, level_b]}
        sr: Sample rate

    Returns:
        Double drop audio
    """
    bar_duration = (60.0 / bpm) * 4
    drop_duration = drop_duration_bars * bar_duration
    drop_samples = int(drop_duration * sr)

    # Default stem mix - BASS is the critical one
    if stem_mix is None:
        stem_mix = {
            "drums": [0.6, 0.6],      # Both at 60% (combined power)
            "bass": [1.0, 0.0],        # ONLY A's bass (never both!)
            "vocals": [0.5, 0.5],      # Both reduced
            "other": [0.5, 0.5]        # Both reduced
        }

    drop_start_sample_a = int(drop_start_a * sr)
    drop_start_sample_b = int(drop_start_b * sr)

    output = np.zeros(drop_samples, dtype=np.float32)

    for stem_name in ["drums", "bass", "vocals", "other"]:
        level_a, level_b = stem_mix.get(stem_name, [0.5, 0.5])

        stem_a = stems_a.get(stem_name)
        stem_b = stems_b.get(stem_name)

        if stem_a is not None:
            end_a = drop_start_sample_a + drop_samples
            if end_a <= len(stem_a):
                segment_a = stem_a[drop_start_sample_a:end_a] * level_a
                output += segment_a

        if stem_b is not None:
            end_b = drop_start_sample_b + drop_samples
            if end_b <= len(stem_b):
                segment_b = stem_b[drop_start_sample_b:end_b] * level_b
                output += segment_b

    # Normalize to prevent clipping
    max_val = np.max(np.abs(output))
    if max_val > 1.0:
        output = output / max_val * 0.95
        logger.debug("Double drop normalized to prevent clipping")

    return output


def create_double_drop_with_exit(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    drop_start_a: float,
    drop_start_b: float,
    double_drop_bars: int,
    exit_to: str = "B",
    exit_bars: int = 8,
    bpm: float = 128.0,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a full double drop with smooth exit to one track.

    Args:
        stems_a: Stems from track A
        stems_b: Stems from track B
        audio_a: Full audio A
        audio_b: Full audio B
        drop_start_a: Drop start in A
        drop_start_b: Drop start in B
        double_drop_bars: Duration of double drop
        exit_to: Which track to exit to ("A" or "B")
        exit_bars: Duration of exit transition
        bpm: Tempo
        sr: Sample rate

    Returns:
        Full transition audio
    """
    bar_duration = (60.0 / bpm) * 4

    # Create double drop section
    double_drop = create_double_drop(
        stems_a=stems_a,
        stems_b=stems_b,
        drop_start_a=drop_start_a,
        drop_start_b=drop_start_b,
        drop_duration_bars=double_drop_bars,
        bpm=bpm,
        sr=sr
    )

    # Get continuation from the exit track
    exit_duration = exit_bars * bar_duration
    exit_samples = int(exit_duration * sr)

    if exit_to == "B":
        # Continue with B after double drop
        exit_start_sample = int(drop_start_b * sr) + len(double_drop)
        if exit_start_sample < len(audio_b):
            continuation = audio_b[exit_start_sample:]
        else:
            continuation = np.array([])

        # Crossfade from double drop to B continuation
        if len(double_drop) >= exit_samples and len(continuation) >= exit_samples:
            t = np.linspace(0, np.pi / 2, exit_samples)
            fade_out = np.cos(t)
            fade_in = np.sin(t)

            exit_from_dd = double_drop[-exit_samples:] * fade_out
            exit_to_b = continuation[:exit_samples] * fade_in

            exit_mix = exit_from_dd + exit_to_b

            result = np.concatenate([
                double_drop[:-exit_samples],
                exit_mix,
                continuation[exit_samples:]
            ])
        else:
            result = np.concatenate([double_drop, continuation])

    else:  # exit to A
        exit_start_sample = int(drop_start_a * sr) + len(double_drop)
        if exit_start_sample < len(audio_a):
            continuation = audio_a[exit_start_sample:]
        else:
            continuation = np.array([])

        if len(double_drop) >= exit_samples and len(continuation) >= exit_samples:
            t = np.linspace(0, np.pi / 2, exit_samples)
            fade_out = np.cos(t)
            fade_in = np.sin(t)

            exit_from_dd = double_drop[-exit_samples:] * fade_out
            exit_to_a = continuation[:exit_samples] * fade_in

            exit_mix = exit_from_dd + exit_to_a

            result = np.concatenate([
                double_drop[:-exit_samples],
                exit_mix,
                continuation[exit_samples:]
            ])
        else:
            result = np.concatenate([double_drop, continuation])

    return result


def get_safe_double_drop_mix() -> Dict:
    """
    Get a safe default stem mix for double drops.

    CRITICAL: Bass should NEVER be from both tracks simultaneously.
    """
    return {
        "drums": [0.5, 0.5],      # Combined at 50% each
        "bass": [1.0, 0.0],        # ONLY track A bass
        "vocals": [0.3, 0.3],      # Both quiet
        "other": [0.4, 0.4]        # Both moderate
    }


def get_alternating_bass_mix(
    double_drop_bars: int,
    swap_every_bars: int = 4
) -> Dict:
    """
    Create a mix configuration that alternates bass between tracks.

    This is safer than simultaneous bass and creates rhythmic interest.

    Args:
        double_drop_bars: Total double drop duration
        swap_every_bars: How often to swap bass

    Returns:
        Mix configuration with bass alternation info
    """
    num_swaps = double_drop_bars // swap_every_bars

    bass_pattern = []
    for i in range(num_swaps):
        if i % 2 == 0:
            bass_pattern.append({"bars": (i * swap_every_bars, (i + 1) * swap_every_bars), "a": 1.0, "b": 0.0})
        else:
            bass_pattern.append({"bars": (i * swap_every_bars, (i + 1) * swap_every_bars), "a": 0.0, "b": 1.0})

    return {
        "drums": [0.5, 0.5],
        "bass": bass_pattern,
        "vocals": [0.3, 0.3],
        "other": [0.4, 0.4],
        "alternating_bass": True
    }
