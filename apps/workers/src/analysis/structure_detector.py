"""
Enhanced Structure Detection Module.

Detects detailed song structure sections:
- INTRO: Minimal elements, designed for mixing in
- VERSE: Progressive energy building
- BUILDUP: Rising tension, anticipation before drop
- DROP: Peak energy, all elements present
- BREAKDOWN: Breathing room, elements removed
- OUTRO: Elements removed progressively, designed for mixing out

Uses Demucs stems for per-stem energy analysis.
"""

import numpy as np
import librosa
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class SectionType(Enum):
    """Types of track sections."""
    INTRO = "INTRO"
    VERSE = "VERSE"
    BUILDUP = "BUILDUP"
    DROP = "DROP"
    BREAKDOWN = "BREAKDOWN"
    OUTRO = "OUTRO"
    MAIN = "MAIN"  # Generic section


@dataclass
class SectionCharacteristics:
    """Characteristics for each section type."""
    typical_bars: tuple  # (min, max)
    energy: str
    has_full_drums: bool | str
    has_bass: bool | str
    description: str


# Section characteristics reference
SECTION_CHARACTERISTICS = {
    SectionType.INTRO: SectionCharacteristics(
        typical_bars=(16, 32),
        energy="low",
        has_full_drums=False,
        has_bass=False,
        description="Minimal elements, designed for mixing in"
    ),
    SectionType.VERSE: SectionCharacteristics(
        typical_bars=(16, 32),
        energy="medium-low",
        has_full_drums=True,
        has_bass=True,
        description="Progressive energy building"
    ),
    SectionType.BUILDUP: SectionCharacteristics(
        typical_bars=(8, 16),
        energy="rising",
        has_full_drums="building",
        has_bass="filtered/rising",
        description="Tension building, anticipation"
    ),
    SectionType.DROP: SectionCharacteristics(
        typical_bars=(16, 32),
        energy="maximum",
        has_full_drums=True,
        has_bass=True,
        description="Peak energy, all elements"
    ),
    SectionType.BREAKDOWN: SectionCharacteristics(
        typical_bars=(8, 16),
        energy="low",
        has_full_drums=False,
        has_bass=False,
        description="Breathing room, emotional moment"
    ),
    SectionType.OUTRO: SectionCharacteristics(
        typical_bars=(16, 32),
        energy="decreasing",
        has_full_drums="decreasing",
        has_bass="decreasing",
        description="Elements removed, designed for mixing out"
    ),
}


