"""
Serpentine flow and teasing techniques for DJ sets.

SERPENTINE FLOW:
Alternate between high and low energy in a 5:1 ratio.
This prevents listener fatigue and makes the highs feel higher.

Example:
HIGH -> HIGH -> HIGH -> HIGH -> HIGH -> MEDIUM -> HIGH -> HIGH -> ...

The "breathing room" (MEDIUM) amplifies the impact of subsequent HIGHs.

TEASING:
Hint at high-energy moments without delivering immediately.
Creates anticipation and makes the payoff more satisfying.
"""

import numpy as np
from typing import List, Optional, Tuple, Literal


def apply_serpentine_flow(
    tracks: List[dict],
    high_energy_threshold: float = 0.7,
    ratio: int = 5
) -> List[dict]:
    """
    Reorder or suggest modifications to follow serpentine flow.

    The serpentine flow alternates between high and lower energy
    tracks in a specific ratio (default 5:1).

    Args:
        tracks: List of track dicts with 'energy' field (0-1)
        high_energy_threshold: Energy level considered "high" (0-1)
        ratio: Number of high energy tracks before a breather

    Returns:
        Reordered list with serpentine flow applied
    """
    if not tracks or len(tracks) < 3:
        return tracks

    # Separate tracks by energy level
    high_energy = [t for t in tracks if t.get("energy", 0.5) >= high_energy_threshold]
    medium_energy = [t for t in tracks if t.get("energy", 0.5) < high_energy_threshold]

    if not high_energy or not medium_energy:
        return tracks  # Can't apply serpentine without both

    # Sort each group by energy (descending for high, ascending for medium)
    high_energy.sort(key=lambda t: t.get("energy", 0.5), reverse=True)
    medium_energy.sort(key=lambda t: t.get("energy", 0.5))

    # Build serpentine pattern
    result = []
    high_idx = 0
    medium_idx = 0
    consecutive_high = 0

    while high_idx < len(high_energy) or medium_idx < len(medium_energy):
        if consecutive_high < ratio and high_idx < len(high_energy):
            # Add high energy track
            result.append(high_energy[high_idx])
            high_idx += 1
            consecutive_high += 1
        elif medium_idx < len(medium_energy):
            # Add breather (medium energy)
            result.append(medium_energy[medium_idx])
            medium_idx += 1
            consecutive_high = 0
        elif high_idx < len(high_energy):
            # No more medium tracks, continue with high
            result.append(high_energy[high_idx])
            high_idx += 1

    return result


def suggest_energy_ordering(
    tracks: List[dict],
    target_flow: Literal["serpentine", "ascending", "descending", "peak_middle"] = "serpentine"
) -> List[dict]:
    """
    Suggest an optimal track ordering based on energy.

    Args:
        tracks: List of track dicts with 'energy' field
        target_flow: Desired energy flow pattern

    Returns:
        Reordered track list
    """
    if not tracks:
        return tracks

    tracks_copy = [dict(t) for t in tracks]  # Don't modify original

    if target_flow == "serpentine":
        return apply_serpentine_flow(tracks_copy)

    elif target_flow == "ascending":
        # Sort low to high energy
        tracks_copy.sort(key=lambda t: t.get("energy", 0.5))
        return tracks_copy

    elif target_flow == "descending":
        # Sort high to low energy
        tracks_copy.sort(key=lambda t: t.get("energy", 0.5), reverse=True)
        return tracks_copy

    elif target_flow == "peak_middle":
        # Build up to middle, then bring down
        tracks_copy.sort(key=lambda t: t.get("energy", 0.5))
        mid = len(tracks_copy) // 2

        # Interleave: take from both ends alternating
        result = []
        left = 0
        right = len(tracks_copy) - 1
        take_left = True

        while left <= right:
            if take_left:
                result.append(tracks_copy[left])
                left += 1
            else:
                result.append(tracks_copy[right])
                right -= 1
            take_left = not take_left

        # This creates: lowest, highest, 2nd lowest, 2nd highest, etc.
        # Reverse first half to get: ascending to peak, then descending
        mid_result = len(result) // 2
        first_half = result[:mid_result]
        second_half = result[mid_result:]
        second_half.reverse()

        return first_half + second_half

    return tracks_copy


def validate_energy_flow(
    tracks: List[dict],
    max_energy_jump: float = 0.3,
    max_consecutive_high: int = 6
) -> List[dict]:
    """
    Validate and report issues with energy flow.

    Args:
        tracks: List of track dicts with 'energy' field
        max_energy_jump: Maximum allowed energy change between tracks
        max_consecutive_high: Maximum consecutive high-energy tracks

    Returns:
        List of issues found (empty if no issues)
    """
    issues = []

    if len(tracks) < 2:
        return issues

    consecutive_high = 0
    high_threshold = 0.7

    for i in range(len(tracks)):
        energy = tracks[i].get("energy", 0.5)

        # Check consecutive high
        if energy >= high_threshold:
            consecutive_high += 1
            if consecutive_high > max_consecutive_high:
                issues.append({
                    "index": i,
                    "type": "CONSECUTIVE_HIGH_ENERGY",
                    "message": f"Track {i+1}: {consecutive_high} consecutive high-energy tracks without breather",
                    "severity": "warning"
                })
        else:
            consecutive_high = 0

        # Check energy jump
        if i > 0:
            prev_energy = tracks[i - 1].get("energy", 0.5)
            delta = abs(energy - prev_energy)

            if delta > max_energy_jump:
                issues.append({
                    "index": i,
                    "type": "LARGE_ENERGY_JUMP",
                    "message": f"Track {i+1}: Energy jump of {delta:.0%} (from {prev_energy:.0%} to {energy:.0%})",
                    "severity": "warning" if delta < 0.5 else "error"
                })

    return issues


