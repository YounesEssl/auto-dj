"""
Tests for theory module - Camelot wheel and BPM reference.
"""

import pytest
from src.theory.camelot import (
    calculate_harmonic_compatibility,
    get_camelot_from_key,
    get_key_from_camelot,
    get_compatible_keys,
    CAMELOT_WHEEL,
)
from src.theory.bpm_reference import BPM_REFERENCE, detect_genre_from_bpm, is_bpm_compatible


class TestCamelotWheel:
    """Test Camelot wheel key relationships."""

    def test_camelot_same_key_100(self):
        """Same key should score 100 (perfect match)."""
        result = calculate_harmonic_compatibility("8A", "8A")
        assert result["score"] == 100
        assert result["type"] == "PERFECT"

    def test_camelot_adjacent_95(self):
        """Adjacent keys (±1 same mode) should score 95."""
        # 8A to 7A (adjacent minor)
        result = calculate_harmonic_compatibility("8A", "7A")
        assert result["score"] == 95
        assert result["type"] == "ADJACENT"

        # 8A to 9A (adjacent minor)
        result = calculate_harmonic_compatibility("8A", "9A")
        assert result["score"] == 95

        # 5B to 6B (adjacent major)
        result = calculate_harmonic_compatibility("5B", "6B")
        assert result["score"] == 95

    def test_camelot_relative_90(self):
        """Relative keys (A↔B same number) should score 90."""
        # 8A to 8B (relative major/minor)
        result = calculate_harmonic_compatibility("8A", "8B")
        assert result["score"] == 90
        assert result["type"] == "RELATIVE"

        # 3B to 3A
        result = calculate_harmonic_compatibility("3B", "3A")
        assert result["score"] == 90

    def test_camelot_diagonal_80(self):
        """Diagonal keys (±1 with mode change) should score 80."""
        # 8A to 7B
        result = calculate_harmonic_compatibility("8A", "7B")
        assert result["score"] == 80
        assert result["type"] == "DIAGONAL"

        # 8A to 9B
        result = calculate_harmonic_compatibility("8A", "9B")
        assert result["score"] == 80

    def test_camelot_two_steps_70(self):
        """Two steps away (±2 same mode) should score 70."""
        # 8A to 6A
        result = calculate_harmonic_compatibility("8A", "6A")
        assert result["score"] == 70
        assert result["type"] == "ENERGY_SHIFT"

        # 8A to 10A
        result = calculate_harmonic_compatibility("8A", "10A")
        assert result["score"] == 70

    def test_camelot_subdominant_70(self):
        """Subdominant (distance 5) should score 70."""
        # 8A to 3A (distance 5 on circular wheel)
        result = calculate_harmonic_compatibility("8A", "3A")
        assert result["score"] == 70
        assert result["type"] == "SUBDOMINANT"

    def test_camelot_incompatible_30(self):
        """Incompatible keys should score 30 or less."""
        # 8A to 2B (far apart)
        result = calculate_harmonic_compatibility("8A", "2B")
        assert result["score"] <= 30
        assert result["type"] == "INCOMPATIBLE"

    def test_musical_key_to_camelot_conversion(self):
        """Test conversion from musical keys to Camelot."""
        assert get_camelot_from_key("Am") == "8A"
        assert get_camelot_from_key("C") == "8B"
        assert get_camelot_from_key("D") == "10B"
        assert get_camelot_from_key("Gm") == "6A"

    def test_camelot_to_musical_key_conversion(self):
        """Test conversion from Camelot to musical keys."""
        assert get_key_from_camelot("8A") == "Am"
        assert get_key_from_camelot("8B") == "C"
        assert get_key_from_camelot("10B") == "D"

    def test_compatible_keys(self):
        """Test getting compatible keys."""
        compatible = get_compatible_keys("8A")
        camelots = [c["camelot"] for c in compatible]
        assert "7A" in camelots
        assert "9A" in camelots
        assert "8B" in camelots

    def test_camelot_wheel_completeness(self):
        """Verify the Camelot wheel has all 24 keys."""
        assert len(CAMELOT_WHEEL) == 24
        for num in range(1, 13):
            assert f"{num}A" in CAMELOT_WHEEL
            assert f"{num}B" in CAMELOT_WHEEL

    def test_harmonic_compatibility_symmetry(self):
        """Harmonic compatibility should be symmetric."""
        result_ab = calculate_harmonic_compatibility("8A", "5B")
        result_ba = calculate_harmonic_compatibility("5B", "8A")
        assert result_ab["score"] == result_ba["score"]


class TestBPMReference:
    """Test BPM reference by genre."""

    def test_genre_has_bpm_range(self):
        """Each genre should have a valid BPM range."""
        for genre, info in BPM_REFERENCE.items():
            assert "min" in info
            assert "max" in info
            assert info["min"] <= info["max"]

    def test_common_genres_present(self):
        """Common electronic genres should be present."""
        common_genres = [
            "deep_house",
            "tech_house",
            "melodic_techno",
            "trance",
            "drum_and_bass",
            "dubstep",
            "progressive_house",
        ]
        for genre in common_genres:
            assert genre in BPM_REFERENCE, f"Missing genre: {genre}"

    def test_tech_house_bpm_range(self):
        """Tech house should be in reasonable BPM range."""
        tech_house = BPM_REFERENCE["tech_house"]
        assert tech_house["min"] >= 120
        assert tech_house["max"] <= 135

    def test_drum_and_bass_bpm_range(self):
        """Drum and bass should be in 160-180 BPM range."""
        dnb = BPM_REFERENCE["drum_and_bass"]
        assert dnb["min"] >= 160
        assert dnb["max"] <= 185

    def test_detect_genre_from_bpm(self):
        """Test detecting genre from BPM."""
        # 128 BPM should match tech house, house, etc.
        matches = detect_genre_from_bpm(128)
        genres = [m["genre"] for m in matches]
        assert len(matches) > 0
        assert "tech_house" in genres or "progressive_house" in genres

    def test_bpm_compatibility(self):
        """Test BPM compatibility check."""
        # Same BPM should be compatible
        result = is_bpm_compatible(128, 128)
        assert result["compatible"] is True
        assert result["diff_percent"] == 0

        # Large difference should be incompatible
        result = is_bpm_compatible(128, 160)
        assert result["compatible"] is False


class TestHarmonicMixingRules:
    """Test harmonic mixing decision rules."""

    def test_high_compatibility_allows_long_blend(self):
        """Score >= 90 should allow long blends (16-64 bars)."""
        result = calculate_harmonic_compatibility("8A", "8A")
        assert result["score"] >= 90
        # This score allows STEM_BLEND transitions

    def test_medium_compatibility_allows_medium_blend(self):
        """Score 70-89 should allow medium blends (8-16 bars)."""
        result = calculate_harmonic_compatibility("8A", "6A")
        assert 70 <= result["score"] < 90

    def test_low_compatibility_requires_short_or_cut(self):
        """Score 50-69 should require short blend or filter."""
        result = calculate_harmonic_compatibility("8A", "4A")
        # 4 positions away
        assert result["score"] < 70

    def test_incompatible_requires_hard_cut(self):
        """Score < 50 should require HARD_CUT."""
        result = calculate_harmonic_compatibility("8A", "2B")
        assert result["score"] < 50
        # HARD_CUT is mandatory for this level
