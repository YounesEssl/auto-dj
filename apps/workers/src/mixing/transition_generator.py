"""
Transition Audio Generator

Generates high-quality audio transitions between two tracks using:
- LLM-powered transition planning (Claude)
- Stem separation (Demucs htdemucs_ft)
- Time-stretching (pyrubberband)
- Beat-aligned mixing with dynamic phase transitions
- Per-stem volume curves for smooth blending
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import os

import numpy as np
import soundfile as sf
import structlog

from src.utils.audio import load_audio, get_audio_duration
from src.mixing.stems import separate_stems
from src.mixing.beatmatch import (
    stretch_to_bpm,
    find_nearest_beat,
    find_downbeat,
    calculate_stretch_ratio,
    MAX_STRETCH_RATIO,
    MIN_STRETCH_RATIO,
)
from src.mixing.plan_executor import TransitionPlanExecutor
from src.config import settings
from src.llm import plan_transition
from src.llm.planner import determine_set_position

logger = structlog.get_logger()

# Global plan executor instance (lazy initialized)
_plan_executor: Optional[TransitionPlanExecutor] = None


def get_plan_executor() -> TransitionPlanExecutor:
    """Get or create the global plan executor instance."""
    global _plan_executor
    if _plan_executor is None:
        _plan_executor = TransitionPlanExecutor(sr=SAMPLE_RATE)
    return _plan_executor

# Transition parameters
TRANSITION_BARS = 16  # Number of bars for the full transition
BEATS_PER_BAR = 4
SAMPLE_RATE = 44100

# Phase durations (in bars)
PHASE_1_BARS = 4   # Introduction: A full, B drums only
PHASE_2_BARS = 4   # Build-up: A keeps drums, B adds bass
PHASE_3_BARS = 4   # Crossover: Swap melodies and vocals
PHASE_4_BARS = 4   # Resolution: B full, A drums out


@dataclass
class TransitionResult:
    """Result of transition generation."""
    audio: np.ndarray
    sample_rate: int
    duration_ms: int
    track_a_cut_ms: int  # Where track A ends in the transition
    track_b_start_ms: int  # Where track B starts in the transition
    target_bpm: float


@dataclass
class TransitionParams:
    """Parameters for transition generation."""
    from_track_path: str
    to_track_path: str
    from_track_bpm: float
    to_track_bpm: float
    from_track_beats: List[float]
    to_track_beats: List[float]
    from_track_outro_start: float
    to_track_intro_end: float
    output_path: Optional[str] = None


def generate_transition(params: TransitionParams) -> TransitionResult:
    """
    Generate a professional-quality transition between two tracks.

    Args:
        params: TransitionParams containing all necessary track info

    Returns:
        TransitionResult with audio and timing info
    """
    logger.info(
        "Generating transition",
        from_track=params.from_track_path,
        to_track=params.to_track_path,
        from_bpm=params.from_track_bpm,
        to_bpm=params.to_track_bpm,
    )

    # Step 1: Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    # Ensure consistent sample rate
    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Step 2: Determine target BPM (use track A's BPM as reference)
    target_bpm = params.from_track_bpm

    # Step 3: Time-stretch track B to match target BPM
    stretch_ratio, within_limits = calculate_stretch_ratio(
        params.to_track_bpm, target_bpm
    )

    if not within_limits:
        logger.warning(
            "BPM difference exceeds safe limits, stretching will be clamped",
            from_bpm=params.from_track_bpm,
            to_bpm=params.to_track_bpm,
            ratio=stretch_ratio,
        )

    audio_b_stretched, actual_bpm = stretch_to_bpm(
        audio_b, SAMPLE_RATE, params.to_track_bpm, target_bpm
    )

    # Adjust track B beats for stretched audio
    beats_b_stretched = _adjust_beats_for_stretch(
        params.to_track_beats, params.to_track_bpm, actual_bpm
    )

    # Step 4: Calculate transition timing
    transition_duration_seconds = _calculate_transition_duration(target_bpm)
    transition_samples = int(transition_duration_seconds * SAMPLE_RATE)

    logger.info(
        "Transition timing",
        duration_seconds=transition_duration_seconds,
        transition_samples=transition_samples,
        target_bpm=target_bpm,
    )

    # Step 5: Find cue points on downbeats
    # Track A: Find downbeat near outro start
    a_cue_time, a_cue_beat_idx = _find_cue_point(
        params.from_track_outro_start,
        params.from_track_beats,
        'before'
    )

    # Track B: Find downbeat near intro end for starting point
    # We want track B to start at time 0, so we use intro_end as reference
    b_intro_end_adjusted = params.to_track_intro_end * (target_bpm / params.to_track_bpm)
    b_cue_time, b_cue_beat_idx = _find_cue_point(
        0,  # Start from beginning
        beats_b_stretched,
        'after'
    )

    # Step 6: Extract transition segments
    # Track A: from cue point to end of transition region
    a_segment_start = int(a_cue_time * SAMPLE_RATE)
    a_segment_end = min(
        a_segment_start + transition_samples,
        len(audio_a)
    )
    segment_a = audio_a[a_segment_start:a_segment_end]

    # Track B: from start to transition length
    b_segment_start = int(b_cue_time * SAMPLE_RATE)
    b_segment_end = min(
        b_segment_start + transition_samples,
        len(audio_b_stretched)
    )
    segment_b = audio_b_stretched[b_segment_start:b_segment_end]

    # Ensure segments are same length
    min_len = min(len(segment_a), len(segment_b))
    segment_a = segment_a[:min_len]
    segment_b = segment_b[:min_len]

    logger.info(
        "Segment lengths",
        segment_a=len(segment_a),
        segment_b=len(segment_b),
        min_len=min_len,
    )

    # Step 7: Separate stems
    logger.info("Separating stems for track A")
    stems_a = separate_stems(segment_a, SAMPLE_RATE)

    logger.info("Separating stems for track B")
    stems_b = separate_stems(segment_b, SAMPLE_RATE)

    # Step 8: Apply 4-phase transition mixing
    transition_audio = _apply_four_phase_mixing(
        stems_a, stems_b, min_len, target_bpm
    )

    # Step 9: Normalize output
    transition_audio = _normalize_audio(transition_audio)

    # Calculate timing info
    duration_ms = int(len(transition_audio) / SAMPLE_RATE * 1000)
    track_a_cut_ms = int(a_cue_time * 1000) + duration_ms
    track_b_start_ms = int(b_cue_time * 1000)

    # Save if output path provided
    if params.output_path:
        _save_audio(transition_audio, SAMPLE_RATE, params.output_path)

    result = TransitionResult(
        audio=transition_audio,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=track_a_cut_ms,
        track_b_start_ms=track_b_start_ms,
        target_bpm=target_bpm,
    )

    logger.info(
        "Transition generated successfully",
        duration_ms=duration_ms,
        track_a_cut_ms=track_a_cut_ms,
        track_b_start_ms=track_b_start_ms,
    )

    return result


def _calculate_transition_duration(bpm: float) -> float:
    """Calculate transition duration in seconds based on BPM."""
    beats = TRANSITION_BARS * BEATS_PER_BAR
    seconds_per_beat = 60.0 / bpm
    return beats * seconds_per_beat


def _adjust_beats_for_stretch(
    beats: List[float],
    original_bpm: float,
    new_bpm: float
) -> List[float]:
    """Adjust beat timestamps after time-stretching."""
    ratio = original_bpm / new_bpm
    return [beat * ratio for beat in beats]


def _find_cue_point(
    reference_time: float,
    beats: List[float],
    direction: str = 'nearest'
) -> Tuple[float, int]:
    """Find a suitable cue point (downbeat) near the reference time."""
    if not beats:
        return reference_time, -1

    # Find nearest beat to reference
    beat_time, beat_idx = find_nearest_beat(reference_time, beats, direction)

    # Find the nearest downbeat
    downbeat_time, downbeat_idx = find_downbeat(beat_idx, beats, BEATS_PER_BAR)

    return downbeat_time, downbeat_idx


def _apply_four_phase_mixing(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float
) -> np.ndarray:
    """
    Apply the 4-phase stem mixing algorithm.

    Phase 1 (bars 1-4): Introduction
        - Track A: Full (100%)
        - Track B: Drums only, fade in 0→50%

    Phase 2 (bars 5-8): Build-up
        - Track A: Drums 100%, bass fade 100→50%, other/vocals fade 100→0%
        - Track B: Drums 50→100%, bass fade 0→50%

    Phase 3 (bars 9-12): Crossover
        - Track A: Drums fade 100→50%, bass 50→0%
        - Track B: All stems rising, vocals/other fade in

    Phase 4 (bars 13-16): Resolution
        - Track A: Drums fade 50→0%
        - Track B: Full (100%)
    """
    # Calculate samples per phase
    seconds_per_beat = 60.0 / bpm
    samples_per_beat = int(seconds_per_beat * SAMPLE_RATE)
    samples_per_bar = samples_per_beat * BEATS_PER_BAR

    phase_samples = [
        samples_per_bar * PHASE_1_BARS,
        samples_per_bar * PHASE_2_BARS,
        samples_per_bar * PHASE_3_BARS,
        samples_per_bar * PHASE_4_BARS,
    ]

    # Ensure we don't exceed total samples
    total_phase_samples = sum(phase_samples)
    if total_phase_samples > total_samples:
        scale = total_samples / total_phase_samples
        phase_samples = [int(s * scale) for s in phase_samples]

    # Generate volume curves for each stem in each track
    # Format: curves[track][stem] = array of volumes (0-1)
    curves_a = _generate_curves_track_a(phase_samples, total_samples)
    curves_b = _generate_curves_track_b(phase_samples, total_samples)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        # Ensure stems are the right length
        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        # Apply volume curves
        curve_a = curves_a[stem_name]
        curve_b = curves_b[stem_name]

        mixed_stem = stem_a * curve_a + stem_b * curve_b
        output += mixed_stem

    return output


def _generate_curves_track_a(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """Generate volume curves for track A (outgoing)."""
    curves = {}

    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1 + p2
    p3_end = p2_end + p3

    # Drums: 100% → 100% → 100→50% → 50→0%
    drums = np.ones(total_samples)
    drums[p2_end:p3_end] = np.linspace(1.0, 0.5, p3)
    drums[p3_end:] = np.linspace(0.5, 0.0, total_samples - p3_end)
    curves['drums'] = drums

    # Bass: 100% → 100→50% → 50→0% → 0%
    bass = np.ones(total_samples)
    bass[p1_end:p2_end] = np.linspace(1.0, 0.5, p2)
    bass[p2_end:p3_end] = np.linspace(0.5, 0.0, p3)
    bass[p3_end:] = 0.0
    curves['bass'] = bass

    # Other: 100% → 100→0% → 0% → 0%
    other = np.ones(total_samples)
    other[p1_end:p2_end] = np.linspace(1.0, 0.0, p2)
    other[p2_end:] = 0.0
    curves['other'] = other

    # Vocals: 100% → 100→0% → 0% → 0%
    vocals = np.ones(total_samples)
    vocals[p1_end:p2_end] = np.linspace(1.0, 0.0, p2)
    vocals[p2_end:] = 0.0
    curves['vocals'] = vocals

    return curves


def _generate_curves_track_b(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """Generate volume curves for track B (incoming)."""
    curves = {}

    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1 + p2
    p3_end = p2_end + p3

    # Drums: 0→50% → 50→100% → 100% → 100%
    drums = np.zeros(total_samples)
    drums[:p1_end] = np.linspace(0.0, 0.5, p1)
    drums[p1_end:p2_end] = np.linspace(0.5, 1.0, p2)
    drums[p2_end:] = 1.0
    curves['drums'] = drums

    # Bass: 0% → 0→50% → 50→100% → 100%
    bass = np.zeros(total_samples)
    bass[p1_end:p2_end] = np.linspace(0.0, 0.5, p2)
    bass[p2_end:p3_end] = np.linspace(0.5, 1.0, p3)
    bass[p3_end:] = 1.0
    curves['bass'] = bass

    # Other: 0% → 0% → 0→100% → 100%
    other = np.zeros(total_samples)
    other[p2_end:p3_end] = np.linspace(0.0, 1.0, p3)
    other[p3_end:] = 1.0
    curves['other'] = other

    # Vocals: 0% → 0% → 0→100% → 100%
    vocals = np.zeros(total_samples)
    vocals[p2_end:p3_end] = np.linspace(0.0, 1.0, p3)
    vocals[p3_end:] = 1.0
    curves['vocals'] = vocals

    return curves


def _ensure_length(audio: np.ndarray, target_length: int) -> np.ndarray:
    """Ensure audio array is exactly the target length."""
    if len(audio) >= target_length:
        return audio[:target_length]
    else:
        # Pad with zeros
        padding = np.zeros(target_length - len(audio), dtype=audio.dtype)
        return np.concatenate([audio, padding])


def _normalize_audio(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize audio to target dB level."""
    # Calculate current RMS
    rms = np.sqrt(np.mean(audio ** 2))

    if rms == 0:
        return audio

    # Calculate target RMS from dB
    target_rms = 10 ** (target_db / 20)

    # Scale audio
    scale = target_rms / rms
    normalized = audio * scale

    # Prevent clipping
    max_val = np.max(np.abs(normalized))
    if max_val > 0.99:
        normalized = normalized * (0.99 / max_val)

    return normalized


