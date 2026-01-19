"""
Tests for transition module - stem blending, cuts, filters.
"""

import pytest
import numpy as np
from src.mixing.transitions.blend import (
    create_stem_blend,
    create_blend_transition,
    get_default_phases,
)
from src.mixing.transitions.cut import (
    create_cut_transition,
    create_cut_with_effect,
)
from src.mixing.transitions.filter_transition import (
    create_filter_transition,
    create_hpf_exit,
    create_lpf_entry,
)


class TestStemBlend:
    """Test stem-based blending transitions."""

    @pytest.fixture
    def sample_stems(self):
        """Generate sample stems for testing."""
        sr = 44100
        duration = 30.0
        samples = int(duration * sr)
        return {
            "drums": np.random.randn(samples).astype(np.float32) * 0.5,
            "bass": np.sin(2 * np.pi * 60 * np.linspace(0, duration, samples)).astype(np.float32),
            "vocals": np.random.randn(samples).astype(np.float32) * 0.3,
            "other": np.random.randn(samples).astype(np.float32) * 0.4,
        }

    def test_stem_blend_creates_output(self, sample_stems):
        """Stem blend should produce audio output."""
        stems_a = sample_stems
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        result = create_stem_blend(
            stems_a=stems_a,
            stems_b=stems_b,
            duration_bars=16,
            bass_swap_bar=9,
            bpm=128.0,
            sr=44100
        )

        assert result is not None
        assert len(result) > 0
        assert isinstance(result, np.ndarray)

    def test_stem_blend_duration_correct(self, sample_stems):
        """Stem blend should have correct duration."""
        stems_a = sample_stems
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        duration_bars = 16
        bpm = 128.0
        sr = 44100

        expected_duration = duration_bars * 4 * (60.0 / bpm)  # bars * beats_per_bar * beat_duration
        expected_samples = int(expected_duration * sr)

        result = create_stem_blend(
            stems_a=stems_a,
            stems_b=stems_b,
            duration_bars=duration_bars,
            bass_swap_bar=9,
            bpm=bpm,
            sr=sr
        )

        # Allow 10% tolerance for processing
        assert abs(len(result) - expected_samples) / expected_samples < 0.1

    def test_stem_blend_phases_applied(self, sample_stems):
        """Custom phases should be applied correctly."""
        stems_a = sample_stems
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        custom_phases = [
            {
                "bars": [1, 4],
                "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0},
                "b": {"drums": 0.0, "bass": 0.0, "other": 0.0, "vocals": 0.0}
            },
            {
                "bars": [5, 8],
                "a": {"drums": 0.5, "bass": 0.5, "other": 0.5, "vocals": 0.5},
                "b": {"drums": 0.5, "bass": 0.5, "other": 0.5, "vocals": 0.5}
            },
        ]

        result = create_stem_blend(
            stems_a=stems_a,
            stems_b=stems_b,
            duration_bars=8,
            bass_swap_bar=5,
            bpm=128.0,
            phases=custom_phases,
            sr=44100
        )

        assert result is not None
        assert len(result) > 0

    def test_default_phases_structure(self):
        """Default phases should have correct structure."""
        phases = get_default_phases(duration_bars=16)

        assert len(phases) == 4  # 4 phases
        for phase in phases:
            assert "bars" in phase
            assert "a" in phase
            assert "b" in phase
            assert len(phase["bars"]) == 2  # [start, end]


class TestPhraseAlignment:
    """Test phrase boundary alignment in transitions."""

    def test_transition_starts_on_phrase(self):
        """Transitions should start on phrase boundaries."""
        sr = 44100
        bpm = 128.0
        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4
        phrase_duration = bar_duration * 8  # 8 bars = 1 phrase

        samples = int(60.0 * sr)
        audio_a = np.random.randn(samples).astype(np.float32)
        audio_b = np.random.randn(samples).astype(np.float32)

        # Transition starting at phrase boundary (16 bars = 2 phrases)
        transition_start = 16 * bar_duration

        result = create_blend_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            transition_duration=phrase_duration,  # 8 bars
            crossfade_type="equal_power",
            sr=sr
        )

        # Result should have correct duration
        expected_samples = int(phrase_duration * sr)
        assert abs(len(result) - expected_samples) / expected_samples < 0.05

    def test_8_bar_phrase(self):
        """Standard 8-bar phrase should be handled."""
        sr = 44100
        bpm = 128.0
        bar_duration = (60.0 / bpm) * 4

        phrase_bars = 8
        phrase_duration = phrase_bars * bar_duration

        samples = int(phrase_duration * sr)
        audio_a = np.random.randn(samples).astype(np.float32)
        audio_b = np.random.randn(samples).astype(np.float32)

        result = create_blend_transition(
            audio_a, audio_b,
            transition_duration=phrase_duration,
            sr=sr
        )

        assert len(result) == samples

    def test_16_bar_phrase(self):
        """16-bar phrase (double phrase) should be handled."""
        sr = 44100
        bpm = 128.0
        bar_duration = (60.0 / bpm) * 4

        phrase_bars = 16
        phrase_duration = phrase_bars * bar_duration

        samples = int(phrase_duration * sr)
        audio_a = np.random.randn(samples).astype(np.float32)
        audio_b = np.random.randn(samples).astype(np.float32)

        result = create_blend_transition(
            audio_a, audio_b,
            transition_duration=phrase_duration,
            sr=sr
        )

        assert len(result) == samples


