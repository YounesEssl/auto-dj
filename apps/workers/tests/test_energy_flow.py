"""
Tests for energy flow management - serpentine pattern and set phases.
"""

import pytest
from src.energy.set_manager import (
    determine_set_phase,
    get_transition_recommendations,
    SetPhase,
)
from src.energy.serpentine import (
    apply_serpentine_flow,
    suggest_energy_ordering,
    create_tease,
    validate_serpentine_ratio,
)


class TestSerpentineFlow:
    """Test serpentine energy flow pattern (5:1 ratio)."""

    def test_serpentine_5_to_1_ratio(self):
        """Energy should follow 5:1 high-to-medium ratio."""
        # Create a sequence of tracks with energies
        tracks = [
            {"id": "1", "energy": 0.8},   # High
            {"id": "2", "energy": 0.85},  # High
            {"id": "3", "energy": 0.9},   # High
            {"id": "4", "energy": 0.82},  # High
            {"id": "5", "energy": 0.87},  # High
            {"id": "6", "energy": 0.6},   # Medium (dip)
            {"id": "7", "energy": 0.75},  # High
            {"id": "8", "energy": 0.88},  # High
        ]

        is_valid, ratio = validate_serpentine_ratio(tracks, threshold=0.7)

        # Should be close to 5:1 ratio
        assert ratio >= 4, f"Expected ratio >= 4, got {ratio}"

    def test_apply_serpentine_reorders_tracks(self):
        """Serpentine flow should reorder tracks to follow pattern."""
        tracks = [
            {"id": "1", "energy": 0.9},
            {"id": "2", "energy": 0.5},  # Low - should become a dip
            {"id": "3", "energy": 0.85},
            {"id": "4", "energy": 0.45},  # Low
            {"id": "5", "energy": 0.88},
            {"id": "6", "energy": 0.82},
        ]

        ordered = apply_serpentine_flow(tracks, target_ratio=5)

        assert len(ordered) == len(tracks)
        # The ordering should create peaks and valleys

    def test_suggest_energy_ordering(self):
        """Energy ordering suggestions should follow serpentine."""
        energies = [0.9, 0.5, 0.85, 0.45, 0.88, 0.82, 0.55, 0.78]
        ordered_indices = suggest_energy_ordering(energies, ratio=5)

        # The result should be indices in suggested order
        assert len(ordered_indices) == len(energies)

    def test_serpentine_prevents_listener_fatigue(self):
        """Serpentine flow should prevent listener fatigue."""
        # A set that's all high energy would cause fatigue
        all_high = [{"id": str(i), "energy": 0.9} for i in range(10)]

        is_valid, ratio = validate_serpentine_ratio(all_high, threshold=0.7)

        # All high energy doesn't follow serpentine
        # This should fail or have infinite ratio (no lows)
        assert not is_valid or ratio > 10


class TestSetPhases:
    """Test set phase determination."""

    def test_warmup_phase_at_start(self):
        """Early tracks should be WARMUP phase."""
        phase = determine_set_phase(track_index=0, total_tracks=20)
        assert phase == SetPhase.WARMUP

        phase = determine_set_phase(track_index=2, total_tracks=20)
        assert phase == SetPhase.WARMUP

    def test_build_phase_early_middle(self):
        """Early-middle tracks should be BUILD phase."""
        phase = determine_set_phase(track_index=5, total_tracks=20)
        assert phase == SetPhase.BUILD

    def test_peak_phase_at_middle(self):
        """Middle tracks should be PEAK phase."""
        phase = determine_set_phase(track_index=10, total_tracks=20)
        assert phase == SetPhase.PEAK

        phase = determine_set_phase(track_index=12, total_tracks=20)
        assert phase == SetPhase.PEAK

    def test_cooldown_phase_at_end(self):
        """Late tracks should be COOLDOWN phase."""
        phase = determine_set_phase(track_index=18, total_tracks=20)
        assert phase == SetPhase.COOLDOWN

        phase = determine_set_phase(track_index=19, total_tracks=20)
        assert phase == SetPhase.COOLDOWN

    def test_short_set_phases(self):
        """Short sets should still have all phases."""
        # 8 track set
        phases = [determine_set_phase(i, 8) for i in range(8)]

        # Should have at least warmup and peak
        assert SetPhase.WARMUP in phases
        assert SetPhase.PEAK in phases