def _save_audio(audio: np.ndarray, sample_rate: int, path: str) -> None:
    """Save audio to file."""
    # Ensure directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    # Save as WAV
    sf.write(path, audio, sample_rate)
    logger.info("Transition audio saved", path=path)


def generate_transition_from_job(job_data: dict, progress_callback: Optional[callable] = None) -> dict:
    """
    Generate transition from job payload.

    This is the main entry point for the worker queue.
    If LLM planning data is available, uses Claude to plan the transition.

    Args:
        job_data: Job payload containing transition parameters
        progress_callback: Optional callback for progress updates (stage, progress_percent)

    Returns:
        Dict with transition result info
    """
    # Build output path
    project_id = job_data['projectId']
    transition_id = job_data['transitionId']
    output_dir = Path(settings.output_path) / 'transitions' / project_id
    output_path = str(output_dir / f'{transition_id}.mp3')

    # UNIFIED ENGINE: Delegate to Draft Transition Generator
    # This ensures previews match drafts exactly (Smart Cuts, Bass Swaps, etc.)
    from src.mixing.draft_transition_generator import (
        generate_draft_transition, 
        DraftTransitionParams,
        DraftTransitionResult
    )

    # Map job data to DraftTransitionParams
    params = DraftTransitionParams(
        draft_id=f"preview_{transition_id}",
        track_a_path=settings.get_absolute_path(job_data['fromTrackPath']),
        track_b_path=settings.get_absolute_path(job_data['toTrackPath']),
        track_a_bpm=job_data['fromTrackBpm'],
        track_b_bpm=job_data['toTrackBpm'],
        track_a_beats=job_data['fromTrackBeats'],
        track_b_beats=job_data['toTrackBeats'],
        track_a_outro_start_ms=int(job_data['fromTrackOutroStart'] * 1000) if isinstance(job_data['fromTrackOutroStart'], float) else job_data['fromTrackOutroStart'],
        track_b_intro_end_ms=int(job_data['toTrackIntroEnd'] * 1000) if isinstance(job_data['toTrackIntroEnd'], float) else job_data['toTrackIntroEnd'],
        track_a_energy=job_data.get('fromTrackEnergy', 0.5),
        track_b_energy=job_data.get('toTrackEnergy', 0.5),
        track_a_duration_ms=int(job_data.get('fromTrackDuration', 300) * 1000),
        track_b_duration_ms=int(job_data.get('toTrackDuration', 300) * 1000),
        output_path=output_path
    )

    logger.info("Delegating preview to Draft Engine", transition_id=transition_id)

    # Use provided callback or fallback to logging
    callback = progress_callback if progress_callback else lambda msg, pct: logger.info(f"Progress: {pct}% - {msg}")

    # Generate using Unified Draft Engine
    result: DraftTransitionResult = generate_draft_transition(
        params,
        progress_callback=callback
    )

    # Return relative path for storage (MP3 extension)
    relative_path = f'transitions/{project_id}/{transition_id}.mp3'

    return {
        'transitionId': transition_id,
        'audioFilePath': relative_path,
        'audioDurationMs': result.transition_duration_ms,
        'trackACutMs': result.track_a_play_until_ms,
        'trackBStartMs': result.track_b_start_from_ms,
        'llmPlanUsed': True, # Draft engine always uses LLM/Smart logic
        'transitionType': result.transition_mode,
    }