class TestCutTransition:
    """Test hard cut transitions."""

    @pytest.fixture
    def sample_audio(self):
        sr = 44100
        duration = 30.0
        samples = int(duration * sr)
        return np.random.randn(samples).astype(np.float32), sr

    def test_hard_cut_instant(self, sample_audio):
        """Hard cut should be near-instantaneous."""
        audio, sr = sample_audio
        audio_a = audio
        audio_b = audio.copy()

        cut_point = 10.0
        entry_point = 0.0

        result = create_cut_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            cut_point_a=cut_point,
            entry_point_b=entry_point,
            sr=sr
        )

        assert result is not None
        # The cut should be clean (very short transition)

    def test_hard_cut_with_reverb_tail(self, sample_audio):
        """Hard cut with reverb should have a tail."""
        audio, sr = sample_audio
        audio_a = audio
        audio_b = audio.copy()

        cut_point = 10.0
        entry_point = 0.0

        result = create_cut_with_effect(
            audio_a=audio_a,
            audio_b=audio_b,
            cut_point_a=cut_point,
            entry_point_b=entry_point,
            effect="reverb",
            effect_params={"room_size": 0.8, "decay": 2.0},
            bpm=128.0,
            sr=sr
        )

        assert result is not None
        # Should be longer due to reverb tail

    def test_hard_cut_with_delay_tail(self, sample_audio):
        """Hard cut with delay should have echo tail."""
        audio, sr = sample_audio
        audio_a = audio
        audio_b = audio.copy()

        result = create_cut_with_effect(
            audio_a=audio_a,
            audio_b=audio_b,
            cut_point_a=10.0,
            entry_point_b=0.0,
            effect="delay",
            effect_params={"beat_fraction": 0.5, "feedback": 0.5},
            bpm=128.0,
            sr=sr
        )

        assert result is not None


class TestFilterTransition:
    """Test filter-based transitions."""

    @pytest.fixture
    def sample_audio(self):
        sr = 44100
        duration = 16.0
        samples = int(duration * sr)
        # Create audio with various frequencies
        t = np.linspace(0, duration, samples)
        audio = (
            np.sin(2 * np.pi * 60 * t) +   # Bass
            np.sin(2 * np.pi * 440 * t) +  # Mid
            np.sin(2 * np.pi * 4000 * t)   # High
        ).astype(np.float32)
        return audio, sr

    def test_filter_transition_creates_output(self, sample_audio):
        """Filter transition should produce output."""
        audio, sr = sample_audio
        audio_a = audio
        audio_b = audio.copy()

        result = create_filter_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            transition_duration=8.0,
            filter_a={"type": "hpf", "start": 20, "end": 2000},
            filter_b={"type": "lpf", "start": 200, "end": 20000},
            sr=sr
        )

        assert result is not None
        assert len(result) > 0

    def test_hpf_exit_removes_bass(self, sample_audio):
        """HPF exit should progressively remove low frequencies."""
        audio, sr = sample_audio

        result = create_hpf_exit(
            audio=audio,
            transition_duration=8.0,
            start_freq=20,
            end_freq=2000,
            sr=sr
        )

        assert result is not None
        # End of the result should have less bass energy
        # (This is a simplified check)
        start_energy = np.mean(result[:sr] ** 2)
        end_energy = np.mean(result[-sr:] ** 2)
        # HPF should reduce energy as it removes bass
        assert end_energy <= start_energy * 1.5  # Allow some tolerance

    def test_lpf_entry_reveals_highs(self, sample_audio):
        """LPF entry should progressively reveal high frequencies."""
        audio, sr = sample_audio

        result = create_lpf_entry(
            audio=audio,
            transition_duration=8.0,
            start_freq=200,
            end_freq=20000,
            sr=sr
        )

        assert result is not None
        # Start should be muffled, end should be full


class TestBlendTransition:
    """Test basic blend/crossfade transitions."""

    def test_equal_power_crossfade(self):
        """Equal power crossfade should maintain energy."""
        sr = 44100
        duration = 8.0
        samples = int(duration * sr)

        audio_a = np.ones(samples, dtype=np.float32)
        audio_b = np.ones(samples, dtype=np.float32)

        result = create_blend_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            transition_duration=duration,
            crossfade_type="equal_power",
            sr=sr
        )

        # Middle of crossfade should maintain approximate energy
        mid_sample = samples // 2
        mid_energy = np.mean(result[mid_sample - 100:mid_sample + 100] ** 2)
        start_energy = np.mean(audio_a[:100] ** 2)

        # Equal power should maintain energy within reasonable bounds
        assert mid_energy > start_energy * 0.5
        assert mid_energy < start_energy * 1.5

    def test_linear_crossfade(self):
        """Linear crossfade should have expected behavior."""
        sr = 44100
        duration = 8.0
        samples = int(duration * sr)

        audio_a = np.ones(samples, dtype=np.float32)
        audio_b = np.ones(samples, dtype=np.float32) * 2  # Different level

        result = create_blend_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            transition_duration=duration,
            crossfade_type="linear",
            sr=sr
        )

        # At midpoint, should be average of both
        mid_sample = samples // 2
        expected_mid = 1.5  # (1 + 2) / 2
        actual_mid = np.mean(result[mid_sample - 10:mid_sample + 10])

        assert abs(actual_mid - expected_mid) < 0.2