def detect_detailed_structure(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    beats: List[float],
    stems: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """
    Detect detailed song structure with section types.

    Args:
        audio: Audio signal
        sr: Sample rate
        bpm: Tempo
        beats: Beat timestamps
        stems: Optional Demucs stems {drums, bass, vocals, other}

    Returns:
        Detailed structure with typed sections
    """
    duration = len(audio) / sr
    bar_duration = (60.0 / bpm) * 4
    bars_per_8 = 8 * bar_duration

    # Calculate energy profiles
    if stems:
        energy_profiles = _calculate_stem_energies(stems, sr, bars_per_8)
    else:
        energy_profiles = _calculate_basic_energy(audio, sr, bars_per_8)

    # Get segment boundaries
    segment_times = _get_segment_times(energy_profiles, bars_per_8, duration, beats)

    # Classify each segment
    sections = []
    for i in range(len(segment_times) - 1):
        start = segment_times[i]
        end = segment_times[i + 1]

        # Get energy values for this segment
        segment_idx = int(start / bars_per_8)
        segment_energy = _get_segment_energy(energy_profiles, segment_idx, len(segment_times) - 1)

        # Classify section type
        section_type = _classify_section(
            segment_energy,
            i,
            len(segment_times) - 1,
            start,
            end,
            duration
        )

        sections.append({
            "start_time": round(start, 2),
            "end_time": round(end, 2),
            "type": section_type.value,
            "duration_bars": int((end - start) / bar_duration),
            "energy": segment_energy,
        })

    # Identify intro and outro
    intro = _find_intro(sections, bar_duration)
    outro = _find_outro(sections, bar_duration, duration)

    # Find drops and breakdowns
    drops = [s for s in sections if s["type"] == SectionType.DROP.value]
    breakdowns = [s for s in sections if s["type"] == SectionType.BREAKDOWN.value]
    buildups = [s for s in sections if s["type"] == SectionType.BUILDUP.value]

    return {
        "intro": intro,
        "outro": outro,
        "sections": sections,
        "drops": drops,
        "breakdowns": breakdowns,
        "buildups": buildups,
        "total_bars": int(duration / bar_duration),
        "analysis_confidence": 0.85 if stems else 0.70
    }


def _calculate_stem_energies(
    stems: Dict[str, np.ndarray],
    sr: int,
    segment_duration: float
) -> Dict[str, np.ndarray]:
    """
    Calculate energy profiles for each stem.
    """
    profiles = {}

    for stem_name, stem_audio in stems.items():
        if stem_audio is None or len(stem_audio) == 0:
            continue

        # Calculate RMS energy
        rms = librosa.feature.rms(y=stem_audio, frame_length=2048, hop_length=512)[0]

        # Segment into chunks
        frames_per_segment = int(segment_duration * sr / 512)
        num_segments = len(rms) // frames_per_segment + 1

        segment_energies = []
        for i in range(num_segments):
            start_frame = i * frames_per_segment
            end_frame = min((i + 1) * frames_per_segment, len(rms))
            if start_frame < end_frame:
                segment_energies.append(np.mean(rms[start_frame:end_frame]))

        profiles[stem_name] = np.array(segment_energies)

    # Normalize each profile
    for stem_name in profiles:
        max_val = np.max(profiles[stem_name])
        if max_val > 0:
            profiles[stem_name] = profiles[stem_name] / max_val

    # Calculate combined energy
    if profiles:
        combined = np.zeros(len(list(profiles.values())[0]))
        for energy in profiles.values():
            if len(energy) == len(combined):
                combined += energy
        profiles["combined"] = combined / len(profiles)

    return profiles


def _calculate_basic_energy(
    audio: np.ndarray,
    sr: int,
    segment_duration: float
) -> Dict[str, np.ndarray]:
    """
    Calculate basic energy profile without stems.
    """
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]

    frames_per_segment = int(segment_duration * sr / 512)
    num_segments = len(rms) // frames_per_segment + 1

    segment_energies = []
    for i in range(num_segments):
        start_frame = i * frames_per_segment
        end_frame = min((i + 1) * frames_per_segment, len(rms))
        if start_frame < end_frame:
            segment_energies.append(np.mean(rms[start_frame:end_frame]))

    energies = np.array(segment_energies)
    max_val = np.max(energies) if len(energies) > 0 else 1
    if max_val > 0:
        energies = energies / max_val

    return {"combined": energies}


def _get_segment_times(
    energy_profiles: Dict[str, np.ndarray],
    segment_duration: float,
    duration: float,
    beats: List[float]
) -> List[float]:
    """
    Get segment boundary times based on energy changes.
    """
    combined = energy_profiles.get("combined", np.array([]))

    if len(combined) < 2:
        # Fallback to regular intervals
        return list(np.arange(0, duration, segment_duration))

    # Calculate energy differences
    energy_diff = np.abs(np.diff(combined))

    # Find significant changes
    threshold = np.mean(energy_diff) + np.std(energy_diff) * 0.5
    change_indices = np.where(energy_diff > threshold)[0]

    # Convert to times
    times = [0.0]
    for idx in change_indices:
        time = (idx + 1) * segment_duration
        # Snap to nearest bar
        if beats:
            time = _snap_to_bar(time, beats)
        times.append(time)

    # Ensure we have the end
    if times[-1] < duration - segment_duration / 2:
        times.append(duration)

    # Remove duplicates and sort
    times = sorted(set(times))

    return times


def _snap_to_bar(time: float, beats: List[float], beats_per_bar: int = 4) -> float:
    """Snap time to nearest bar boundary."""
    if not beats or len(beats) < beats_per_bar:
        return time

    bar_beats = beats[::beats_per_bar]
    bars_array = np.array(bar_beats)
    idx = np.argmin(np.abs(bars_array - time))
    return float(bars_array[idx])


