"""
Tests for harmonic mixing rules.

Key rule: harmonic < 50 FORCES hard cut, no blend allowed.
"""

import pytest
from src.theory.camelot import calculate_harmonic_compatibility


class TestHarmonicForcesHardCut:
    """Test that low harmonic compatibility forces hard cuts."""

    def test_harmonic_below_50_forces_hard_cut(self):
        """Score < 50 should force HARD_CUT transition."""
        # 8A to 2B is very incompatible
        result = calculate_harmonic_compatibility("8A", "2B")

        assert result["score"] < 50, "8A to 2B should have score < 50"
        # In real usage, this score would trigger HARD_CUT

    def test_harmonic_50_to_69_forces_short_blend(self):
        """Score 50-69 should require short blend or filter."""
        # Find keys that give score in this range
        # ±3 or ±4 positions typically fall here
        result = calculate_harmonic_compatibility("8A", "4A")

        # This should be in the medium-low range
        assert result["score"] < 70 or result["type"] == "incompatible"

    def test_harmonic_70_to_89_allows_medium_blend(self):
        """Score 70-89 should allow medium blends (8-16 bars)."""
        # Two steps away (±2 same mode)
        result = calculate_harmonic_compatibility("8A", "6A")

        assert result["score"] == 70
        # This allows CROSSFADE or short STEM_BLEND

    def test_harmonic_90_plus_allows_long_blend(self):
        """Score >= 90 should allow long blends (16-64 bars)."""
        # Same key
        result = calculate_harmonic_compatibility("8A", "8A")
        assert result["score"] == 100

        # Adjacent key
        result = calculate_harmonic_compatibility("8A", "7A")
        assert result["score"] == 95

        # Relative key
        result = calculate_harmonic_compatibility("8A", "8B")
        assert result["score"] == 90


class TestHarmonicDecisionLogic:
    """Test the decision logic based on harmonic scores."""

    def get_recommended_transition(self, score: int) -> str:
        """Get recommended transition type based on harmonic score."""
        if score >= 90:
            return "STEM_BLEND"
        elif score >= 70:
            return "CROSSFADE"
        elif score >= 50:
            return "FILTER_SWEEP"
        else:
            return "HARD_CUT"

    def test_same_key_recommends_stem_blend(self):
        """Same key should recommend STEM_BLEND."""
        result = calculate_harmonic_compatibility("8A", "8A")
        transition = self.get_recommended_transition(result["score"])
        assert transition == "STEM_BLEND"

    def test_adjacent_key_recommends_stem_blend(self):
        """Adjacent key should recommend STEM_BLEND."""
        result = calculate_harmonic_compatibility("8A", "7A")
        transition = self.get_recommended_transition(result["score"])
        assert transition == "STEM_BLEND"

    def test_relative_key_recommends_stem_blend(self):
        """Relative key should recommend STEM_BLEND."""
        result = calculate_harmonic_compatibility("8A", "8B")
        transition = self.get_recommended_transition(result["score"])
        assert transition == "STEM_BLEND"

    def test_two_steps_recommends_crossfade(self):
        """Two steps away should recommend CROSSFADE."""
        result = calculate_harmonic_compatibility("8A", "6A")
        transition = self.get_recommended_transition(result["score"])
        assert transition == "CROSSFADE"

    def test_incompatible_recommends_hard_cut(self):
        """Incompatible keys should recommend HARD_CUT."""
        result = calculate_harmonic_compatibility("8A", "2B")
        transition = self.get_recommended_transition(result["score"])
        assert transition == "HARD_CUT"


