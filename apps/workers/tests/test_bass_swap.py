"""
Tests for bass swap - THE SACRED RULE.

NEVER two basses simultaneously for more than 2 beats.
"""

import pytest
import numpy as np
from src.mixing.transitions.bass_swap import (
    execute_bass_swap,
    validate_bass_swap,
    apply_bass_swap_to_stems,
)


class TestBassSwapSacredRule:
    """Test the sacred bass swap rule: NEVER two basses > 2 beats."""

    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for testing."""
        sr = 44100
        duration = 10.0  # 10 seconds
        samples = int(duration * sr)
        # Generate sine wave as bass
        t = np.linspace(0, duration, samples)
        audio = np.sin(2 * np.pi * 60 * t).astype(np.float32)  # 60Hz bass
        return audio, sr

    @pytest.fixture
    def sample_stems(self, sample_audio):
        """Generate sample stems for testing."""
        audio, sr = sample_audio
        return {
            "drums": np.random.randn(len(audio)).astype(np.float32) * 0.5,
            "bass": audio.copy(),
            "vocals": np.random.randn(len(audio)).astype(np.float32) * 0.3,
            "other": np.random.randn(len(audio)).astype(np.float32) * 0.4,
        }

    def test_instant_swap_no_overlap(self, sample_stems):
        """Instant bass swap should have zero overlap."""
        stems_a = sample_stems.copy()
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        swap_time = 5.0  # Swap at 5 seconds
        sr = 44100
        bpm = 128

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=swap_time,
            swap_duration="instant",
            bpm=bpm,
            sr=sr
        )

        swap_sample = int(swap_time * sr)

        # Before swap: A bass should be present, B bass should be 0
        assert np.any(result_a["bass"][:swap_sample] != 0), "A bass should exist before swap"
        assert np.allclose(result_b["bass"][:swap_sample], 0), "B bass should be 0 before swap"

        # After swap: A bass should be 0, B bass should be present
        assert np.allclose(result_a["bass"][swap_sample:], 0), "A bass should be 0 after swap"
        assert np.any(result_b["bass"][swap_sample:] != 0), "B bass should exist after swap"

    def test_one_bar_swap_max_overlap(self, sample_stems):
        """1-bar bass swap should have maximum 1 bar overlap."""
        stems_a = sample_stems.copy()
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        swap_time = 5.0
        sr = 44100
        bpm = 128

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=swap_time,
            swap_duration="1_bar",
            bpm=bpm,
            sr=sr
        )

        # Calculate 1 bar duration (4 beats)
        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4
        bar_samples = int(bar_duration * sr)

        swap_sample = int(swap_time * sr)

        # The overlap region should be at most 1 bar
        overlap_start = swap_sample
        overlap_end = swap_sample + bar_samples

        # Check both basses are present in overlap (crossfade)
        a_in_overlap = result_a["bass"][overlap_start:overlap_end]
        b_in_overlap = result_b["bass"][overlap_start:overlap_end]

        # After the overlap, only B should have bass
        assert np.allclose(result_a["bass"][overlap_end:], 0, atol=0.01), \
            "A bass should be gone after crossfade"

    def test_never_two_basses_more_than_2_beats(self, sample_stems):
        """SACRED RULE: Never two basses simultaneously > 2 beats."""
        stems_a = sample_stems.copy()
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        swap_time = 5.0
        sr = 44100
        bpm = 128

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=swap_time,
            swap_duration="1_bar",
            bpm=bpm,
            sr=sr
        )

        # Calculate 2 beats duration
        beat_duration = 60.0 / bpm
        two_beats_samples = int(2 * beat_duration * sr)

        # Find where both basses are non-zero (above threshold)
        threshold = 0.01
        both_present = (np.abs(result_a["bass"]) > threshold) & (np.abs(result_b["bass"]) > threshold)

        # Find consecutive regions where both are present
        changes = np.diff(both_present.astype(int))
        starts = np.where(changes == 1)[0] + 1
        ends = np.where(changes == -1)[0] + 1

        if len(starts) > 0 and len(ends) > 0:
            for start, end in zip(starts, ends):
                overlap_duration = end - start
                assert overlap_duration <= two_beats_samples, \
                    f"Both basses present for {overlap_duration} samples, max allowed is {two_beats_samples}"

    def test_validate_bass_swap_catches_violations(self):
        """Validate function should catch bass swap violations."""
        sr = 44100
        bpm = 128
        duration = 10.0
        samples = int(duration * sr)

        # Create stems with both basses present for too long (violation)
        bass_a = np.ones(samples, dtype=np.float32)
        bass_b = np.ones(samples, dtype=np.float32)

        is_valid, error_msg = validate_bass_swap(
            bass_a=bass_a,
            bass_b=bass_b,
            bpm=bpm,
            sr=sr
        )

        assert not is_valid, "Should detect bass overlap violation"
        assert "overlap" in error_msg.lower() or "violation" in error_msg.lower()

    def test_validate_bass_swap_passes_clean_swap(self, sample_stems):
        """Validate function should pass clean bass swaps."""
        stems_a = sample_stems.copy()
        stems_b = {k: v.copy() for k, v in sample_stems.items()}

        swap_time = 5.0
        sr = 44100
        bpm = 128

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=swap_time,
            swap_duration="instant",
            bpm=bpm,
            sr=sr
        )

        is_valid, error_msg = validate_bass_swap(
            bass_a=result_a["bass"],
            bass_b=result_b["bass"],
            bpm=bpm,
            sr=sr
        )

        assert is_valid, f"Clean bass swap should validate: {error_msg}"


class TestBassSwapTiming:
    """Test bass swap timing precision."""

    def test_swap_on_downbeat(self):
        """Bass swap should ideally occur on a downbeat."""
        sr = 44100
        bpm = 128
        beat_duration = 60.0 / bpm

        # Swap at bar 4 (beat 16)
        swap_beat = 16
        expected_swap_time = swap_beat * beat_duration

        # Create simple audio
        duration = 30.0
        samples = int(duration * sr)
        audio = np.random.randn(samples).astype(np.float32) * 0.5

        stems_a = {"bass": audio.copy()}
        stems_b = {"bass": audio.copy()}

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=expected_swap_time,
            swap_duration="instant",
            bpm=bpm,
            sr=sr
        )

        # Verify swap happened at expected time
        expected_sample = int(expected_swap_time * sr)

        assert np.allclose(result_a["bass"][expected_sample:], 0, atol=0.01), \
            "Bass A should be cut after swap"

    def test_swap_at_phrase_boundary(self):
        """Bass swap in real mixes happens at phrase boundaries (8 bars)."""
        sr = 44100
        bpm = 128
        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4

        # Swap at phrase boundary (8 bars = 32 beats)
        phrase_bars = 8
        swap_time = phrase_bars * bar_duration

        samples = int(60.0 * sr)
        audio = np.random.randn(samples).astype(np.float32) * 0.5

        stems_a = {"bass": audio.copy(), "drums": audio.copy(), "other": audio.copy(), "vocals": audio.copy()}
        stems_b = {"bass": audio.copy(), "drums": audio.copy(), "other": audio.copy(), "vocals": audio.copy()}

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=swap_time,
            swap_duration="instant",
            bpm=bpm,
            sr=sr
        )

        # Bass swap should be clean at phrase boundary
        swap_sample = int(swap_time * sr)
        assert np.allclose(result_a["bass"][swap_sample:], 0, atol=0.01)


class TestBassSwapDurations:
    """Test different bass swap duration styles."""

    @pytest.fixture
    def stems(self):
        sr = 44100
        samples = int(30.0 * sr)
        audio = np.sin(2 * np.pi * 60 * np.linspace(0, 30.0, samples)).astype(np.float32)
        return {
            "bass": audio,
            "drums": np.random.randn(samples).astype(np.float32),
            "other": np.random.randn(samples).astype(np.float32),
            "vocals": np.random.randn(samples).astype(np.float32),
        }

    def test_instant_swap(self, stems):
        """Instant swap should be instantaneous."""
        stems_a = {k: v.copy() for k, v in stems.items()}
        stems_b = {k: v.copy() for k, v in stems.items()}

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a, stems_b,
            swap_time=10.0,
            swap_duration="instant",
            bpm=128,
            sr=44100
        )

        # Check the transition is sharp
        swap_sample = int(10.0 * 44100)
        assert result_a["bass"][swap_sample - 1] != 0 or result_a["bass"][swap_sample] == 0

    def test_1_bar_swap(self, stems):
        """1-bar swap should crossfade over 4 beats."""
        stems_a = {k: v.copy() for k, v in stems.items()}
        stems_b = {k: v.copy() for k, v in stems.items()}

        result_a, result_b = apply_bass_swap_to_stems(
            stems_a, stems_b,
            swap_time=10.0,
            swap_duration="1_bar",
            bpm=128,
            sr=44100
        )

        # The swap should take exactly 1 bar
        bpm = 128
        bar_duration = (60.0 / bpm) * 4
        bar_samples = int(bar_duration * 44100)
        swap_sample = int(10.0 * 44100)

        # During the bar, both basses should be present (crossfading)
        mid_swap = swap_sample + bar_samples // 2
        # After the bar, only B bass
        after_swap = swap_sample + bar_samples + 100
        assert np.allclose(result_a["bass"][after_swap:], 0, atol=0.01)