def _has_llm_planning_data(job_data: dict) -> bool:
    """Check if job data contains the required fields for LLM planning."""
    required_fields = ['fromTrackKey', 'toTrackKey', 'fromTrackEnergy', 'toTrackEnergy']
    return all(field in job_data for field in required_fields)


def _get_llm_transition_plan(job_data: dict) -> Optional[dict]:
    """
    Get LLM transition plan from job data.

    Args:
        job_data: Job payload with extended track data

    Returns:
        LLM transition plan or None if planning fails
    """
    try:
        # Build track_a data
        track_a = {
            "id": job_data.get('fromTrackId', ''),
            "title": job_data.get('fromTrackTitle', 'Track A'),
            "duration_seconds": job_data.get('fromTrackDuration', 300),
            "bpm": job_data['fromTrackBpm'],
            "key": job_data['fromTrackKey'],
            "energy": job_data['fromTrackEnergy'],
            "beats": job_data['fromTrackBeats'][:20] if job_data['fromTrackBeats'] else [],  # Limit beats for API
            "intro_start": job_data.get('fromTrackIntroStart', 0),
            "outro_start": job_data['fromTrackOutroStart'],
        }

        # Build track_b data
        track_b = {
            "id": job_data.get('toTrackId', ''),
            "title": job_data.get('toTrackTitle', 'Track B'),
            "duration_seconds": job_data.get('toTrackDuration', 300),
            "bpm": job_data['toTrackBpm'],
            "key": job_data['toTrackKey'],
            "energy": job_data['toTrackEnergy'],
            "beats": job_data['toTrackBeats'][:20] if job_data['toTrackBeats'] else [],
            "intro_start": 0,
            "outro_start": job_data.get('toTrackOutroStart', 0),
        }

        # Build compatibility data
        compatibility = {
            "harmonic": job_data.get('harmonicScore', 50),
            "bpm": job_data.get('bpmScore', 50),
            "energy": job_data.get('energyScore', 50),
            "overall": job_data.get('overallScore', 50),
        }

        # Build context
        track_index = job_data.get('trackIndex', 0)
        total_tracks = job_data.get('totalTracks', 10)
        context = {
            "position_in_set": determine_set_position(track_index, total_tracks),
            "track_index": track_index,
            "total_tracks": total_tracks,
            "previous_transition_type": job_data.get('previousTransitionType'),
        }

        # Call LLM planner
        plan = plan_transition(track_a, track_b, compatibility, context)
        return plan

    except Exception as e:
        logger.error("Failed to get LLM transition plan", error=str(e))
        return None