class TestHarmonicEdgeCases:
    """Test edge cases in harmonic compatibility."""

    def test_wrap_around_12_to_1(self):
        """12A to 1A should be adjacent (wrap around)."""
        result = calculate_harmonic_compatibility("12A", "1A")
        assert result["score"] == 95
        assert result["type"] == "adjacent"

    def test_wrap_around_1_to_12(self):
        """1A to 12A should be adjacent (wrap around)."""
        result = calculate_harmonic_compatibility("1A", "12A")
        assert result["score"] == 95
        assert result["type"] == "adjacent"

    def test_energy_boost_wrap_around(self):
        """Energy boost +7 should wrap around correctly."""
        # 8A + 7 = 3A (wraps at 12)
        result = calculate_harmonic_compatibility("8A", "3A")
        assert result["score"] == 75
        assert result["type"] == "energy_boost"

        # 6A + 7 = 1A (wraps at 12)
        result = calculate_harmonic_compatibility("6A", "1A")
        assert result["score"] == 75

    def test_both_keys_normalized(self):
        """Both uppercase and lowercase should work."""
        result1 = calculate_harmonic_compatibility("8A", "8B")
        result2 = calculate_harmonic_compatibility("8a", "8b")
        assert result1["score"] == result2["score"]


class TestHarmonicWithBPM:
    """Test harmonic rules combined with BPM constraints."""

    def should_use_hard_cut(
        self,
        harmonic_score: int,
        bpm_delta_percent: float
    ) -> bool:
        """Determine if HARD_CUT should be used."""
        # Hard cut if:
        # - Harmonic < 50, OR
        # - BPM delta > 6%
        return harmonic_score < 50 or bpm_delta_percent > 6

    def test_good_harmonic_bad_bpm_forces_cut(self):
        """Good harmonic but bad BPM should force HARD_CUT."""
        harmonic_result = calculate_harmonic_compatibility("8A", "8A")
        assert harmonic_result["score"] == 100

        # But 126 BPM to 145 BPM is too far
        bpm_a = 126.0
        bpm_b = 145.0
        bpm_delta = abs(bpm_a - bpm_b) / bpm_a * 100

        assert bpm_delta > 6
        assert self.should_use_hard_cut(harmonic_result["score"], bpm_delta)

    def test_bad_harmonic_good_bpm_forces_cut(self):
        """Bad harmonic even with good BPM should force HARD_CUT."""
        harmonic_result = calculate_harmonic_compatibility("8A", "2B")
        assert harmonic_result["score"] < 50

        # Same BPM
        bpm_delta = 0

        assert self.should_use_hard_cut(harmonic_result["score"], bpm_delta)

    def test_both_good_allows_blend(self):
        """Good harmonic and good BPM should allow blending."""
        harmonic_result = calculate_harmonic_compatibility("8A", "7A")
        assert harmonic_result["score"] >= 90

        # Similar BPM (1% diff)
        bpm_a = 126.0
        bpm_b = 127.0
        bpm_delta = abs(bpm_a - bpm_b) / bpm_a * 100

        assert bpm_delta < 6
        assert not self.should_use_hard_cut(harmonic_result["score"], bpm_delta)


class TestHarmonicAllPairs:
    """Test systematic harmonic pairs."""

    def test_all_same_keys_score_100(self):
        """All same-key pairs should score 100."""
        for num in range(1, 13):
            for mode in ["A", "B"]:
                key = f"{num}{mode}"
                result = calculate_harmonic_compatibility(key, key)
                assert result["score"] == 100, f"{key} to {key} should be 100"

    def test_all_adjacent_pairs_score_95(self):
        """All adjacent pairs should score 95."""
        for num in range(1, 13):
            for mode in ["A", "B"]:
                key = f"{num}{mode}"
                # +1 adjacent
                next_num = (num % 12) + 1
                adjacent_key = f"{next_num}{mode}"
                result = calculate_harmonic_compatibility(key, adjacent_key)
                assert result["score"] == 95, f"{key} to {adjacent_key} should be 95"

    def test_all_relative_pairs_score_90(self):
        """All relative major/minor pairs should score 90."""
        for num in range(1, 13):
            key_a = f"{num}A"
            key_b = f"{num}B"
            result = calculate_harmonic_compatibility(key_a, key_b)
            assert result["score"] == 90, f"{key_a} to {key_b} should be 90"
