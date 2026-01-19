"""
Theory module for music theory utilities.

Contains:
- Camelot wheel for harmonic mixing
- BPM reference by genre
"""

from .camelot import (
    CAMELOT_WHEEL,
    calculate_harmonic_compatibility,
    get_camelot_from_key,
    get_key_from_camelot,
    get_compatible_keys,
    get_relative_key,
)

from .bpm_reference import (
    BPM_REFERENCE,
    detect_genre_from_bpm,
    get_transition_style_for_genre,
)

__all__ = [
    "CAMELOT_WHEEL",
    "calculate_harmonic_compatibility",
    "get_camelot_from_key",
    "get_key_from_camelot",
    "get_compatible_keys",
    "get_relative_key",
    "BPM_REFERENCE",
    "detect_genre_from_bpm",
    "get_transition_style_for_genre",
]
