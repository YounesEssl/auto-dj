"""
Camelot Wheel - Complete harmonic mixing system.

The Camelot Wheel is Mark Davis's (Mixed In Key) system for organizing
the 24 musical keys in a circle for easy harmonic mixing.

Outer circle (B) = MAJOR keys (bright, energetic sound)
Inner circle (A) = MINOR keys (dark, melancholic sound)

Adjacent keys on the wheel are harmonically compatible.
"""

from typing import Optional

# Complete Camelot Wheel mapping
CAMELOT_WHEEL = {
    # Minor keys (A) - inner circle
    "1A": {"musical_key": "Abm", "enharmonic": "G#m", "relative_major": "1B"},
    "2A": {"musical_key": "Ebm", "enharmonic": "D#m", "relative_major": "2B"},
    "3A": {"musical_key": "Bbm", "enharmonic": "A#m", "relative_major": "3B"},
    "4A": {"musical_key": "Fm", "enharmonic": None, "relative_major": "4B"},
    "5A": {"musical_key": "Cm", "enharmonic": None, "relative_major": "5B"},
    "6A": {"musical_key": "Gm", "enharmonic": None, "relative_major": "6B"},
    "7A": {"musical_key": "Dm", "enharmonic": None, "relative_major": "7B"},
    "8A": {"musical_key": "Am", "enharmonic": None, "relative_major": "8B"},
    "9A": {"musical_key": "Em", "enharmonic": None, "relative_major": "9B"},
    "10A": {"musical_key": "Bm", "enharmonic": None, "relative_major": "10B"},
    "11A": {"musical_key": "F#m", "enharmonic": "Gbm", "relative_major": "11B"},
    "12A": {"musical_key": "C#m", "enharmonic": "Dbm", "relative_major": "12B"},
    # Major keys (B) - outer circle
    "1B": {"musical_key": "B", "enharmonic": "Cb", "relative_minor": "1A"},
    "2B": {"musical_key": "F#", "enharmonic": "Gb", "relative_minor": "2A"},
    "3B": {"musical_key": "Db", "enharmonic": "C#", "relative_minor": "3A"},
    "4B": {"musical_key": "Ab", "enharmonic": "G#", "relative_minor": "4A"},
    "5B": {"musical_key": "Eb", "enharmonic": "D#", "relative_minor": "5A"},
    "6B": {"musical_key": "Bb", "enharmonic": "A#", "relative_minor": "6A"},
    "7B": {"musical_key": "F", "enharmonic": None, "relative_minor": "7A"},
    "8B": {"musical_key": "C", "enharmonic": None, "relative_minor": "8A"},
    "9B": {"musical_key": "G", "enharmonic": None, "relative_minor": "9A"},
    "10B": {"musical_key": "D", "enharmonic": None, "relative_minor": "10A"},
    "11B": {"musical_key": "A", "enharmonic": None, "relative_minor": "11A"},
    "12B": {"musical_key": "E", "enharmonic": None, "relative_minor": "12A"},
}

# Reverse mapping: musical key to Camelot
_KEY_TO_CAMELOT = {}
for camelot, data in CAMELOT_WHEEL.items():
    _KEY_TO_CAMELOT[data["musical_key"].lower()] = camelot
    if data["enharmonic"]:
        _KEY_TO_CAMELOT[data["enharmonic"].lower()] = camelot

# Add common variations
_KEY_ALIASES = {
    # Flats
    "ab minor": "1A", "g# minor": "1A", "abm": "1A", "g#m": "1A",
    "eb minor": "2A", "d# minor": "2A", "ebm": "2A", "d#m": "2A",
    "bb minor": "3A", "a# minor": "3A", "bbm": "3A", "a#m": "3A",
    "f minor": "4A", "fm": "4A",
    "c minor": "5A", "cm": "5A",
    "g minor": "6A", "gm": "6A",
    "d minor": "7A", "dm": "7A",
    "a minor": "8A", "am": "8A",
    "e minor": "9A", "em": "9A",
    "b minor": "10A", "bm": "10A",
    "f# minor": "11A", "gb minor": "11A", "f#m": "11A", "gbm": "11A",
    "c# minor": "12A", "db minor": "12A", "c#m": "12A", "dbm": "12A",
    # Majors
    "b major": "1B", "cb major": "1B",
    "f# major": "2B", "gb major": "2B",
    "db major": "3B", "c# major": "3B",
    "ab major": "4B", "g# major": "4B",
    "eb major": "5B", "d# major": "5B",
    "bb major": "6B", "a# major": "6B",
    "f major": "7B",
    "c major": "8B",
    "g major": "9B",
    "d major": "10B",
    "a major": "11B",
    "e major": "12B",
}
_KEY_TO_CAMELOT.update(_KEY_ALIASES)