def create_tease(
    audio: np.ndarray,
    buildup_start: float,
    buildup_end: float,
    drop_start: float,
    tease_type: Literal["cut_before_drop", "filtered_drop", "half_drop"] = "cut_before_drop",
    sr: int = 44100
) -> np.ndarray:
    """
    Create a tease moment (hint at drop without delivering).

    This creates anticipation by:
    - Playing a buildup but cutting before the drop
    - Playing a filtered/muted version of the drop
    - Playing half the drop then pulling back

    Args:
        audio: Full audio array
        buildup_start: Start of buildup section (seconds)
        buildup_end: End of buildup / start of drop (seconds)
        drop_start: Where the drop actually begins (seconds)
        tease_type: Type of tease to create
        sr: Sample rate

    Returns:
        Modified audio with tease effect
    """
    buildup_start_sample = int(buildup_start * sr)
    buildup_end_sample = int(buildup_end * sr)
    drop_start_sample = int(drop_start * sr)

    # Validate bounds
    if buildup_start_sample >= len(audio) or buildup_end_sample >= len(audio):
        return audio

    if tease_type == "cut_before_drop":
        # Play buildup, then silence/fade where drop would be
        output = np.zeros_like(audio)

        # Copy everything before buildup
        output[:buildup_start_sample] = audio[:buildup_start_sample]

        # Copy buildup
        output[buildup_start_sample:buildup_end_sample] = audio[buildup_start_sample:buildup_end_sample]

        # Fade out quickly at the end of buildup
        fade_samples = min(int(0.5 * sr), buildup_end_sample - buildup_start_sample)
        fade_out = np.linspace(1, 0, fade_samples)
        output[buildup_end_sample - fade_samples:buildup_end_sample] *= fade_out

        # Skip the drop section, continue after
        # (In practice, this would be followed by a different track)

        return output[:buildup_end_sample]

    elif tease_type == "filtered_drop":
        # Play buildup normally, then play drop with heavy low-pass filter
        from ..mixing.effects.filters import apply_lpf

        output = audio.copy()

        # Apply LPF to drop section
        if drop_start_sample < len(audio):
            drop_section = audio[drop_start_sample:]
            filtered_drop = apply_lpf(drop_section, cutoff_freq=300, sr=sr)

            # Also reduce volume
            filtered_drop *= 0.5

            output[drop_start_sample:] = filtered_drop

        return output

    elif tease_type == "half_drop":
        # Play half the drop, then pull back with filter
        from ..mixing.effects.filters import create_filter_sweep

        output = audio.copy()

        if drop_start_sample < len(audio):
            # Calculate half drop duration (typically 8 bars)
            # Assume drop is about 16 bars, so half is 8
            half_drop_samples = int(8 * sr)  # Rough estimate

            # After half drop, apply HPF sweep up
            half_drop_end = drop_start_sample + half_drop_samples

            if half_drop_end < len(audio):
                fade_section = audio[half_drop_end:]
                faded = create_filter_sweep(
                    fade_section,
                    filter_type="hpf",
                    start_freq=20,
                    end_freq=2000,
                    duration=2.0,
                    sr=sr
                )

                # Volume fade too
                fade_envelope = np.linspace(1, 0, len(faded))
                faded = faded * fade_envelope

                output[half_drop_end:half_drop_end + len(faded)] = faded[:len(output) - half_drop_end]

        return output

    return audio


def calculate_tease_positions(
    structure: dict,
    num_teases: int = 1
) -> List[dict]:
    """
    Calculate optimal positions for tease moments based on track structure.

    Args:
        structure: Track structure dict with 'sections' containing buildups and drops
        num_teases: Number of tease positions to find

    Returns:
        List of tease position suggestions
    """
    positions = []

    sections = structure.get("sections", [])

    # Find buildup-drop pairs
    for i, section in enumerate(sections):
        if section.get("type") == "buildup":
            # Look for following drop
            if i + 1 < len(sections) and sections[i + 1].get("type") == "drop":
                drop = sections[i + 1]

                positions.append({
                    "buildup_start": section.get("start_time", 0),
                    "buildup_end": section.get("end_time", 0),
                    "drop_start": drop.get("start_time", 0),
                    "drop_end": drop.get("end_time", 0),
                    "tease_potential": "high" if i == 0 else "medium"  # First buildup often best for tease
                })

    # Sort by potential and return requested number
    positions.sort(key=lambda x: 0 if x["tease_potential"] == "high" else 1)

    return positions[:num_teases]
