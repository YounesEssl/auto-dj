"""
Camelot wheel compatibility rules for harmonic mixing
"""

from typing import Tuple


def calculate_compatibility_score(
    camelot1: str,
    camelot2: str
) -> float:
    """
    Calculate harmonic compatibility between two Camelot keys.

    Scoring:
    - Perfect match (same key): 1.0
    - Adjacent on wheel (+1 or -1): 0.9
    - Relative major/minor: 0.85
    - Diagonal (+1 with mode change): 0.7
    - Two steps away: 0.5
    - Far away: 0.2

    Args:
        camelot1: First Camelot notation (e.g., "8A")
        camelot2: Second Camelot notation (e.g., "9A")

    Returns:
        Compatibility score from 0 to 1
    """
    try:
        num1, letter1 = _parse_camelot(camelot1)
        num2, letter2 = _parse_camelot(camelot2)
    except ValueError:
        return 0.5  # Default for invalid keys

    # Calculate wheel distance (1-12 circular)
    distance = min(
        abs(num1 - num2),
        12 - abs(num1 - num2)
    )

    same_mode = letter1 == letter2

    # Perfect match
    if distance == 0 and same_mode:
        return 1.0

    # Relative major/minor (same number, different letter)
    if distance == 0 and not same_mode:
        return 0.85

    # Adjacent on wheel, same mode
    if distance == 1 and same_mode:
        return 0.9

    # Adjacent with mode change (diagonal)
    if distance == 1 and not same_mode:
        return 0.7

    # Two steps away
    if distance == 2:
        return 0.5 if same_mode else 0.4

    # Three steps away
    if distance == 3:
        return 0.3

    # Far away
    return 0.2


def _parse_camelot(camelot: str) -> Tuple[int, str]:
    """
    Parse Camelot notation into number and letter.

    Args:
        camelot: Camelot notation (e.g., "8A", "12B")

    Returns:
        Tuple of (number, letter)

    Raises:
        ValueError: If notation is invalid
    """
    camelot = camelot.upper().strip()

    if len(camelot) < 2:
        raise ValueError(f"Invalid Camelot notation: {camelot}")

    letter = camelot[-1]
    if letter not in ("A", "B"):
        raise ValueError(f"Invalid Camelot letter: {letter}")

    try:
        number = int(camelot[:-1])
        if not 1 <= number <= 12:
            raise ValueError(f"Invalid Camelot number: {number}")
    except ValueError:
        raise ValueError(f"Invalid Camelot notation: {camelot}")

    return number, letter