def get_camelot_from_key(key: str) -> Optional[str]:
    """
    Convert a musical key to Camelot notation.

    Args:
        key: Musical key string (e.g., "Am", "C major", "F#m")

    Returns:
        Camelot notation (e.g., "8A") or None if not found
    """
    if not key:
        return None

    # Check if already Camelot format
    key_upper = key.upper()
    if key_upper in CAMELOT_WHEEL:
        return key_upper

    # Normalize and lookup
    key_lower = key.lower().strip()
    return _KEY_TO_CAMELOT.get(key_lower)


def get_key_from_camelot(camelot: str) -> Optional[str]:
    """
    Convert Camelot notation to musical key.

    Args:
        camelot: Camelot notation (e.g., "8A")

    Returns:
        Musical key string (e.g., "Am") or None if invalid
    """
    if not camelot:
        return None

    camelot_upper = camelot.upper()
    if camelot_upper in CAMELOT_WHEEL:
        return CAMELOT_WHEEL[camelot_upper]["musical_key"]
    return None


def get_relative_key(camelot: str) -> Optional[str]:
    """
    Get the relative major/minor key.

    Args:
        camelot: Camelot notation (e.g., "8A")

    Returns:
        Relative key in Camelot notation (e.g., "8B")
    """
    if not camelot:
        return None

    camelot_upper = camelot.upper()
    if camelot_upper not in CAMELOT_WHEEL:
        return None

    data = CAMELOT_WHEEL[camelot_upper]
    return data.get("relative_major") or data.get("relative_minor")


def get_compatible_keys(camelot: str) -> list[dict]:
    """
    Get all harmonically compatible keys for mixing.

    Args:
        camelot: Camelot notation (e.g., "8A")

    Returns:
        List of compatible keys with their compatibility scores
    """
    if not camelot:
        return []

    camelot_upper = camelot.upper()
    if camelot_upper not in CAMELOT_WHEEL:
        return []

    num = int(camelot_upper[:-1])
    mode = camelot_upper[-1]

    compatible = []

    # Same key (100)
    compatible.append({
        "camelot": camelot_upper,
        "score": 100,
        "type": "PERFECT",
        "description": "Same key"
    })

    # Adjacent +1 (95)
    next_num = (num % 12) + 1
    next_key = f"{next_num}{mode}"
    compatible.append({
        "camelot": next_key,
        "score": 95,
        "type": "ADJACENT",
        "description": "Adjacent +1"
    })

    # Adjacent -1 (95)
    prev_num = ((num - 2) % 12) + 1
    prev_key = f"{prev_num}{mode}"
    compatible.append({
        "camelot": prev_key,
        "score": 95,
        "type": "ADJACENT",
        "description": "Adjacent -1"
    })

    # Relative major/minor (90)
    other_mode = "B" if mode == "A" else "A"
    relative_key = f"{num}{other_mode}"
    compatible.append({
        "camelot": relative_key,
        "score": 90,
        "type": "RELATIVE",
        "description": "Relative major/minor"
    })

    # Diagonal adjacent +1 with mode change (80)
    diagonal_next = f"{next_num}{other_mode}"
    compatible.append({
        "camelot": diagonal_next,
        "score": 80,
        "type": "DIAGONAL",
        "description": "Diagonal +1"
    })

    # Diagonal adjacent -1 with mode change (80)
    diagonal_prev = f"{prev_num}{other_mode}"
    compatible.append({
        "camelot": diagonal_prev,
        "score": 80,
        "type": "DIAGONAL",
        "description": "Diagonal -1"
    })

    return compatible