def generate_transition_with_plan(params: TransitionParams, plan: dict) -> TransitionResult:
    """
    Generate transition using LLM-generated plan with dynamic stem phases.

    Args:
        params: TransitionParams containing all necessary track info
        plan: LLM-generated transition plan

    Returns:
        TransitionResult with audio and timing info
    """
    logger.info(
        "Generating LLM-planned transition",
        type=plan.get("transition", {}).get("type"),
        duration_bars=plan.get("transition", {}).get("duration_bars"),
    )

    # Step 1: Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    # Ensure consistent sample rate
    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Step 2: Determine target BPM
    target_bpm = params.from_track_bpm

    # Step 3: Time-stretch track B to match target BPM
    audio_b_stretched, actual_bpm = stretch_to_bpm(
        audio_b, SAMPLE_RATE, params.to_track_bpm, target_bpm
    )

    # Adjust track B beats for stretched audio
    beats_b_stretched = _adjust_beats_for_stretch(
        params.to_track_beats, params.to_track_bpm, actual_bpm
    )

    # Step 4: Get transition timing from plan
    transition_config = plan.get("transition", {})
    duration_bars = transition_config.get("duration_bars", TRANSITION_BARS)
    transition_duration_seconds = duration_bars * BEATS_PER_BAR * (60.0 / target_bpm)
    transition_samples = int(transition_duration_seconds * SAMPLE_RATE)

    # Use plan's start time if available, otherwise use outro_start
    start_time_in_a = transition_config.get("start_time_in_a", params.from_track_outro_start)

    logger.info(
        "LLM transition timing",
        duration_bars=duration_bars,
        duration_seconds=transition_duration_seconds,
        start_time=start_time_in_a,
    )

    # Step 5: Find cue points on downbeats
    a_cue_time, a_cue_beat_idx = _find_cue_point(
        start_time_in_a,
        params.from_track_beats,
        'before'
    )

    b_cue_time, b_cue_beat_idx = _find_cue_point(
        plan.get("track_b", {}).get("start_from_seconds", 0),
        beats_b_stretched,
        'after'
    )

    # Step 6: Extract transition segments
    a_segment_start = int(a_cue_time * SAMPLE_RATE)
    a_segment_end = min(a_segment_start + transition_samples, len(audio_a))
    segment_a = audio_a[a_segment_start:a_segment_end]

    b_segment_start = int(b_cue_time * SAMPLE_RATE)
    b_segment_end = min(b_segment_start + transition_samples, len(audio_b_stretched))
    segment_b = audio_b_stretched[b_segment_start:b_segment_end]

    # Ensure segments are same length
    min_len = min(len(segment_a), len(segment_b))
    segment_a = segment_a[:min_len]
    segment_b = segment_b[:min_len]

    # Step 7: Separate stems
    logger.info("Separating stems for track A (LLM plan)")
    stems_a = separate_stems(segment_a, SAMPLE_RATE)

    logger.info("Separating stems for track B (LLM plan)")
    stems_b = separate_stems(segment_b, SAMPLE_RATE)

    # Step 8: Apply LLM-planned phase mixing
    stems_config = transition_config.get("stems", {})
    if stems_config and stems_config.get("phases"):
        transition_audio = _apply_llm_phase_mixing(
            stems_a, stems_b, min_len, target_bpm, stems_config
        )
    else:
        # Fallback to default 4-phase mixing
        transition_audio = _apply_four_phase_mixing(
            stems_a, stems_b, min_len, target_bpm
        )

    # Step 9: Normalize output
    transition_audio = _normalize_audio(transition_audio)

    # Calculate timing info
    duration_ms = int(len(transition_audio) / SAMPLE_RATE * 1000)
    track_a_cut_ms = int(a_cue_time * 1000) + duration_ms
    track_b_start_ms = int(b_cue_time * 1000)

    # Save if output path provided
    if params.output_path:
        _save_audio(transition_audio, SAMPLE_RATE, params.output_path)

    result = TransitionResult(
        audio=transition_audio,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=track_a_cut_ms,
        track_b_start_ms=track_b_start_ms,
        target_bpm=target_bpm,
    )

    logger.info(
        "LLM-planned transition generated successfully",
        duration_ms=duration_ms,
        track_a_cut_ms=track_a_cut_ms,
        track_b_start_ms=track_b_start_ms,
    )

    return result