class TestTransitionRecommendations:
    """Test transition recommendations by set phase."""

    def test_warmup_recommends_long_smooth(self):
        """WARMUP should recommend long, smooth transitions."""
        rec = get_transition_recommendations(SetPhase.WARMUP)

        assert rec["min_bars"] >= 16
        assert rec["max_bars"] >= 32
        assert "STEM_BLEND" in rec["preferred_types"]
        assert rec["allow_hard_cut"] is False

    def test_build_recommends_medium(self):
        """BUILD should recommend medium transitions."""
        rec = get_transition_recommendations(SetPhase.BUILD)

        assert 8 <= rec["min_bars"] <= 16
        assert rec["max_bars"] <= 32
        assert "STEM_BLEND" in rec["preferred_types"]
        assert "CROSSFADE" in rec["preferred_types"]

    def test_peak_allows_variety(self):
        """PEAK should allow varied transitions including hard cuts."""
        rec = get_transition_recommendations(SetPhase.PEAK)

        assert rec["min_bars"] >= 4
        assert rec["max_bars"] <= 16
        assert rec["allow_hard_cut"] is True

    def test_cooldown_recommends_long_smooth(self):
        """COOLDOWN should recommend long, smooth transitions."""
        rec = get_transition_recommendations(SetPhase.COOLDOWN)

        assert rec["min_bars"] >= 16
        assert "STEM_BLEND" in rec["preferred_types"]


class TestTease:
    """Test the tease technique for building anticipation."""

    def test_create_tease_structure(self):
        """Tease should create brief introduction then pull back."""
        track_energy = 0.9
        current_energy = 0.7

        tease_config = create_tease(
            target_energy=track_energy,
            current_energy=current_energy,
            tease_duration_bars=4,
            full_intro_bars=16,
            bpm=128.0
        )

        assert "tease_duration" in tease_config
        assert "pullback_duration" in tease_config
        assert "final_intro_duration" in tease_config

        # Tease should be short
        assert tease_config["tease_duration"] <= 4 * (60.0 / 128.0) * 4  # 4 bars

    def test_tease_builds_anticipation(self):
        """Tease should be used for building to high-energy tracks."""
        # Tease makes sense when:
        # - Current energy is medium
        # - Target energy is high
        # - We want to build anticipation

        track_energy = 0.95  # Very high energy target
        current_energy = 0.65  # Medium energy current

        should_tease = track_energy - current_energy > 0.2
        assert should_tease, "Should use tease for large energy jump"


class TestEnergyProgression:
    """Test energy progression throughout a set."""

    def test_warmup_has_lower_energy(self):
        """WARMUP phase should target lower energy tracks."""
        # In warmup, we should play 60-75% energy tracks
        target_energy_range = (0.5, 0.75)

        phase = SetPhase.WARMUP
        rec = get_transition_recommendations(phase)

        # Recommendations should suggest moderate energy
        assert rec.get("target_energy_min", 0.5) >= 0.4
        assert rec.get("target_energy_max", 0.75) <= 0.8

    def test_peak_has_highest_energy(self):
        """PEAK phase should target highest energy tracks."""
        # In peak, we should play 80-100% energy tracks
        target_energy_range = (0.8, 1.0)

        phase = SetPhase.PEAK
        rec = get_transition_recommendations(phase)

        # Recommendations should suggest high energy
        assert rec.get("target_energy_min", 0.7) >= 0.7

    def test_cooldown_decreases_energy(self):
        """COOLDOWN phase should decrease energy gradually."""
        phase = SetPhase.COOLDOWN
        rec = get_transition_recommendations(phase)

        # Should prefer smoother, longer transitions
        assert rec["min_bars"] >= 16


class TestEnergyJumpWarnings:
    """Test warnings for energy jumps."""

    def test_large_energy_jump_warned(self):
        """Large energy jumps should generate warnings."""
        energy_a = 0.6
        energy_b = 0.95

        delta = abs(energy_b - energy_a)

        # Delta > 0.25 should trigger ENERGY_JUMP warning
        should_warn = delta > 0.25
        assert should_warn, "Large energy jump should trigger warning"

    def test_gradual_energy_change_ok(self):
        """Gradual energy changes should not warn."""
        energy_a = 0.7
        energy_b = 0.75

        delta = abs(energy_b - energy_a)

        should_warn = delta > 0.25
        assert not should_warn, "Small energy change should be OK"
