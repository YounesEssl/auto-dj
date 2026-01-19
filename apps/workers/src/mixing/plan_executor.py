"""
Plan Executor - Execute LLM-generated transition plans.

This module takes a JSON plan from the LLM and executes it EXACTLY.
It's the heart of the transition generation system.

The plan format (v2.0) includes:
- track_a: play_from, play_until, cut_reason
- track_b: start_from, entry_reason
- transition: type, duration_bars, stems configuration, effects, volume automation
"""

import numpy as np
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import structlog

from .transitions.bass_swap import apply_bass_swap_to_stems
from .transitions.blend import create_stem_blend, create_blend_transition
from .transitions.cut import create_cut_transition, create_cut_with_effect
from .transitions.filter_transition import create_filter_transition
from .transitions.echo_out import create_echo_out_transition
from .stems import StemSeparator

logger = structlog.get_logger()


class TransitionPlanExecutor:
    """
    Executes LLM-generated transition plans.

    This class interprets the v2.0 plan format and calls the appropriate
    transition modules to generate professional DJ transitions.
    """

    def __init__(self, sr: int = 44100):
        """
        Initialize the executor.

        Args:
            sr: Sample rate for audio processing
        """
        self.sr = sr
        self.stem_separator = StemSeparator()

    def execute(
        self,
        track_a_path: str,
        track_b_path: str,
        plan: Dict[str, Any],
        analysis_a: Dict,
        analysis_b: Dict
    ) -> np.ndarray:
        """
        Execute a complete transition plan.

        Args:
            track_a_path: Path to track A audio file
            track_b_path: Path to track B audio file
            plan: LLM-generated transition plan (v2.0 format)
            analysis_a: Analysis data for track A
            analysis_b: Analysis data for track B

        Returns:
            Complete transition audio as numpy array
        """
        bpm = analysis_a.get("bpm", 128)
        bar_duration = self._get_bar_duration(bpm)

        logger.info(
            "Executing transition plan",
            transition_type=plan.get("transition", {}).get("type"),
            duration_bars=plan.get("transition", {}).get("duration_bars")
        )

        # 1. Load audio segments according to cut points
        audio_a = self._load_segment(
            track_a_path,
            start=plan.get("track_a", {}).get("play_from_seconds", 0),
            end=plan.get("track_a", {}).get("play_until_seconds")
        )

        audio_b = self._load_segment(
            track_b_path,
            start=plan.get("track_b", {}).get("start_from_seconds", 0),
            end=None
        )

        # 2. Time-stretch B if needed to match BPM
        bpm_b = analysis_b.get("bpm", bpm)
        if abs(bpm - bpm_b) > 0.5:
            audio_b = self._time_stretch(audio_b, bpm_b, bpm)
            logger.debug(f"Time-stretched track B from {bpm_b} to {bpm} BPM")

        # 3. Execute transition based on type
        transition_config = plan.get("transition", {})
        transition_type = transition_config.get("type", "CROSSFADE")

        try:
            if transition_type == "STEM_BLEND":
                result = self._execute_stem_blend(
                    audio_a, audio_b,
                    plan, bpm
                )
            elif transition_type == "CROSSFADE":
                result = self._execute_crossfade(audio_a, audio_b, plan, bpm)
            elif transition_type == "HARD_CUT":
                result = self._execute_hard_cut(audio_a, audio_b, plan, bpm)
            elif transition_type == "FILTER_SWEEP":
                result = self._execute_filter_sweep(audio_a, audio_b, plan, bpm)
            elif transition_type == "ECHO_OUT":
                result = self._execute_echo_out(audio_a, audio_b, plan, bpm)
            else:
                logger.warning(f"Unknown transition type: {transition_type}, using crossfade")
                result = self._execute_crossfade(audio_a, audio_b, plan, bpm)

        except Exception as e:
            logger.error(f"Transition execution failed: {e}, falling back to crossfade")
            result = self._fallback_crossfade(audio_a, audio_b, plan, bpm)

        return result

    def _execute_stem_blend(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Execute a stem-based blend transition.

        This is the professional DJ transition with:
        - Per-stem volume control
        - Proper bass swap
        - Phase-based automation
        """
        bar_duration = self._get_bar_duration(bpm)
        transition_config = plan.get("transition", {})
        stems_config = transition_config.get("stems", {})

        duration_bars = transition_config.get("duration_bars", 16)
        duration_seconds = duration_bars * bar_duration
        duration_samples = int(duration_seconds * self.sr)

        # Get transition timing
        trans_start_a = transition_config.get("start_time_in_a", len(audio_a) / self.sr - duration_seconds)
        trans_start_sample = int(trans_start_a * self.sr)

        # Separate stems
        logger.debug("Separating stems for track A")
        stems_a = self._separate_stems(audio_a)

        logger.debug("Separating stems for track B")
        stems_b = self._separate_stems(audio_b)

        # Get bass swap configuration
        bass_swap_bar = stems_config.get("bass_swap_bar", duration_bars // 2)
        bass_swap_style = stems_config.get("bass_swap_style", "instant")
        bass_swap_time = (bass_swap_bar - 1) * bar_duration

        # Apply bass swap
        stems_a_swapped, stems_b_swapped = apply_bass_swap_to_stems(
            stems_a, stems_b,
            swap_time=bass_swap_time,
            swap_duration=bass_swap_style,
            bpm=bpm,
            sr=self.sr
        )

        # Part before transition
        result_before = audio_a[:trans_start_sample]

        # Process transition zone with phase automation
        phases = stems_config.get("phases", self._get_default_phases(duration_bars))
        transition_audio = self._apply_phase_mixing(
            stems_a_swapped, stems_b_swapped,
            phases, trans_start_sample, bar_duration
        )

        # Part after transition (from B)
        trans_end_sample = trans_start_sample + duration_samples
        if duration_samples < len(audio_b):
            result_after = audio_b[duration_samples:]
        else:
            result_after = np.array([])

        # Assemble result
        result = np.concatenate([
            result_before,
            transition_audio,
            result_after
        ])

        # Normalize
        max_val = np.max(np.abs(result))
        if max_val > 1.0:
            result = result / max_val * 0.95

        return result

    def _apply_phase_mixing(
        self,
        stems_a: Dict[str, np.ndarray],
        stems_b: Dict[str, np.ndarray],
        phases: list,
        trans_start_sample: int,
        bar_duration: float
    ) -> np.ndarray:
        """
        Apply phase-based stem mixing.
        """
        bar_samples = int(bar_duration * self.sr)

        # Calculate total transition length
        last_phase = phases[-1] if phases else {"bars": [1, 16]}
        total_bars = last_phase["bars"][1]
        total_samples = total_bars * bar_samples

        transition_audio = np.zeros(total_samples, dtype=np.float32)

        for phase in phases:
            bar_start = phase["bars"][0] - 1  # Convert to 0-indexed
            bar_end = phase["bars"][1]

            phase_start = bar_start * bar_samples
            phase_end = min(bar_end * bar_samples, total_samples)
            phase_length = phase_end - phase_start

            if phase_length <= 0:
                continue

            # Mix stems for this phase
            for stem_name in ["drums", "bass", "other", "vocals"]:
                level_a = phase.get("a", {}).get(stem_name, 0)
                level_b = phase.get("b", {}).get(stem_name, 0)

                # Get stem segments
                stem_a = stems_a.get(stem_name)
                stem_b = stems_b.get(stem_name)

                # Position in original stems
                a_pos_start = trans_start_sample + phase_start
                a_pos_end = trans_start_sample + phase_end

                if stem_a is not None and a_pos_end <= len(stem_a) and level_a > 0:
                    segment_a = stem_a[a_pos_start:a_pos_end] * level_a
                    transition_audio[phase_start:phase_end] += segment_a

                if stem_b is not None and phase_end <= len(stem_b) and level_b > 0:
                    segment_b = stem_b[phase_start:phase_end] * level_b
                    transition_audio[phase_start:phase_end] += segment_b

        return transition_audio

    def _execute_crossfade(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Execute a simple volume crossfade transition.
        """
        bar_duration = self._get_bar_duration(bpm)
        transition_config = plan.get("transition", {})

        duration_bars = transition_config.get("duration_bars", 8)
        duration_seconds = duration_bars * bar_duration
        duration_samples = int(duration_seconds * self.sr)

        # Get segments
        trans_start_a = transition_config.get("start_time_in_a", len(audio_a) / self.sr - duration_seconds)
        trans_start_sample = int(trans_start_a * self.sr)

        # Before transition
        result_before = audio_a[:trans_start_sample]

        # Transition zone
        transition_segment = create_blend_transition(
            audio_a[trans_start_sample:trans_start_sample + duration_samples],
            audio_b[:duration_samples],
            transition_duration=duration_seconds,
            crossfade_type="equal_power",
            sr=self.sr
        )

        # After transition
        result_after = audio_b[duration_samples:] if duration_samples < len(audio_b) else np.array([])

        return np.concatenate([result_before, transition_segment, result_after])

    def _execute_hard_cut(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Execute a hard cut transition with optional effect.
        """
        transition_config = plan.get("transition", {})
        effects_config = transition_config.get("effects", {})

        effect_a = effects_config.get("track_a", {})
        effect_type = effect_a.get("type", "none")

        trans_start_a = transition_config.get("start_time_in_a", len(audio_a) / self.sr)
        entry_point_b = plan.get("track_b", {}).get("start_from_seconds", 0)

        if effect_type != "none":
            return create_cut_with_effect(
                audio_a=audio_a,
                audio_b=audio_b,
                cut_point_a=trans_start_a,
                entry_point_b=entry_point_b,
                effect=effect_type,
                effect_params=effect_a.get("params", {}),
                bpm=bpm,
                sr=self.sr
            )
        else:
            return create_cut_transition(
                audio_a=audio_a,
                audio_b=audio_b,
                cut_point_a=trans_start_a,
                entry_point_b=entry_point_b,
                sr=self.sr
            )

    def _execute_filter_sweep(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Execute a filter sweep transition.
        """
        bar_duration = self._get_bar_duration(bpm)
        transition_config = plan.get("transition", {})
        effects_config = transition_config.get("effects", {})

        duration_bars = transition_config.get("duration_bars", 8)
        duration_seconds = duration_bars * bar_duration

        trans_start_a = transition_config.get("start_time_in_a", len(audio_a) / self.sr - duration_seconds)
        trans_start_sample = int(trans_start_a * self.sr)
        duration_samples = int(duration_seconds * self.sr)

        # Get filter configs
        filter_a = effects_config.get("track_a", {})
        filter_b = effects_config.get("track_b", {})

        # Default filter configs if not specified
        if not filter_a.get("type"):
            filter_a = {"type": "hpf", "start": 20, "end": 2000}
        if not filter_b.get("type"):
            filter_b = {"type": "lpf", "start": 200, "end": 20000}

        # Before transition
        result_before = audio_a[:trans_start_sample]

        # Transition with filter
        transition_segment = create_filter_transition(
            audio_a=audio_a[trans_start_sample:trans_start_sample + duration_samples],
            audio_b=audio_b[:duration_samples],
            transition_duration=duration_seconds,
            filter_a=filter_a,
            filter_b=filter_b,
            crossfade=True,
            sr=self.sr
        )

        # After transition
        result_after = audio_b[duration_samples:] if duration_samples < len(audio_b) else np.array([])

        return np.concatenate([result_before, transition_segment, result_after])

    def _execute_echo_out(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Execute an echo out transition.
        """
        bar_duration = self._get_bar_duration(bpm)
        transition_config = plan.get("transition", {})
        effects_config = transition_config.get("effects", {})

        duration_bars = transition_config.get("duration_bars", 8)
        duration_seconds = duration_bars * bar_duration

        trans_start_a = transition_config.get("start_time_in_a", len(audio_a) / self.sr - duration_seconds)

        effect_a = effects_config.get("track_a", {})
        effect_type = effect_a.get("type", "delay")

        return create_echo_out_transition(
            audio_a=audio_a,
            audio_b=audio_b,
            echo_start=trans_start_a,
            echo_duration=duration_seconds,
            effect_type=effect_type,
            effect_params=effect_a.get("params", {}),
            bpm=bpm,
            sr=self.sr
        )

    def _fallback_crossfade(
        self,
        audio_a: np.ndarray,
        audio_b: np.ndarray,
        plan: Dict,
        bpm: float
    ) -> np.ndarray:
        """
        Fallback to simple crossfade if other methods fail.
        """
        logger.warning("Using fallback crossfade")
        bar_duration = self._get_bar_duration(bpm)
        duration_seconds = 8 * bar_duration  # Default 8 bars
        duration_samples = int(duration_seconds * self.sr)

        duration_samples = min(duration_samples, len(audio_a), len(audio_b))

        transition = create_blend_transition(
            audio_a[-duration_samples:],
            audio_b[:duration_samples],
            transition_duration=duration_seconds,
            crossfade_type="equal_power",
            sr=self.sr
        )

        return np.concatenate([
            audio_a[:-duration_samples],
            transition,
            audio_b[duration_samples:]
        ])

    def _load_segment(
        self,
        path: str,
        start: float,
        end: Optional[float] = None
    ) -> np.ndarray:
        """Load an audio segment from file."""
        audio, sr = sf.read(path)

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # Resample if needed
        if sr != self.sr:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sr)

        # Extract segment
        start_sample = int(start * self.sr)
        end_sample = int(end * self.sr) if end else len(audio)

        return audio[start_sample:end_sample].astype(np.float32)

    def _time_stretch(
        self,
        audio: np.ndarray,
        source_bpm: float,
        target_bpm: float
    ) -> np.ndarray:
        """Time-stretch audio to match target BPM."""
        try:
            import pyrubberband as pyrb
            ratio = source_bpm / target_bpm
            return pyrb.time_stretch(audio, self.sr, ratio)
        except ImportError:
            logger.warning("pyrubberband not available, skipping time-stretch")
            return audio

    def _separate_stems(self, audio: np.ndarray) -> Dict[str, np.ndarray]:
        """Separate audio into stems using Demucs."""
        try:
            return self.stem_separator.separate(audio, self.sr)
        except Exception as e:
            logger.warning(f"Stem separation failed: {e}")
            # Return full audio as all stems (fallback)
            return {
                "drums": audio.copy(),
                "bass": audio.copy(),
                "vocals": audio.copy(),
                "other": audio.copy()
            }

    def _get_bar_duration(self, bpm: float) -> float:
        """Calculate bar duration in seconds."""
        return (60.0 / bpm) * 4

    def _get_default_phases(self, duration_bars: int) -> list:
        """Get default 4-phase configuration."""
        phase_len = duration_bars // 4
        return [
            {
                "bars": [1, phase_len],
                "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0},
                "b": {"drums": 0.3, "bass": 0.0, "other": 0.0, "vocals": 0.0}
            },
            {
                "bars": [phase_len + 1, phase_len * 2],
                "a": {"drums": 1.0, "bass": 1.0, "other": 0.7, "vocals": 0.7},
                "b": {"drums": 0.5, "bass": 0.0, "other": 0.3, "vocals": 0.0}
            },
            {
                "bars": [phase_len * 2 + 1, phase_len * 3],
                "a": {"drums": 0.6, "bass": 0.0, "other": 0.4, "vocals": 0.3},
                "b": {"drums": 0.7, "bass": 1.0, "other": 0.6, "vocals": 0.3}
            },
            {
                "bars": [phase_len * 3 + 1, duration_bars],
                "a": {"drums": 0.2, "bass": 0.0, "other": 0.0, "vocals": 0.0},
                "b": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}
            }
        ]
