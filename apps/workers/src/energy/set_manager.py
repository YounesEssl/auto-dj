"""
Set phase management for DJ sets.

A successful DJ set is NOT a constant energy climb.
It's a JOURNEY with intentional peaks and valleys.

TYPICAL SET STRUCTURE (2 hours):

| Phase    | Duration  | Energy  | BPM       | Transition Style     |
|----------|-----------|---------|-----------|----------------------|
| Warmup   | 0-30 min  | 3-5/10  | Moderate  | Long blends (32-64)  |
| Build    | 30-60 min | 5-7/10  | Rising    | Medium blends (16-32)|
| Peak     | 60-90 min | 8-10/10 | Maximum   | Varied (8-16)        |
| Cooldown | 90-120min | 6-4/10  | Declining | Long blends (32-64)  |
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, List


class SetPhase(Enum):
    """Phases of a DJ set."""
    WARMUP = "WARMUP"
    BUILD = "BUILD"
    PEAK = "PEAK"
    COOLDOWN = "COOLDOWN"


@dataclass
class PhaseConfig:
    """Configuration for a set phase."""
    phase: SetPhase
    energy_range: Tuple[int, int]  # (min, max) out of 10
    transition_style: str
    transition_bars: Tuple[int, int]  # (min, max)
    bpm_change: str  # "stable", "increasing", "decreasing"
    preferred_transitions: List[str]


# Phase configurations
PHASE_CONFIGS = {
    SetPhase.WARMUP: PhaseConfig(
        phase=SetPhase.WARMUP,
        energy_range=(3, 5),
        transition_style="long_blend",
        transition_bars=(32, 64),
        bpm_change="stable",
        preferred_transitions=["STEM_BLEND", "CROSSFADE"]
    ),
    SetPhase.BUILD: PhaseConfig(
        phase=SetPhase.BUILD,
        energy_range=(5, 7),
        transition_style="medium_blend",
        transition_bars=(16, 32),
        bpm_change="slightly_increasing",
        preferred_transitions=["STEM_BLEND", "CROSSFADE", "FILTER_SWEEP"]
    ),
    SetPhase.PEAK: PhaseConfig(
        phase=SetPhase.PEAK,
        energy_range=(8, 10),
        transition_style="varied",
        transition_bars=(8, 16),
        bpm_change="stable_high",
        preferred_transitions=["STEM_BLEND", "HARD_CUT", "DOUBLE_DROP"]
    ),
    SetPhase.COOLDOWN: PhaseConfig(
        phase=SetPhase.COOLDOWN,
        energy_range=(4, 6),
        transition_style="long_blend",
        transition_bars=(32, 64),
        bpm_change="decreasing",
        preferred_transitions=["STEM_BLEND", "CROSSFADE", "ECHO_OUT"]
    ),
}


def determine_set_phase(
    track_index: int,
    total_tracks: int,
    elapsed_time: Optional[float] = None,
    total_duration: Optional[float] = None
) -> dict:
    """
    Determine the current phase of the set.

    Can use either track index or time-based progress.

    Args:
        track_index: Current track index (0-based)
        total_tracks: Total number of tracks in set
        elapsed_time: Elapsed time in seconds (optional)
        total_duration: Total set duration in seconds (optional)

    Returns:
        Dict with phase info and recommendations
    """
    # Calculate progress (0-1)
    if elapsed_time is not None and total_duration is not None and total_duration > 0:
        progress = elapsed_time / total_duration
    elif total_tracks > 0:
        progress = track_index / total_tracks
    else:
        progress = 0.5  # Default to middle if unknown

    # Determine phase based on progress
    if progress < 0.25:
        phase = SetPhase.WARMUP
    elif progress < 0.50:
        phase = SetPhase.BUILD
    elif progress < 0.75:
        phase = SetPhase.PEAK
    else:
        phase = SetPhase.COOLDOWN

    config = PHASE_CONFIGS[phase]

    return {
        "phase": phase.value,
        "progress": progress,
        "target_energy": config.energy_range,
        "transition_style": config.transition_style,
        "transition_bars": config.transition_bars,
        "bpm_change": config.bpm_change,
        "preferred_transitions": config.preferred_transitions
    }


def get_transition_recommendations(
    phase: str,
    current_energy: float,
    next_energy: float,
    harmonic_score: int,
    bpm_diff_percent: float
) -> dict:
    """
    Get specific transition recommendations based on context.

    Args:
        phase: Current set phase ("WARMUP", "BUILD", "PEAK", "COOLDOWN")
        current_energy: Current track energy (0-1)
        next_energy: Next track energy (0-1)
        harmonic_score: Harmonic compatibility score (0-100)
        bpm_diff_percent: BPM difference percentage

    Returns:
        Dict with transition type, duration, and specific recommendations
    """
    # Get phase config
    try:
        phase_enum = SetPhase(phase)
    except ValueError:
        phase_enum = SetPhase.BUILD  # Default

    config = PHASE_CONFIGS[phase_enum]

    # Base recommendations
    recommendations = {
        "phase": phase,
        "suggested_type": "STEM_BLEND",
        "suggested_bars": config.transition_bars[0],
        "bass_swap_bar": config.transition_bars[0] // 2,
        "effects": [],
        "warnings": [],
        "confidence": 0.9
    }

    # Adjust based on harmonic compatibility
    if harmonic_score >= 90:
        # Excellent harmony - long blend OK
        recommendations["suggested_bars"] = config.transition_bars[1]
        recommendations["confidence"] = 0.95
    elif harmonic_score >= 70:
        # Good harmony - medium blend
        recommendations["suggested_bars"] = (config.transition_bars[0] + config.transition_bars[1]) // 2
    elif harmonic_score >= 50:
        # Marginal harmony - short blend or filter sweep
        recommendations["suggested_bars"] = config.transition_bars[0]
        recommendations["suggested_type"] = "FILTER_SWEEP"
        recommendations["warnings"].append("MARGINAL_HARMONIC_COMPATIBILITY")
    else:
        # Poor harmony - hard cut required
        recommendations["suggested_type"] = "HARD_CUT"
        recommendations["suggested_bars"] = 0
        recommendations["effects"].append("reverb_tail")
        recommendations["warnings"].append("HARD_CUT_REQUIRED_HARMONIC_CLASH")
        recommendations["confidence"] = 0.85

    # Adjust based on BPM difference
    if bpm_diff_percent > 6:
        recommendations["suggested_type"] = "HARD_CUT"
        recommendations["suggested_bars"] = 0
        recommendations["warnings"].append("BPM_DIFFERENCE_TOO_LARGE")
        recommendations["confidence"] = min(recommendations["confidence"], 0.8)
    elif bpm_diff_percent > 4:
        recommendations["warnings"].append("BPM_STRETCH_AUDIBLE")

    # Adjust based on energy delta
    energy_delta = next_energy - current_energy

    if phase_enum == SetPhase.WARMUP:
        # Warmup: prefer gradual energy increase
        if energy_delta > 0.3:
            recommendations["warnings"].append("ENERGY_JUMP_TOO_LARGE_FOR_WARMUP")
    elif phase_enum == SetPhase.BUILD:
        # Build: energy should generally increase
        if energy_delta < -0.2:
            recommendations["warnings"].append("ENERGY_DROP_DURING_BUILD_PHASE")
    elif phase_enum == SetPhase.PEAK:
        # Peak: maintain high energy, allow variety
        if next_energy < 0.7:
            recommendations["warnings"].append("LOW_ENERGY_TRACK_DURING_PEAK")
    elif phase_enum == SetPhase.COOLDOWN:
        # Cooldown: energy should decrease
        if energy_delta > 0.2:
            recommendations["warnings"].append("ENERGY_INCREASE_DURING_COOLDOWN")

    # Update bass swap bar based on suggested duration
    recommendations["bass_swap_bar"] = max(1, recommendations["suggested_bars"] // 2)

    return recommendations


def calculate_energy_trajectory(
    tracks: List[dict],
    current_phase: Optional[str] = None
) -> List[dict]:
    """
    Calculate the energy trajectory for a sequence of tracks.

    Args:
        tracks: List of track dicts with 'energy' field (0-1)
        current_phase: Optional current phase to validate against

    Returns:
        List of tracks with added trajectory info
    """
    if not tracks:
        return []

    result = []
    prev_energy = None

    for i, track in enumerate(tracks):
        energy = track.get("energy", 0.5)

        info = {
            **track,
            "index": i,
            "energy": energy,
            "energy_percent": int(energy * 100),
        }

        if prev_energy is not None:
            delta = energy - prev_energy
            info["energy_delta"] = delta
            info["energy_direction"] = "up" if delta > 0.05 else ("down" if delta < -0.05 else "stable")
        else:
            info["energy_delta"] = 0
            info["energy_direction"] = "start"

        # Determine phase for this track position
        phase_info = determine_set_phase(i, len(tracks))
        info["suggested_phase"] = phase_info["phase"]

        # Check if energy matches phase expectations
        target_min, target_max = phase_info["target_energy"]
        energy_10 = int(energy * 10)

        if energy_10 < target_min:
            info["energy_warning"] = f"Energy below target for {phase_info['phase']} (expected {target_min}-{target_max})"
        elif energy_10 > target_max:
            info["energy_warning"] = f"Energy above target for {phase_info['phase']} (expected {target_min}-{target_max})"
        else:
            info["energy_warning"] = None

        result.append(info)
        prev_energy = energy

    return result


def get_effective_track_duration(
    phase: str,
    track_duration: float,
    transition_duration: float
) -> Tuple[float, float]:
    """
    Calculate how much of a track should be played based on set phase.

    Args:
        phase: Current set phase
        track_duration: Total track duration in seconds
        transition_duration: Transition duration in seconds

    Returns:
        Tuple of (play_duration_seconds, percentage_played)
    """
    # Phase multipliers for track usage
    # Higher multiplier = play more of the track
    phase_multipliers = {
        "WARMUP": (0.70, 0.90),     # Play 70-90% of tracks
        "BUILD": (0.60, 0.80),      # Play 60-80% of tracks
        "PEAK": (0.40, 0.70),       # Play 40-70% of tracks (faster turnover)
        "COOLDOWN": (0.70, 0.90),   # Play 70-90% of tracks
    }

    min_mult, max_mult = phase_multipliers.get(phase, (0.60, 0.80))

    # Use middle of range by default
    multiplier = (min_mult + max_mult) / 2

    # Calculate play duration
    play_duration = track_duration * multiplier

    # Ensure at least transition duration + some play time
    min_play = transition_duration * 2
    play_duration = max(play_duration, min_play)

    # Don't exceed track duration
    play_duration = min(play_duration, track_duration)

    percentage = (play_duration / track_duration) * 100 if track_duration > 0 else 0

    return (play_duration, percentage)
