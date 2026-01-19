"""
Mix Points Detection Module.

Identifies the best points for DJ mixing:
- MIX IN: Where to start introducing an incoming track
- MIX OUT: Where to start exiting an outgoing track
- CUE POINTS: Points of interest (drops, breakdowns, vocal entries)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


def analyze_mix_points(
    structure: Dict,
    phrases: List[Dict],
    vocals: Dict,
    energy: float,
    duration: float,
    bpm: float
) -> Dict:
    """
    Analyze and return optimal mix points for a track.

    Rules for mix points:
    - Mix in on a phrase boundary
    - Mix out after a drop or on outro
    - Avoid mixing during intense vocals
    - Breakdowns are excellent transition zones

    Args:
        structure: Track structure with sections (intro, outro, drops, etc.)
        phrases: Detected phrases
        vocals: Vocal detection results
        energy: Overall track energy (0-1)
        duration: Track duration in seconds
        bpm: Track tempo

    Returns:
        Dict with best_mix_in_points, best_mix_out_points, cue_points
    """
    bar_duration = (60.0 / bpm) * 4

    mix_in_points = []
    mix_out_points = []
    cue_points = []

    # Get sections from structure
    intro = structure.get("intro", {})
    outro = structure.get("outro", {})
    sections = structure.get("sections", [])

    # Get vocal sections for clash avoidance
    vocal_sections = vocals.get("vocal_sections", []) if vocals.get("has_vocals") else []

    # === MIX IN POINTS ===

    # 1. Intro is always a good mix-in point
    if intro:
        intro_start = intro.get("start", 0)
        intro_end = intro.get("end", 16)
        mix_in_points.append({
            "time": intro_start,
            "type": "INTRO_START",
            "quality": "excellent",
            "reason": "Track intro - designed for mixing in",
            "duration_available": intro_end - intro_start
        })

    # 2. Beginning of each phrase (after intro)
    for phrase in phrases:
        phrase_start = phrase.get("start_time", 0)

        # Skip if in intro (already covered)
        if intro and phrase_start <= intro.get("end", 0):
            continue

        # Check if this phrase start has vocals
        has_vocal_at_start = any(
            v["start"] <= phrase_start < v["end"]
            for v in vocal_sections
            if v.get("intensity") == "FULL"
        )

        if not has_vocal_at_start:
            # Find what section this phrase is in
            section_type = _get_section_at_time(sections, phrase_start)

            quality = "good"
            if section_type in ["breakdown", "buildup"]:
                quality = "excellent"
            elif section_type == "drop":
                quality = "fair"  # Mixing in during drop is unusual

            mix_in_points.append({
                "time": phrase_start,
                "type": f"PHRASE_START_{section_type.upper()}",
                "quality": quality,
                "reason": f"Phrase boundary in {section_type}",
                "bar_count": phrase.get("bar_count", 16)
            })

    # 3. Breakdown starts are great mix-in points
    for section in sections:
        if section.get("type") == "breakdown":
            mix_in_points.append({
                "time": section.get("start", 0),
                "type": "BREAKDOWN_START",
                "quality": "excellent",
                "reason": "Breakdown - low energy, perfect for blending"
            })

    # === MIX OUT POINTS ===

    # 1. Outro is always a good mix-out point
    if outro:
        outro_start = outro.get("start", duration - 30)
        mix_out_points.append({
            "time": outro_start,
            "type": "OUTRO_START",
            "quality": "excellent",
            "reason": "Track outro - designed for mixing out"
        })

    # 2. After each drop (before the breakdown)
    prev_section = None
    for section in sections:
        if prev_section and prev_section.get("type") == "drop":
            mix_out_points.append({
                "time": section.get("start", 0),
                "type": "POST_DROP",
                "quality": "good",
                "reason": "After drop - natural exit point"
            })
        prev_section = section

    # 3. End of breakdowns (before buildup to next drop)
    for section in sections:
        if section.get("type") == "breakdown":
            breakdown_end = section.get("end", 0)
            mix_out_points.append({
                "time": breakdown_end,
                "type": "BREAKDOWN_END",
                "quality": "good",
                "reason": "End of breakdown - before energy returns"
            })

    # 4. Phrase boundaries in second half of track
    half_point = duration / 2
    for phrase in phrases:
        phrase_end = phrase.get("end_time", 0)
        if phrase_end > half_point:
            # Check for vocals
            has_vocal = any(
                v["start"] <= phrase_end < v["end"]
                for v in vocal_sections
                if v.get("intensity") == "FULL"
            )

            if not has_vocal:
                mix_out_points.append({
                    "time": phrase_end,
                    "type": "PHRASE_END",
                    "quality": "fair",
                    "reason": "Phrase boundary in second half"
                })

    # === CUE POINTS ===

    # Drop positions
    for section in sections:
        if section.get("type") == "drop":
            cue_points.append({
                "time": section.get("start", 0),
                "type": "DROP",
                "importance": "high"
            })

    # Breakdown positions
    for section in sections:
        if section.get("type") == "breakdown":
            cue_points.append({
                "time": section.get("start", 0),
                "type": "BREAKDOWN",
                "importance": "high"
            })

    # Buildup positions
    for section in sections:
        if section.get("type") == "buildup":
            cue_points.append({
                "time": section.get("start", 0),
                "type": "BUILDUP",
                "importance": "medium"
            })

    # Vocal entry points
    for vocal in vocal_sections:
        if vocal.get("intensity") == "FULL":
            cue_points.append({
                "time": vocal.get("start", 0),
                "type": "VOCAL_START",
                "importance": "medium"
            })

    # Sort and deduplicate
    mix_in_points = _deduplicate_points(mix_in_points, threshold=bar_duration)
    mix_out_points = _deduplicate_points(mix_out_points, threshold=bar_duration)
    cue_points = _deduplicate_points(cue_points, threshold=bar_duration * 2)

    # Sort by quality/time
    mix_in_points.sort(key=lambda x: ({"excellent": 0, "good": 1, "fair": 2}.get(x.get("quality", "fair"), 2), x["time"]))
    mix_out_points.sort(key=lambda x: ({"excellent": 0, "good": 1, "fair": 2}.get(x.get("quality", "fair"), 2), x["time"]))
    cue_points.sort(key=lambda x: x["time"])

    return {
        "best_mix_in_points": mix_in_points[:10],  # Top 10
        "best_mix_out_points": mix_out_points[:10],
        "cue_points": cue_points[:20],
        "recommended_mix_in": mix_in_points[0] if mix_in_points else None,
        "recommended_mix_out": mix_out_points[0] if mix_out_points else None
    }


def _get_section_at_time(sections: List[Dict], time: float) -> str:
    """Get the section type at a given time."""
    for section in sections:
        if section.get("start", 0) <= time < section.get("end", 0):
            return section.get("type", "main")
    return "main"


def _deduplicate_points(points: List[Dict], threshold: float) -> List[Dict]:
    """Remove points that are too close together, keeping the higher quality one."""
    if not points:
        return []

    # Sort by time
    sorted_points = sorted(points, key=lambda x: x["time"])
    result = [sorted_points[0]]

    quality_order = {"excellent": 0, "good": 1, "fair": 2, "high": 0, "medium": 1, "low": 2}

    for point in sorted_points[1:]:
        last = result[-1]
        if point["time"] - last["time"] < threshold:
            # Keep the better quality one
            point_quality = quality_order.get(point.get("quality") or point.get("importance", "fair"), 2)
            last_quality = quality_order.get(last.get("quality") or last.get("importance", "fair"), 2)

            if point_quality < last_quality:
                result[-1] = point
        else:
            result.append(point)

    return result


def get_optimal_transition_points(
    track_a_mix_points: Dict,
    track_b_mix_points: Dict,
    harmonic_score: int,
    bpm_diff_percent: float,
    set_phase: str
) -> Dict:
    """
    Get the optimal points for transitioning between two tracks.

    Args:
        track_a_mix_points: Mix points for outgoing track
        track_b_mix_points: Mix points for incoming track
        harmonic_score: Harmonic compatibility (0-100)
        bpm_diff_percent: BPM difference percentage
        set_phase: Current set phase (WARMUP, BUILD, PEAK, COOLDOWN)

    Returns:
        Dict with recommended exit point for A and entry point for B
    """
    # Get best mix out point from track A
    mix_out = track_a_mix_points.get("recommended_mix_out")
    if not mix_out:
        mix_out_points = track_a_mix_points.get("best_mix_out_points", [])
        mix_out = mix_out_points[0] if mix_out_points else {"time": 0, "type": "DEFAULT"}

    # Get best mix in point from track B
    mix_in = track_b_mix_points.get("recommended_mix_in")
    if not mix_in:
        mix_in_points = track_b_mix_points.get("best_mix_in_points", [])
        mix_in = mix_in_points[0] if mix_in_points else {"time": 0, "type": "DEFAULT"}

    # Determine transition style based on compatibility
    if harmonic_score < 50 or bpm_diff_percent > 6:
        transition_type = "HARD_CUT"
        transition_duration_bars = 0
    elif harmonic_score < 70:
        transition_type = "SHORT_BLEND"
        transition_duration_bars = 8
    elif set_phase in ["WARMUP", "COOLDOWN"]:
        transition_type = "LONG_BLEND"
        transition_duration_bars = 32
    else:
        transition_type = "MEDIUM_BLEND"
        transition_duration_bars = 16

    return {
        "track_a_exit": {
            "time": mix_out["time"],
            "type": mix_out["type"],
            "quality": mix_out.get("quality", "good")
        },
        "track_b_entry": {
            "time": mix_in["time"],
            "type": mix_in["type"],
            "quality": mix_in.get("quality", "good")
        },
        "recommended_transition": {
            "type": transition_type,
            "duration_bars": transition_duration_bars
        }
    }


def calculate_track_play_duration(
    mix_points: Dict,
    total_duration: float,
    set_phase: str,
    bpm: float
) -> Dict:
    """
    Calculate how much of a track should be played.

    Args:
        mix_points: Mix points for the track
        total_duration: Total track duration
        set_phase: Current set phase
        bpm: Track tempo

    Returns:
        Dict with recommended play start, end, and percentage
    """
    bar_duration = (60.0 / bpm) * 4

    # Default entry/exit points
    mix_in = mix_points.get("recommended_mix_in", {})
    mix_out = mix_points.get("recommended_mix_out", {})

    entry_time = mix_in.get("time", 0)
    exit_time = mix_out.get("time", total_duration)

    # Adjust based on set phase
    phase_multipliers = {
        "WARMUP": 0.85,    # Play more of the track
        "BUILD": 0.70,     # Medium
        "PEAK": 0.55,      # Faster turnover
        "COOLDOWN": 0.85   # Longer, relaxed
    }

    multiplier = phase_multipliers.get(set_phase, 0.70)

    # Calculate play duration
    available_duration = exit_time - entry_time
    target_duration = total_duration * multiplier

    # Ensure we play at least some minimum
    min_duration = bar_duration * 16  # At least 16 bars
    play_duration = max(min_duration, min(available_duration, target_duration))

    # Adjust exit time based on calculated duration
    actual_exit = entry_time + play_duration
    if actual_exit > exit_time:
        actual_exit = exit_time

    percentage = (actual_exit - entry_time) / total_duration * 100

    return {
        "play_from": entry_time,
        "play_until": actual_exit,
        "duration_seconds": actual_exit - entry_time,
        "duration_bars": int((actual_exit - entry_time) / bar_duration),
        "percentage_played": round(percentage, 1)
    }
