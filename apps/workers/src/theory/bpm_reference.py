"""
BPM Reference by Genre.

Typical BPM ranges for electronic music genres.
Useful for:
- Adapting transition duration
- Understanding energy context
- Automatic genre detection
"""

from typing import Optional

# BPM ranges by genre with transition style recommendations
BPM_REFERENCE = {
    # House variants
    "deep_house": {
        "min": 120,
        "max": 125,
        "typical": 122,
        "energy": "low",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Deep, melodic, warm"
    },
    "chicago_house": {
        "min": 120,
        "max": 128,
        "typical": 124,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Classic, soulful, vocal-driven"
    },
    "tech_house": {
        "min": 125,
        "max": 130,
        "typical": 127,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Groovy, percussive, minimal vocals"
    },
    "progressive_house": {
        "min": 125,
        "max": 130,
        "typical": 128,
        "energy": "building",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Melodic buildups, emotional drops"
    },
    "electro_house": {
        "min": 128,
        "max": 132,
        "typical": 130,
        "energy": "high",
        "transition_style": "blend_or_cut",
        "transition_bars": (8, 16),
        "description": "Big synths, heavy drops"
    },
    "bass_house": {
        "min": 125,
        "max": 130,
        "typical": 128,
        "energy": "high",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Heavy bass, UK garage influenced"
    },
    "hard_house": {
        "min": 145,
        "max": 150,
        "typical": 148,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Fast, aggressive, hard kicks"
    },
    "future_house": {
        "min": 125,
        "max": 128,
        "typical": 126,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Metallic leads, bouncy bass"
    },
    "afro_house": {
        "min": 120,
        "max": 125,
        "typical": 122,
        "energy": "medium",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Organic percussion, tribal elements"
    },

    # Techno variants
    "minimal_techno": {
        "min": 125,
        "max": 135,
        "typical": 130,
        "energy": "medium",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Stripped down, hypnotic, subtle changes"
    },
    "detroit_techno": {
        "min": 125,
        "max": 135,
        "typical": 130,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Futuristic, soulful, melodic elements"
    },
    "berlin_techno": {
        "min": 130,
        "max": 140,
        "typical": 135,
        "energy": "high",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Dark, industrial, relentless"
    },
    "acid_techno": {
        "min": 130,
        "max": 145,
        "typical": 138,
        "energy": "high",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "303 basslines, squelchy, psychedelic"
    },
    "hard_techno": {
        "min": 145,
        "max": 160,
        "typical": 150,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Aggressive, distorted, fast"
    },
    "industrial_techno": {
        "min": 130,
        "max": 145,
        "typical": 138,
        "energy": "high",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Harsh textures, mechanical, dark"
    },
    "melodic_techno": {
        "min": 125,
        "max": 132,
        "typical": 128,
        "energy": "building",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Emotional, atmospheric, progressive"
    },

    # Trance variants
    "trance": {
        "min": 130,
        "max": 145,
        "typical": 138,
        "energy": "building",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Uplifting, melodic, emotional buildups"
    },
    "psytrance": {
        "min": 140,
        "max": 150,
        "typical": 145,
        "energy": "very_high",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Psychedelic, rolling basslines, trippy"
    },
    "progressive_trance": {
        "min": 128,
        "max": 136,
        "typical": 132,
        "energy": "building",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Deep, atmospheric, slow builds"
    },
    "hard_trance": {
        "min": 140,
        "max": 150,
        "typical": 145,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (8, 16),
        "description": "Hard kicks, big leads, high energy"
    },

    # Bass music
    "dubstep": {
        "min": 140,
        "max": 150,
        "typical": 140,
        "energy": "high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Half-time feel, heavy wobbles, drops",
        "note": "Half-time feel at 70 BPM"
    },
    "drum_and_bass": {
        "min": 170,
        "max": 180,
        "typical": 174,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Fast breaks, rolling basslines"
    },
    "jungle": {
        "min": 160,
        "max": 180,
        "typical": 170,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Chopped breaks, reggae influence"
    },
    "breakbeat": {
        "min": 120,
        "max": 140,
        "typical": 130,
        "energy": "medium",
        "transition_style": "cut",
        "transition_bars": (8, 16),
        "description": "Broken beats, funk influenced"
    },
    "uk_garage": {
        "min": 130,
        "max": 140,
        "typical": 134,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "2-step rhythms, shuffled beats, vocals"
    },

    # Hard dance
    "hardcore": {
        "min": 160,
        "max": 200,
        "typical": 175,
        "energy": "extreme",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Extremely fast, distorted kicks"
    },
    "hardstyle": {
        "min": 150,
        "max": 160,
        "typical": 155,
        "energy": "very_high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Reverse bass, hard kicks, euphoric leads"
    },
    "gabber": {
        "min": 160,
        "max": 190,
        "typical": 180,
        "energy": "extreme",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Ultra fast, distorted kicks, aggressive"
    },

    # Other electronic
    "disco": {
        "min": 110,
        "max": 130,
        "typical": 120,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Funky, four-on-the-floor, strings"
    },
    "nu_disco": {
        "min": 115,
        "max": 125,
        "typical": 120,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "Modern disco, filter house influence"
    },
    "synthwave": {
        "min": 100,
        "max": 120,
        "typical": 110,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (16, 32),
        "description": "80s inspired, arpeggios, nostalgia"
    },
    "ambient": {
        "min": 60,
        "max": 120,
        "typical": 90,
        "energy": "low",
        "transition_style": "long_blend",
        "transition_bars": (64, 128),
        "description": "Atmospheric, textural, no beat focus"
    },
    "downtempo": {
        "min": 70,
        "max": 100,
        "typical": 85,
        "energy": "low",
        "transition_style": "long_blend",
        "transition_bars": (32, 64),
        "description": "Chilled, trip-hop influenced, groovy"
    },

    # Non-electronic
    "hip_hop": {
        "min": 85,
        "max": 115,
        "typical": 95,
        "energy": "variable",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Vocal-focused, boom-bap or trap beats"
    },
    "trap": {
        "min": 130,
        "max": 160,
        "typical": 140,
        "energy": "high",
        "transition_style": "cut",
        "transition_bars": (4, 8),
        "description": "Half-time hi-hats, 808 bass, drops",
        "note": "Often felt at half tempo (70-80 BPM)"
    },
    "rnb": {
        "min": 60,
        "max": 90,
        "typical": 75,
        "energy": "low",
        "transition_style": "fade",
        "transition_bars": (8, 16),
        "description": "Smooth, vocal-driven, sensual"
    },
    "reggae": {
        "min": 60,
        "max": 90,
        "typical": 75,
        "energy": "low",
        "transition_style": "fade",
        "transition_bars": (8, 16),
        "description": "Offbeat emphasis, one-drop rhythm"
    },
    "reggaeton": {
        "min": 85,
        "max": 100,
        "typical": 92,
        "energy": "medium",
        "transition_style": "blend",
        "transition_bars": (8, 16),
        "description": "Dembow rhythm, Latin influence"
    },
}


