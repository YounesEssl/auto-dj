"""
Transition scoring module

Combines multiple factors to score how well two tracks will mix together.
"""

from typing import Any, Dict

from src.ordering.camelot_rules import calculate_compatibility_score


def score_transition(
    track_from: Dict[str, Any],
    track_to: Dict[str, Any]
) -> float:
    """
    Score the quality of a transition between two tracks.

    Factors considered:
    - Harmonic compatibility (Camelot wheel)
    - BPM compatibility
    - Energy progression
    - Danceability match

    Args:
        track_from: Source track analysis data
        track_to: Destination track analysis data

    Returns:
        Score from 0 to 1 where 1 is a perfect transition
    """
    analysis_from = track_from.get("analysis", {})
    analysis_to = track_to.get("analysis", {})

    # Harmonic compatibility (weight: 40%)
    camelot_from = analysis_from.get("camelot", "8A")
    camelot_to = analysis_to.get("camelot", "8A")
    harmonic_score = calculate_compatibility_score(camelot_from, camelot_to)

    # BPM compatibility (weight: 30%)
    bpm_from = analysis_from.get("bpm", 128)
    bpm_to = analysis_to.get("bpm", 128)
    bpm_score = _score_bpm_compatibility(bpm_from, bpm_to)

    # Energy progression (weight: 20%)
    energy_from = analysis_from.get("energy", 0.5)
    energy_to = analysis_to.get("energy", 0.5)
    energy_score = _score_energy_progression(energy_from, energy_to)

    # Danceability match (weight: 10%)
    dance_from = analysis_from.get("danceability", 0.5)
    dance_to = analysis_to.get("danceability", 0.5)
    dance_score = _score_danceability_match(dance_from, dance_to)

    # Weighted combination
    total_score = (
        harmonic_score * 0.4 +
        bpm_score * 0.3 +
        energy_score * 0.2 +
        dance_score * 0.1
    )

    return total_score


def _score_bpm_compatibility(bpm1: float, bpm2: float) -> float:
    """
    Score BPM compatibility.

    Perfect if within 3 BPM, good if within 6, acceptable if within 10.
    Also considers half-time/double-time relationships.
    """
    diff = abs(bpm1 - bpm2)

    # Check for half-time/double-time
    if bpm1 > bpm2:
        ratio = bpm1 / bpm2
    else:
        ratio = bpm2 / bpm1

    # Near 2:1 ratio is acceptable
    if abs(ratio - 2.0) < 0.1:
        return 0.7

    # Score based on absolute difference
    if diff <= 3:
        return 1.0
    elif diff <= 6:
        return 0.85
    elif diff <= 10:
        return 0.6
    elif diff <= 15:
        return 0.3
    else:
        return 0.1


def _score_energy_progression(energy_from: float, energy_to: float) -> float:
    """
    Score energy progression.

    Slight increases in energy are preferred for building sets.
    Large jumps or drops are penalized.
    """
    diff = energy_to - energy_from

    # Slight increase is ideal (building energy)
    if 0 <= diff <= 0.15:
        return 1.0

    # Slight decrease is okay
    if -0.1 <= diff < 0:
        return 0.85

    # Moderate change
    if -0.2 <= diff <= 0.25:
        return 0.6

    # Large change
    return 0.3


def _score_danceability_match(dance1: float, dance2: float) -> float:
    """
    Score danceability similarity.

    Tracks with similar danceability flow better together.
    """
    diff = abs(dance1 - dance2)

    if diff <= 0.1:
        return 1.0
    elif diff <= 0.2:
        return 0.8
    elif diff <= 0.3:
        return 0.5
    else:
        return 0.3