def _apply_llm_phase_mixing(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float,
    stems_config: dict
) -> np.ndarray:
    """
    Apply LLM-planned stem mixing with custom phases.

    Args:
        stems_a: Stems from track A
        stems_b: Stems from track B
        total_samples: Total number of samples
        bpm: Target BPM
        stems_config: LLM-generated stems configuration with phases

    Returns:
        Mixed audio array
    """
    phases = stems_config.get("phases", [])
    if not phases:
        return _apply_four_phase_mixing(stems_a, stems_b, total_samples, bpm)

    # Calculate samples per bar
    seconds_per_beat = 60.0 / bpm
    samples_per_bar = int(seconds_per_beat * BEATS_PER_BAR * SAMPLE_RATE)

    # Get total bars from phases
    total_bars = max(phase.get("bars", [1, 1])[1] for phase in phases)

    # Generate volume curves for each stem based on phases
    curves_a = {stem: np.zeros(total_samples) for stem in ['drums', 'bass', 'other', 'vocals']}
    curves_b = {stem: np.zeros(total_samples) for stem in ['drums', 'bass', 'other', 'vocals']}

    for phase in phases:
        bars = phase.get("bars", [1, 1])
        start_bar = bars[0] - 1  # Convert to 0-indexed
        end_bar = bars[1]

        start_sample = start_bar * samples_per_bar
        end_sample = min(end_bar * samples_per_bar, total_samples)
        phase_samples = end_sample - start_sample

        if phase_samples <= 0:
            continue

        a_levels = phase.get("a", {})
        b_levels = phase.get("b", {})

        for stem in ['drums', 'bass', 'other', 'vocals']:
            a_level = a_levels.get(stem, 1.0)
            b_level = b_levels.get(stem, 0.0)

            # Fill with constant level for this phase
            curves_a[stem][start_sample:end_sample] = a_level
            curves_b[stem][start_sample:end_sample] = b_level

    # Apply smoothing to avoid clicks
    for stem in ['drums', 'bass', 'other', 'vocals']:
        curves_a[stem] = _smooth_curve(curves_a[stem], samples_per_bar // 4)
        curves_b[stem] = _smooth_curve(curves_b[stem], samples_per_bar // 4)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        # Ensure stems are the right length
        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        # Apply volume curves
        mixed_stem = stem_a * curves_a[stem_name] + stem_b * curves_b[stem_name]
        output += mixed_stem

    return output


def _smooth_curve(curve: np.ndarray, window_size: int) -> np.ndarray:
    """Apply smoothing to a volume curve to avoid clicks."""
    if window_size <= 1:
        return curve

    # Simple moving average smoothing
    kernel = np.ones(window_size) / window_size
    smoothed = np.convolve(curve, kernel, mode='same')
    return smoothed.astype(np.float32)


def generate_hard_cut_transition(params: TransitionParams, plan: dict) -> TransitionResult:
    """
    Generate a hard cut transition (instant switch between tracks).

    Args:
        params: TransitionParams
        plan: LLM transition plan

    Returns:
        TransitionResult
    """
    logger.info("Generating hard cut transition")

    # Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Get cut point from plan
    track_a_config = plan.get("track_a", {})
    cut_time = track_a_config.get("play_until_seconds", params.from_track_outro_start)

    # Get entry point for track B
    track_b_config = plan.get("track_b", {})
    entry_time = track_b_config.get("start_from_seconds", 0)

    # Apply reverb tail to track A if specified
    effects = plan.get("transition", {}).get("effects", {})
    a_exit_effect = effects.get("track_a_exit", {})

    cut_sample = int(cut_time * SAMPLE_RATE)

    # Create short crossfade (about 50ms) to avoid click
    crossfade_samples = int(0.05 * SAMPLE_RATE)

    # Extract end of track A
    segment_a_end = audio_a[max(0, cut_sample - crossfade_samples):cut_sample]

    # Apply fade out to track A
    fade_out = np.linspace(1.0, 0.0, len(segment_a_end))
    segment_a_end = segment_a_end * fade_out

    # Extract start of track B
    entry_sample = int(entry_time * SAMPLE_RATE)
    segment_b_start = audio_b[entry_sample:entry_sample + crossfade_samples]

    # Apply fade in to track B
    fade_in = np.linspace(0.0, 1.0, len(segment_b_start))
    segment_b_start = segment_b_start * fade_in

    # Combine with crossfade
    min_len = min(len(segment_a_end), len(segment_b_start))
    transition_audio = segment_a_end[:min_len] + segment_b_start[:min_len]

    # Normalize
    transition_audio = _normalize_audio(transition_audio)

    duration_ms = int(len(transition_audio) / SAMPLE_RATE * 1000)

    if params.output_path:
        _save_audio(transition_audio, SAMPLE_RATE, params.output_path)

    return TransitionResult(
        audio=transition_audio,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=int(cut_time * 1000),
        track_b_start_ms=int(entry_time * 1000),
        target_bpm=params.from_track_bpm,
    )


def generate_crossfade_transition(params: TransitionParams, plan: dict) -> TransitionResult:
    """
    Generate a simple crossfade transition (no stem separation).

    Args:
        params: TransitionParams
        plan: LLM transition plan

    Returns:
        TransitionResult
    """
    logger.info("Generating crossfade transition")

    # Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Get transition parameters from plan
    transition_config = plan.get("transition", {})
    duration_bars = transition_config.get("duration_bars", 8)
    target_bpm = params.from_track_bpm

    # Time-stretch track B if needed
    audio_b_stretched, actual_bpm = stretch_to_bpm(
        audio_b, SAMPLE_RATE, params.to_track_bpm, target_bpm
    )

    # Calculate transition duration
    transition_duration_seconds = duration_bars * BEATS_PER_BAR * (60.0 / target_bpm)
    transition_samples = int(transition_duration_seconds * SAMPLE_RATE)

    # Get start time from plan
    start_time = transition_config.get("start_time_in_a", params.from_track_outro_start)
    start_sample = int(start_time * SAMPLE_RATE)

    # Get track B entry time
    b_entry = plan.get("track_b", {}).get("start_from_seconds", 0)
    b_entry_sample = int(b_entry * SAMPLE_RATE)

    # Extract segments
    segment_a = audio_a[start_sample:start_sample + transition_samples]
    segment_b = audio_b_stretched[b_entry_sample:b_entry_sample + transition_samples]

    # Ensure same length
    min_len = min(len(segment_a), len(segment_b))
    segment_a = segment_a[:min_len]
    segment_b = segment_b[:min_len]

    # Create crossfade curves
    fade_out = np.linspace(1.0, 0.0, min_len).astype(np.float32)
    fade_in = np.linspace(0.0, 1.0, min_len).astype(np.float32)

    # Apply crossfade
    transition_audio = segment_a * fade_out + segment_b * fade_in

    # Normalize
    transition_audio = _normalize_audio(transition_audio)

    duration_ms = int(len(transition_audio) / SAMPLE_RATE * 1000)

    if params.output_path:
        _save_audio(transition_audio, SAMPLE_RATE, params.output_path)

    return TransitionResult(
        audio=transition_audio,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=int(start_time * 1000) + duration_ms,
        track_b_start_ms=int(b_entry * 1000),
        target_bpm=target_bpm,
    )


def generate_filter_sweep_transition(params: TransitionParams, plan: dict) -> TransitionResult:
    """
    Generate a filter sweep transition (HPF on A, LPF on B).

    Args:
        params: TransitionParams
        plan: LLM transition plan

    Returns:
        TransitionResult
    """
    from src.mixing.effects.filters import create_filter_sweep

    logger.info("Generating filter sweep transition")

    # Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Get transition parameters from plan
    transition_config = plan.get("transition", {})
    duration_bars = transition_config.get("duration_bars", 8)
    target_bpm = params.from_track_bpm

    # Time-stretch track B if needed
    audio_b_stretched, actual_bpm = stretch_to_bpm(
        audio_b, SAMPLE_RATE, params.to_track_bpm, target_bpm
    )

    # Calculate transition duration
    transition_duration_seconds = duration_bars * BEATS_PER_BAR * (60.0 / target_bpm)
    transition_samples = int(transition_duration_seconds * SAMPLE_RATE)

    # Get start time from plan
    start_time = transition_config.get("start_time_in_a", params.from_track_outro_start)
    start_sample = int(start_time * SAMPLE_RATE)

    # Get track B entry time
    b_entry = plan.get("track_b", {}).get("start_from_seconds", 0)
    b_entry_sample = int(b_entry * SAMPLE_RATE)

    # Extract segments
    segment_a = audio_a[start_sample:start_sample + transition_samples]
    segment_b = audio_b_stretched[b_entry_sample:b_entry_sample + transition_samples]

    # Ensure same length
    min_len = min(len(segment_a), len(segment_b))
    segment_a = segment_a[:min_len]
    segment_b = segment_b[:min_len]

    # Get filter parameters from plan
    effects_config = transition_config.get("effects", {})
    effect_a = effects_config.get("track_a", {})
    effect_b = effects_config.get("track_b", {})

    # Apply HPF sweep to track A (removes low frequencies)
    hpf_start = effect_a.get("params", {}).get("start_freq", 20)
    hpf_end = effect_a.get("params", {}).get("end_freq", 2000)
    segment_a_filtered = create_filter_sweep(
        audio=segment_a,
        filter_type="hpf",
        start_freq=hpf_start,
        end_freq=hpf_end,
        duration=transition_duration_seconds,
        sr=SAMPLE_RATE
    )

    # Apply LPF sweep to track B (opens up frequencies)
    lpf_start = effect_b.get("params", {}).get("start_freq", 500)
    lpf_end = effect_b.get("params", {}).get("end_freq", 20000)
    segment_b_filtered = create_filter_sweep(
        audio=segment_b,
        filter_type="lpf",
        start_freq=lpf_start,
        end_freq=lpf_end,
        duration=transition_duration_seconds,
        sr=SAMPLE_RATE
    )

    # Create crossfade curves (equal power)
    t = np.linspace(0, np.pi / 2, min_len)
    fade_out = np.cos(t).astype(np.float32)
    fade_in = np.sin(t).astype(np.float32)

    # Apply crossfade
    transition_audio = segment_a_filtered * fade_out + segment_b_filtered * fade_in

    # Normalize
    transition_audio = _normalize_audio(transition_audio)

    duration_ms = int(len(transition_audio) / SAMPLE_RATE * 1000)

    if params.output_path:
        _save_audio(transition_audio, SAMPLE_RATE, params.output_path)

    return TransitionResult(
        audio=transition_audio,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=int(start_time * 1000) + duration_ms,
        track_b_start_ms=int(b_entry * 1000),
        target_bpm=target_bpm,
    )


def generate_echo_out_transition(params: TransitionParams, plan: dict) -> TransitionResult:
    """
    Generate an echo out transition (delay/reverb tail on A, then B enters).

    Args:
        params: TransitionParams
        plan: LLM transition plan

    Returns:
        TransitionResult
    """
    from src.mixing.effects.delay import create_delay_tail
    from src.mixing.effects.reverb import create_reverb_tail

    logger.info("Generating echo out transition")

    # Load audio files
    audio_a, sr_a = load_audio(params.from_track_path)
    audio_b, sr_b = load_audio(params.to_track_path)

    if sr_a != SAMPLE_RATE:
        import librosa
        audio_a = librosa.resample(audio_a, orig_sr=sr_a, target_sr=SAMPLE_RATE)
    if sr_b != SAMPLE_RATE:
        import librosa
        audio_b = librosa.resample(audio_b, orig_sr=sr_b, target_sr=SAMPLE_RATE)

    # Get transition parameters from plan
    transition_config = plan.get("transition", {})
    duration_bars = transition_config.get("duration_bars", 4)
    target_bpm = params.from_track_bpm

    # Time-stretch track B if needed
    audio_b_stretched, actual_bpm = stretch_to_bpm(
        audio_b, SAMPLE_RATE, params.to_track_bpm, target_bpm
    )

    # Calculate echo duration
    echo_duration_seconds = duration_bars * BEATS_PER_BAR * (60.0 / target_bpm)
    echo_samples = int(echo_duration_seconds * SAMPLE_RATE)

    # Get echo start time from plan
    echo_start_time = transition_config.get("start_time_in_a", params.from_track_outro_start)
    echo_start_sample = int(echo_start_time * SAMPLE_RATE)

    # Get track B entry time
    b_entry = plan.get("track_b", {}).get("start_from_seconds", 0)
    b_entry_sample = int(b_entry * SAMPLE_RATE)

    # Get effect type from plan
    effects_config = transition_config.get("effects", {})
    effect_a = effects_config.get("track_a", {})
    effect_type = effect_a.get("type", "delay")

    # Create segment A with echo tail
    segment_a_with_tail = audio_a[:echo_start_sample + echo_samples].copy()

    if effect_type == "reverb":
        # Apply reverb tail
        room_size = effect_a.get("params", {}).get("size", 0.8)
        decay = effect_a.get("params", {}).get("decay", echo_duration_seconds * 0.8)
        segment_a_with_tail = create_reverb_tail(
            audio=segment_a_with_tail,
            tail_start_sample=echo_start_sample,
            room_size=room_size,
            decay=decay,
            fade_out_duration=echo_duration_seconds * 0.5,
            sr=SAMPLE_RATE
        )
    else:
        # Apply delay tail
        beat_fraction = effect_a.get("params", {}).get("time", 0.5)
        feedback = effect_a.get("params", {}).get("feedback", 0.5)
        segment_a_with_tail = create_delay_tail(
            audio=segment_a_with_tail,
            tail_start_sample=echo_start_sample,
            bpm=target_bpm,
            beat_fraction=beat_fraction,
            feedback=feedback,
            fade_out_duration=echo_duration_seconds * 0.5,
            sr=SAMPLE_RATE
        )

    # Determine overlap point (B enters during the tail)
    b_entry_in_transition = int(echo_duration_seconds * 0.5 * SAMPLE_RATE)  # Enter halfway through tail

    # Extract B segment
    segment_b = audio_b_stretched[b_entry_sample:]

    # Build the output
    tail_length = len(segment_a_with_tail) - echo_start_sample
    overlap_start = echo_start_sample + b_entry_in_transition

    # Create output buffer
    output_length = overlap_start + len(segment_b)
    output = np.zeros(output_length, dtype=np.float32)

    # Place A with tail
    output[:len(segment_a_with_tail)] = segment_a_with_tail

    # Add B with crossfade in the overlap region
    overlap_length = len(segment_a_with_tail) - overlap_start
    if overlap_length > 0:
        # Create short crossfade for overlap
        crossfade_samples = min(overlap_length, int(1.0 * SAMPLE_RATE))
        fade_out = np.linspace(1.0, 0.0, crossfade_samples)
        fade_in = np.linspace(0.0, 1.0, crossfade_samples)

        # Apply crossfade to tail
        output[overlap_start:overlap_start + crossfade_samples] *= fade_out

        # Add B
        b_to_add = segment_b[:crossfade_samples]
        output[overlap_start:overlap_start + len(b_to_add)] += b_to_add * fade_in

        # Add rest of B
        if len(segment_b) > crossfade_samples:
            output[overlap_start + crossfade_samples:overlap_start + len(segment_b)] = segment_b[crossfade_samples:]
    else:
        # No overlap, just concatenate
        output[overlap_start:overlap_start + len(segment_b)] = segment_b

    # Normalize
    output = _normalize_audio(output)

    duration_ms = int(len(output) / SAMPLE_RATE * 1000)

    if params.output_path:
        _save_audio(output, SAMPLE_RATE, params.output_path)

    return TransitionResult(
        audio=output,
        sample_rate=SAMPLE_RATE,
        duration_ms=duration_ms,
        track_a_cut_ms=int(echo_start_time * 1000) + int(echo_duration_seconds * 1000),
        track_b_start_ms=int(b_entry * 1000),
        target_bpm=target_bpm,
    )