def detect_genre_from_bpm(bpm: float, threshold: float = 5.0) -> list[dict]:
    """
    Detect possible genres for a given BPM.

    Args:
        bpm: The BPM to match
        threshold: How far from typical BPM to still consider (default 5)

    Returns:
        List of matching genres sorted by closeness to typical BPM
    """
    matches = []

    for genre, data in BPM_REFERENCE.items():
        # Check if BPM is within range
        if data["min"] <= bpm <= data["max"]:
            # Calculate how close to typical BPM
            distance = abs(bpm - data["typical"])
            matches.append({
                "genre": genre,
                "distance_from_typical": distance,
                "within_typical": distance <= threshold,
                **data
            })

    # Sort by distance from typical (closest first)
    matches.sort(key=lambda x: x["distance_from_typical"])

    return matches


def get_transition_style_for_genre(genre: str) -> Optional[dict]:
    """
    Get recommended transition style for a genre.

    Args:
        genre: Genre name

    Returns:
        Dict with transition_style and transition_bars, or None
    """
    genre_lower = genre.lower().replace(" ", "_").replace("-", "_")

    if genre_lower in BPM_REFERENCE:
        data = BPM_REFERENCE[genre_lower]
        return {
            "transition_style": data["transition_style"],
            "transition_bars": data["transition_bars"],
            "energy": data["energy"]
        }

    return None