def _get_segment_energy(
    energy_profiles: Dict[str, np.ndarray],
    segment_idx: int,
    num_segments: int
) -> Dict[str, float]:
    """
    Get energy values for a segment.
    """
    result = {}

    for stem_name, energies in energy_profiles.items():
        if segment_idx < len(energies):
            result[stem_name] = float(energies[segment_idx])
        else:
            result[stem_name] = 0.0

    return result


def _classify_section(
    energy: Dict[str, float],
    segment_index: int,
    total_segments: int,
    start_time: float,
    end_time: float,
    duration: float
) -> SectionType:
    """
    Classify a segment into a section type.
    """
    combined_energy = energy.get("combined", 0.5)
    drums_energy = energy.get("drums", combined_energy)
    bass_energy = energy.get("bass", combined_energy)

    # Position-based classification
    relative_position = start_time / duration

    # First section is likely intro
    if segment_index == 0 and combined_energy < 0.4:
        return SectionType.INTRO

    # Last section is likely outro
    if segment_index == total_segments - 1 and combined_energy < 0.5:
        return SectionType.OUTRO

    # Near the end with decreasing energy
    if relative_position > 0.85 and combined_energy < 0.5:
        return SectionType.OUTRO

    # Energy-based classification

    # DROP: High energy in all elements
    if combined_energy > 0.8 and drums_energy > 0.7 and bass_energy > 0.7:
        return SectionType.DROP

    # BREAKDOWN: Low energy, especially in drums and bass
    if combined_energy < 0.4 and drums_energy < 0.3 and bass_energy < 0.3:
        return SectionType.BREAKDOWN

    # BUILDUP: Medium energy with rising pattern
    # (Would need next segment energy to properly detect rising)
    if 0.4 <= combined_energy <= 0.7 and drums_energy < 0.5:
        return SectionType.BUILDUP

    # VERSE: Medium-low energy with drums and bass present
    if 0.3 <= combined_energy <= 0.6:
        return SectionType.VERSE

    # Default to MAIN
    return SectionType.MAIN


def _find_intro(sections: List[Dict], bar_duration: float) -> Dict:
    """
    Find and return the intro section.
    """
    for section in sections:
        if section["type"] == SectionType.INTRO.value:
            return {
                "start": section["start_time"],
                "end": section["end_time"],
                "duration_bars": section["duration_bars"]
            }

    # Fallback: first section or first 16 bars
    if sections:
        return {
            "start": 0,
            "end": sections[0]["end_time"],
            "duration_bars": sections[0]["duration_bars"]
        }

    return {
        "start": 0,
        "end": 16 * bar_duration,
        "duration_bars": 16
    }


def _find_outro(sections: List[Dict], bar_duration: float, duration: float) -> Dict:
    """
    Find and return the outro section.
    """
    for section in reversed(sections):
        if section["type"] == SectionType.OUTRO.value:
            return {
                "start": section["start_time"],
                "end": section["end_time"],
                "duration_bars": section["duration_bars"]
            }

    # Fallback: last section or last 16 bars
    if sections:
        return {
            "start": sections[-1]["start_time"],
            "end": duration,
            "duration_bars": sections[-1]["duration_bars"]
        }

    return {
        "start": max(0, duration - 16 * bar_duration),
        "end": duration,
        "duration_bars": 16
    }


def get_mixable_sections(structure: Dict) -> List[Dict]:
    """
    Get sections suitable for mixing (intro, breakdown, outro).
    """
    mixable = []

    # Intro is always mixable
    if structure.get("intro"):
        intro = structure["intro"]
        mixable.append({
            "type": "INTRO",
            "start": intro.get("start", 0),
            "end": intro.get("end", 0),
            "quality": "excellent"
        })

    # Breakdowns are great for mixing
    for breakdown in structure.get("breakdowns", []):
        mixable.append({
            "type": "BREAKDOWN",
            "start": breakdown.get("start_time", 0),
            "end": breakdown.get("end_time", 0),
            "quality": "excellent"
        })

    # Outro is always mixable
    if structure.get("outro"):
        outro = structure["outro"]
        mixable.append({
            "type": "OUTRO",
            "start": outro.get("start", 0),
            "end": outro.get("end", 0),
            "quality": "excellent"
        })

    return mixable
