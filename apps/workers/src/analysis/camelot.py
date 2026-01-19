"""
Camelot Wheel conversion module

Converts musical keys to Camelot notation for harmonic mixing.
"""

from typing import Dict

# Mapping from musical key to Camelot notation
KEY_TO_CAMELOT: Dict[str, str] = {
    # Major keys (B column)
    "C": "8B",
    "G": "9B",
    "D": "10B",
    "A": "11B",
    "E": "12B",
    "B": "1B",
    "F#": "2B",
    "Gb": "2B",
    "Db": "3B",
    "C#": "3B",
    "Ab": "4B",
    "G#": "4B",
    "Eb": "5B",
    "D#": "5B",
    "Bb": "6B",
    "A#": "6B",
    "F": "7B",
    # Minor keys (A column)
    "Am": "8A",
    "Em": "9A",
    "Bm": "10A",
    "F#m": "11A",
    "Gbm": "11A",
    "C#m": "12A",
    "Dbm": "12A",
    "G#m": "1A",
    "Abm": "1A",
    "D#m": "2A",
    "Ebm": "2A",
    "A#m": "3A",
    "Bbm": "3A",
    "Fm": "4A",
    "Cm": "5A",
    "Gm": "6A",
    "Dm": "7A",
}

# Reverse mapping for getting key from Camelot
CAMELOT_TO_KEY: Dict[str, str] = {v: k for k, v in KEY_TO_CAMELOT.items()}


def key_to_camelot(key: str) -> str:
    """
    Convert a musical key to Camelot notation.

    Args:
        key: Musical key (e.g., "Am", "C", "F#m")

    Returns:
        Camelot notation (e.g., "8A", "8B", "11A")
    """
    # Normalize key format
    key = key.strip()

    # Direct lookup
    if key in KEY_TO_CAMELOT:
        return KEY_TO_CAMELOT[key]

    # Try with different capitalization
    key_upper = key[0].upper() + key[1:].lower()
    if key_upper in KEY_TO_CAMELOT:
        return KEY_TO_CAMELOT[key_upper]

    # Default fallback
    return "8A"


def camelot_to_key(camelot: str) -> str:
    """
    Convert Camelot notation to musical key.

    Args:
        camelot: Camelot notation (e.g., "8A", "8B")

    Returns:
        Musical key (e.g., "Am", "C")
    """
    camelot = camelot.upper()
    return CAMELOT_TO_KEY.get(camelot, "Am")


def get_compatible_camelots(camelot: str) -> list[str]:
    """
    Get compatible Camelot keys for harmonic mixing.

    Compatible keys are:
    - Same key (perfect match)
    - +1 or -1 on the wheel (energy change)
    - Relative major/minor (same number, different letter)

    Args:
        camelot: Camelot notation (e.g., "8A")

    Returns:
        List of compatible Camelot notations
    """
    camelot = camelot.upper()

    try:
        number = int(camelot[:-1])
        letter = camelot[-1]
    except (ValueError, IndexError):
        return [camelot]

    compatible = [camelot]

    # +1 and -1 on the wheel
    next_num = number + 1 if number < 12 else 1
    prev_num = number - 1 if number > 1 else 12
    compatible.append(f"{next_num}{letter}")
    compatible.append(f"{prev_num}{letter}")

    # Relative major/minor
    other_letter = "B" if letter == "A" else "A"
    compatible.append(f"{number}{other_letter}")

    return compatible