def calculate_harmonic_compatibility(key_a: str, key_b: str) -> dict:
    """
    Calculate the harmonic compatibility between two keys.

    COMPATIBILITY RULES (Camelot Wheel):

    | Movement            | Score | Description                              | Example      |
    |---------------------|-------|------------------------------------------|--------------|
    | Same key            | 100   | Perfect, no tension                      | 8A -> 8A     |
    | +1 or -1            | 95    | Adjacent, very harmonious                | 8A -> 9A, 7A |
    | Major <-> Minor     | 90    | Relative, subtle mood change             | 8A -> 8B     |
    | +1/-1 + mode change | 80    | Diagonal adjacent                        | 8A -> 9B, 7B |
    | +2 or -2            | 70    | Energy boost/drop, use with care         | 8A -> 10A    |
    | +7 (dominant)       | 75    | Classic resolution movement              | 8A -> 3A     |
    | +5 (subdominant)    | 70    | Inverse of dominant                      | 8A -> 1A     |
    | Other               | <50   | INCOMPATIBLE - avoid long blends         |              |

    Args:
        key_a: First key (Camelot or musical notation)
        key_b: Second key (Camelot or musical notation)

    Returns:
        dict with score (0-100), type, and description
    """
    # Convert to Camelot if needed
    camelot_a = get_camelot_from_key(key_a) if key_a else None
    camelot_b = get_camelot_from_key(key_b) if key_b else None

    if not camelot_a or not camelot_b:
        return {
            "score": 50,
            "type": "UNKNOWN",
            "description": "Could not determine one or both keys"
        }

    # Parse Camelot notation
    num_a = int(camelot_a[:-1])
    mode_a = camelot_a[-1]
    num_b = int(camelot_b[:-1])
    mode_b = camelot_b[-1]

    # Calculate circular distance (0-6, since wheel is circular with 12 positions)
    raw_distance = abs(num_a - num_b)
    distance = min(raw_distance, 12 - raw_distance)
    same_mode = mode_a == mode_b

    # Same key
    if camelot_a == camelot_b:
        return {
            "score": 100,
            "type": "PERFECT",
            "description": "Same key - perfect match"
        }

    # Adjacent +/-1, same mode
    if distance == 1 and same_mode:
        return {
            "score": 95,
            "type": "ADJACENT",
            "description": "Adjacent key - very harmonious"
        }

    # Relative major/minor (same number, different mode)
    if num_a == num_b and not same_mode:
        return {
            "score": 90,
            "type": "RELATIVE",
            "description": "Relative major/minor - subtle mood change"
        }

    # Diagonal adjacent (+/-1 + mode change)
    if distance == 1 and not same_mode:
        return {
            "score": 80,
            "type": "DIAGONAL",
            "description": "Diagonal adjacent - creative transition"
        }

    # +7 (dominant) - distance of 7 on the circle, same mode
    # On a 12-position circle, +7 = -5
    if distance == 7 and same_mode:
        return {
            "score": 75,
            "type": "DOMINANT",
            "description": "Dominant resolution - classic movement"
        }

    # +/-2, same mode
    if distance == 2 and same_mode:
        return {
            "score": 70,
            "type": "ENERGY_SHIFT",
            "description": "Energy boost/drop - use with care"
        }

    # +5 (subdominant)
    if distance == 5 and same_mode:
        return {
            "score": 70,
            "type": "SUBDOMINANT",
            "description": "Subdominant - inverse of dominant"
        }

    # +/-2 with mode change
    if distance == 2 and not same_mode:
        return {
            "score": 60,
            "type": "DISTANT_DIAGONAL",
            "description": "Distant diagonal - risky blend"
        }

    # +/-3, same mode
    if distance == 3 and same_mode:
        return {
            "score": 50,
            "type": "DISTANT",
            "description": "Distant - short transition only"
        }

    # Everything else is incompatible
    return {
        "score": 30,
        "type": "INCOMPATIBLE",
        "description": "Harmonic clash likely - use hard cut"
    }


def is_blend_safe(key_a: str, key_b: str) -> bool:
    """
    Quick check if a long blend is safe between two keys.

    Args:
        key_a: First key
        key_b: Second key

    Returns:
        True if score >= 70 (safe for blending)
    """
    result = calculate_harmonic_compatibility(key_a, key_b)
    return result["score"] >= 70


def requires_hard_cut(key_a: str, key_b: str) -> bool:
    """
    Check if a hard cut is required due to harmonic incompatibility.

    Args:
        key_a: First key
        key_b: Second key

    Returns:
        True if score < 50 (hard cut required)
    """
    result = calculate_harmonic_compatibility(key_a, key_b)
    return result["score"] < 50