def get_transition_duration_bars(
    bpm: float,
    energy_level: str = "medium",
    set_phase: str = "BUILD"
) -> tuple[int, int]:
    """
    Get recommended transition duration in bars based on BPM and context.

    Args:
        bpm: Current BPM
        energy_level: "low", "medium", "high", "very_high"
        set_phase: "WARMUP", "BUILD", "PEAK", "COOLDOWN"

    Returns:
        Tuple of (min_bars, max_bars)
    """
    # Detect possible genres
    genres = detect_genre_from_bpm(bpm)

    if genres:
        # Use the most likely genre's recommendation
        base_bars = genres[0]["transition_bars"]
    else:
        # Default based on BPM
        if bpm < 100:
            base_bars = (16, 32)
        elif bpm < 130:
            base_bars = (16, 32)
        elif bpm < 145:
            base_bars = (8, 16)
        else:
            base_bars = (4, 8)

    # Adjust for set phase
    phase_multipliers = {
        "WARMUP": 2.0,    # Longer transitions
        "BUILD": 1.0,     # Standard
        "PEAK": 0.5,      # Shorter, punchier
        "COOLDOWN": 2.0   # Longer, smoother
    }

    multiplier = phase_multipliers.get(set_phase, 1.0)

    # Calculate adjusted bars
    min_bars = max(4, int(base_bars[0] * multiplier))
    max_bars = max(8, int(base_bars[1] * multiplier))

    # Ensure min <= max and reasonable bounds
    min_bars = min(min_bars, 64)
    max_bars = min(max_bars, 128)

    return (min_bars, max_bars)


def is_bpm_compatible(bpm_a: float, bpm_b: float, max_diff_percent: float = 6.0) -> dict:
    """
    Check if two BPMs are compatible for mixing.

    Args:
        bpm_a: First track BPM
        bpm_b: Second track BPM
        max_diff_percent: Maximum allowed percentage difference

    Returns:
        Dict with compatibility info
    """
    # Calculate percentage difference
    diff = abs(bpm_a - bpm_b)
    avg_bpm = (bpm_a + bpm_b) / 2
    diff_percent = (diff / avg_bpm) * 100

    # Check for half/double time compatibility
    half_bpm_b = bpm_b / 2
    double_bpm_b = bpm_b * 2

    half_diff_percent = (abs(bpm_a - half_bpm_b) / bpm_a) * 100
    double_diff_percent = (abs(bpm_a - double_bpm_b) / bpm_a) * 100

    if diff_percent <= max_diff_percent:
        return {
            "compatible": True,
            "diff_percent": diff_percent,
            "stretch_needed": diff_percent > 2,
            "transition_type": "blend" if diff_percent <= 4 else "blend_or_cut",
            "note": "Direct BPM match"
        }
    elif half_diff_percent <= max_diff_percent:
        return {
            "compatible": True,
            "diff_percent": half_diff_percent,
            "stretch_needed": True,
            "transition_type": "cut",
            "note": f"Half-time match ({bpm_b} -> {half_bpm_b})"
        }
    elif double_diff_percent <= max_diff_percent:
        return {
            "compatible": True,
            "diff_percent": double_diff_percent,
            "stretch_needed": True,
            "transition_type": "cut",
            "note": f"Double-time match ({bpm_b} -> {double_bpm_b})"
        }
    else:
        return {
            "compatible": False,
            "diff_percent": diff_percent,
            "stretch_needed": False,
            "transition_type": "hard_cut",
            "note": f"BPM difference too large ({diff_percent:.1f}%)"
        }
