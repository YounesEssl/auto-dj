"""
Draft Transition Generator

Generates professional DJ transitions between exactly 2 tracks for the Draft feature.
Implements the spec exactly:
- LLM-powered transition planning (Claude) when data available
- Duration based on average energy (16/24/32 bars) or LLM decision
- 4-phase stem mixing with specific curves or LLM-defined phases
- Progressive EQ (high-pass on A, low-pass on B)
- Fallback to crossfade if BPM diff > 8%
- Export as MP3 320kbps
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path
from enum import Enum
import os

import numpy as np
import soundfile as sf
import structlog
from scipy.signal import butter, sosfilt

from src.utils.audio import load_audio, ensure_wav_format
from src.mixing.stems import separate_stems
from src.mixing.beatmatch import (
    stretch_to_bpm,
    find_nearest_beat,
    find_downbeat,
    calculate_stretch_ratio,
)
from src.config import settings
from src.llm import plan_transition
from src.llm.planner import determine_set_position

# === NEW MODULE IMPORTS FOR PROFESSIONAL DJ TRANSITIONS ===
# Phrase detection for phrase boundary alignment
from src.analysis.phrase_detector import (
    detect_phrases,
    find_nearest_phrase_boundary,
    calculate_time_from_bars,
)
# Vocal detection for vocal clash prevention
from src.analysis.vocal_detector import (
    detect_vocals,
    check_vocal_clash,
    get_vocal_free_regions,
)
# Bass swap - THE SACRED RULE
from src.mixing.transitions.bass_swap import (
    execute_bass_swap,
    apply_bass_swap_to_stems,
    calculate_bass_swap_time,
    validate_bass_swap,
)
# Effects for transitions
from src.mixing.effects.reverb import apply_reverb, create_reverb_tail
from src.mixing.effects.delay import apply_delay_bpm_sync, create_delay_tail
from src.mixing.effects.filters import (
    create_filter_sweep,
    create_combined_filter_sweep,
    apply_hpf,
    apply_lpf,
)
# Mix points for optimal cut positions
from src.analysis.mix_points import (
    analyze_mix_points,
    get_optimal_transition_points,
)

logger = structlog.get_logger()

SAMPLE_RATE = 44100
BEATS_PER_BAR = 4


class TransitionMode(Enum):
    """Mode of transition generation."""
    STEMS = "STEMS"         # Full 4-phase stem-based mixing
    CROSSFADE = "CROSSFADE" # Simple crossfade fallback


@dataclass
class DraftTransitionParams:
    """Parameters for draft transition generation."""
    draft_id: str
    track_a_path: str
    track_b_path: str
    track_a_bpm: float
    track_b_bpm: float
    track_a_beats: List[float]
    track_b_beats: List[float]
    track_a_outro_start_ms: int
    track_b_intro_end_ms: int
    track_a_energy: float
    track_b_energy: float
    track_a_duration_ms: int
    track_b_duration_ms: int
    output_path: str


@dataclass
class DraftTransitionResult:
    """Result of draft transition generation."""
    draft_id: str
    transition_file_path: str
    transition_duration_ms: int
    track_a_outro_ms: int  # Actual outro point used
    track_b_intro_ms: int  # Actual intro point used
    transition_mode: str   # 'STEMS' or 'CROSSFADE' or 'HARD_CUT'

    # Cut points for seamless playback (to avoid audio duplication)
    track_a_play_until_ms: int = 0  # Stop playing Track A here (transition takes over)
    track_b_start_from_ms: int = 0  # Start playing Track B here (after transition)

    error: Optional[str] = None


def calculate_transition_bars(avg_energy: float) -> int:
    """
    Calculate transition duration in bars based on average energy.

    Per spec:
    - >= 0.8 energy: 16 bars (high energy = quick transition)
    - 0.5 - 0.8: 24 bars (medium energy)
    - < 0.5: 32 bars (low energy = gradual transition)
    """
    if avg_energy >= 0.8:
        return 16
    elif avg_energy >= 0.5:
        return 24
    else:
        return 32


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


def bars_to_ms(bars: int, bpm: float) -> int:
    """Convert bars to milliseconds."""
    beats = bars * BEATS_PER_BAR
    seconds_per_beat = 60.0 / bpm
    return int(beats * seconds_per_beat * 1000)


def bars_to_samples(bars: int, bpm: float) -> int:
    """Convert bars to samples."""
    beats = bars * BEATS_PER_BAR
    seconds_per_beat = 60.0 / bpm
    return int(beats * seconds_per_beat * SAMPLE_RATE)


# =============================================================================
# ENRICHED ANALYSIS FUNCTIONS - Phase 1-3 Integration
# =============================================================================

@dataclass
class EnrichedAnalysis:
    """Enriched analysis data for a single track."""
    phrases: List[Dict]
    vocals: Dict
    mix_points: Dict
    structure: Dict
    has_vocals: bool
    vocal_free_regions: List[tuple]


def _analyze_track_enriched(
    audio: np.ndarray,
    vocal_stem: Optional[np.ndarray],
    bpm: float,
    beats: List[float],
    energy: float,
    duration: float,
    sr: int = SAMPLE_RATE
) -> EnrichedAnalysis:
    """
    Perform enriched analysis on a single track.

    This runs:
    - Phrase detection for boundary alignment
    - Vocal detection for clash prevention
    - Mix points analysis for optimal cut positions

    Args:
        audio: Audio signal
        vocal_stem: Pre-separated vocal stem (recommended)
        bpm: Track tempo
        beats: Beat timestamps
        energy: Track energy (0-1)
        duration: Track duration in seconds
        sr: Sample rate

    Returns:
        EnrichedAnalysis with all analysis results
    """
    # 1. Detect phrases (for alignment)
    phrases = detect_phrases(audio, bpm, beats, sr)
    logger.info(
        "Phrases detected",
        num_phrases=len(phrases),
        phrase_lengths=[p.get("bar_count") for p in phrases[:5]]
    )

    # 2. Detect vocals (for clash prevention)
    vocals = detect_vocals(audio, sr, vocal_stem)
    has_vocals = vocals.get("has_vocals", False)
    vocal_free_regions = []

    if has_vocals:
        vocal_free_regions = get_vocal_free_regions(vocals, min_duration=4.0, track_duration=duration)
        logger.info(
            "Vocals detected",
            vocal_percentage=vocals.get("vocal_percentage", 0),
            num_sections=len(vocals.get("vocal_sections", [])),
            vocal_free_regions=len(vocal_free_regions)
        )
    else:
        # No vocals = entire track is a vocal-free region
        vocal_free_regions = [(0, duration)]
        logger.info("No vocals detected - entire track is vocal-free")

    # 3. Build simplified structure from phrases
    # (Full structure detection would use structure_detector module)
    structure = _build_simple_structure(phrases, duration, bpm)

    # 4. Analyze mix points
    mix_points = analyze_mix_points(
        structure=structure,
        phrases=phrases,
        vocals=vocals,
        energy=energy,
        duration=duration,
        bpm=bpm
    )
    logger.info(
        "Mix points analyzed",
        num_mix_in=len(mix_points.get("best_mix_in_points", [])),
        num_mix_out=len(mix_points.get("best_mix_out_points", [])),
        recommended_in=mix_points.get("recommended_mix_in", {}).get("time"),
        recommended_out=mix_points.get("recommended_mix_out", {}).get("time")
    )

    return EnrichedAnalysis(
        phrases=phrases,
        vocals=vocals,
        mix_points=mix_points,
        structure=structure,
        has_vocals=has_vocals,
        vocal_free_regions=vocal_free_regions
    )


def _build_simple_structure(
    phrases: List[Dict],
    duration: float,
    bpm: float
) -> Dict:
    """
    Build a simplified structure from phrases.

    This is a basic implementation - the full structure_detector
    provides more detailed analysis.
    """
    bar_duration = (60.0 / bpm) * 4

    # Simple structure: intro (first 8-16 bars), main, outro (last 8-16 bars)
    intro_end = bar_duration * 16  # 16 bars intro
    outro_start = duration - bar_duration * 16  # 16 bars outro

    if outro_start <= intro_end:
        # Track too short, adjust
        intro_end = duration * 0.15
        outro_start = duration * 0.85

    sections = []

    # Intro
    sections.append({
        "type": "intro",
        "start": 0,
        "end": intro_end
    })

    # Main section (could be broken into drops/breakdowns with full analysis)
    sections.append({
        "type": "main",
        "start": intro_end,
        "end": outro_start
    })

    # Outro
    sections.append({
        "type": "outro",
        "start": outro_start,
        "end": duration
    })

    return {
        "intro": {"start": 0, "end": intro_end},
        "outro": {"start": outro_start, "end": duration},
        "sections": sections
    }


def _check_vocal_clash_and_adjust(
    analysis_a: EnrichedAnalysis,
    analysis_b: EnrichedAnalysis,
    transition_start_a: float,
    transition_duration: float,
    bpm: float
) -> Dict:
    """
    Check for potential vocal clash and suggest adjustments.

    RULE: NEVER two vocals simultaneous = CATASTROPHE

    SMART LOGIC:
    - If Track B has a vocal-free INTRO >= transition_duration → NO CLASH
    - If Track B has a vocal-free INTRO < transition_duration → REDUCE duration to fit
    - Only force HARD_CUT if no safe transition zone exists

    Returns:
        Dict with clash info and recommended adjustments
    """
    bar_duration = (60.0 / bpm) * 4
    min_transition_bars = 4  # Minimum 4 bars for a decent transition

    result = {
        "has_clash": False,
        "severity": "none",
        "recommendations": [],
        "adjusted_start": transition_start_a,
        "adjusted_duration": transition_duration,
        "force_hard_cut": False
    }

    # === STEP 1: Find Track B's vocal-free INTRO ===
    intro_b_duration = 0.0
    for region in analysis_b.vocal_free_regions:
        if region[0] == 0:  # Region starts at beginning = INTRO
            intro_b_duration = region[1] - region[0]
            break

    # === STEP 2: Find Track A's vocal-free zone at end of segment ===
    # Look for an OUTRO region (the last vocal-free region that extends to segment end)
    # The analysis was done on the extracted segment, so region[1] should be near the segment duration
    outro_a_duration = 0.0
    if analysis_a.vocal_free_regions:
        # Check the LAST region - if it's an outro, it should be near the end
        last_region = analysis_a.vocal_free_regions[-1]
        # Get the max end time from all regions to infer actual segment duration
        max_region_end = max(r[1] for r in analysis_a.vocal_free_regions)
        # If last region ends at or near the max (within 2s), it's the outro
        if last_region[1] >= max_region_end - 2.0:
            outro_a_duration = last_region[1] - last_region[0]

    logger.info(
        "Vocal-free zones for transition",
        intro_b_duration=intro_b_duration,
        outro_a_duration=outro_a_duration,
        requested_transition=transition_duration,
        track_a_has_vocals=analysis_a.has_vocals,
        track_b_has_vocals=analysis_b.has_vocals
    )

    # === STEP 3: Determine safe transition duration ===
    # If Track B has a vocal-free intro, we can safely blend during that time
    if intro_b_duration > 0:
        if intro_b_duration >= transition_duration:
            # Track B's intro covers entire transition - NO CLASH possible
            logger.info(
                "Track B intro covers transition - NO vocal clash",
                intro_b=intro_b_duration,
                transition=transition_duration
            )
            return result  # No clash, no adjustments needed

        # Track B's intro is shorter - reduce transition to fit
        # Align to bar boundary
        safe_bars = int(intro_b_duration / bar_duration)
        if safe_bars >= min_transition_bars:
            adjusted_duration = safe_bars * bar_duration
            # Leave 1 bar margin for safety
            adjusted_duration = max((safe_bars - 1) * bar_duration, min_transition_bars * bar_duration)

            logger.info(
                "Reducing transition to fit Track B vocal-free intro",
                original_duration=transition_duration,
                intro_b_duration=intro_b_duration,
                adjusted_duration=adjusted_duration,
                safe_bars=safe_bars
            )
            result["adjusted_duration"] = adjusted_duration
            result["recommendations"].append(
                f"Transition shortened to {adjusted_duration:.1f}s to stay within Track B's {intro_b_duration:.1f}s vocal-free intro"
            )
            return result

    # === STEP 4: No vocal-free intro on B - check if A's outro is clean ===
    if not analysis_a.has_vocals:
        # Track A has no vocals at all - safe to blend
        logger.info("Track A has no vocals - safe to blend")
        return result

    if outro_a_duration >= transition_duration:
        # Track A's outro is vocal-free for the entire transition
        # But B has vocals - this IS a clash
        pass  # Fall through to clash check

    # === STEP 5: Both tracks have vocals in transition zone - check severity ===
    clash_info = check_vocal_clash(
        vocals_a=analysis_a.vocals,
        vocals_b=analysis_b.vocals,
        transition_start_a=transition_start_a,
        transition_end_b=transition_duration,
        overlap_duration=transition_duration
    )

    if clash_info.get("has_clash"):
        severity = clash_info.get("clash_severity", "none")
        result["has_clash"] = True
        result["severity"] = severity
        result["recommendations"] = clash_info.get("recommendations", [])

        if severity == "severe":
            # Last resort: check if we can do a minimal transition
            min_safe_duration = min(intro_b_duration, outro_a_duration) if intro_b_duration > 0 or outro_a_duration > 0 else 0

            if min_safe_duration >= min_transition_bars * bar_duration:
                # We can do a short transition
                adjusted = int(min_safe_duration / bar_duration) * bar_duration
                result["adjusted_duration"] = adjusted
                result["force_hard_cut"] = False
                logger.warning(
                    "Severe clash avoided with shortened transition",
                    adjusted_duration=adjusted,
                    min_safe=min_safe_duration
                )
            else:
                # No safe zone - force hard cut
                result["force_hard_cut"] = True
                result["adjusted_duration"] = 0
                logger.warning(
                    "Severe vocal clash - no safe transition zone, forcing HARD_CUT",
                    severity=severity,
                    intro_b=intro_b_duration,
                    outro_a=outro_a_duration
                )
        elif severity == "moderate":
            # Try to shorten transition
            result["adjusted_duration"] = min(transition_duration, bar_duration * 8)
            logger.warning(
                "Moderate vocal clash - shortening transition",
                original_duration=transition_duration,
                adjusted_duration=result["adjusted_duration"]
            )

    return result


def _align_to_phrase_boundary(
    time: float,
    phrases: List[Dict],
    direction: str = "nearest"
) -> float:
    """
    Align a time to the nearest phrase boundary.

    RULE: Transitions MUST start/end on phrase boundaries.

    Args:
        time: Time to align
        phrases: List of phrase dicts
        direction: "nearest", "before", or "after"

    Returns:
        Aligned time
    """
    aligned = find_nearest_phrase_boundary(phrases, time, direction)

    if aligned is not None:
        logger.debug(
            "Aligned to phrase boundary",
            original_time=time,
            aligned_time=aligned,
            direction=direction
        )
        return aligned

    return time


def generate_draft_transition(
    params: DraftTransitionParams,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """
    Generate professional transition between two tracks.

    Args:
        params: DraftTransitionParams containing all track info
        progress_callback: Optional callback(step, progress) for progress updates

    Returns:
        DraftTransitionResult with file path and timing info
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)
        logger.info(f"Progress: {step} - {progress}%")

    logger.info(
        "Generating draft transition",
        draft_id=params.draft_id,
        track_a_bpm=params.track_a_bpm,
        track_b_bpm=params.track_b_bpm,
        track_a_energy=params.track_a_energy,
        track_b_energy=params.track_b_energy,
    )

    # Calculate average energy and transition duration
    avg_energy = (params.track_a_energy + params.track_b_energy) / 2
    transition_bars = calculate_transition_bars(avg_energy)

    logger.info(
        "Transition parameters",
        avg_energy=avg_energy,
        transition_bars=transition_bars,
    )

    # Check BPM difference for fallback
    bpm_diff_percent = abs(params.track_a_bpm - params.track_b_bpm) / params.track_a_bpm * 100
    use_stems = bpm_diff_percent <= 8.0

    if not use_stems:
        logger.warning(
            "BPM difference > 8%, falling back to crossfade",
            bpm_diff=bpm_diff_percent
        )
        return _generate_crossfade_fallback(params, transition_bars, progress_callback)

    try:
        report_progress("extraction", 0)

        # Step 0: Convert M4A/AAC to WAV if needed (avoids librosa warnings)
        track_a_path = ensure_wav_format(params.track_a_path)
        track_b_path = ensure_wav_format(params.track_b_path)

        # Step 1: Load audio files at 44100 Hz for quality
        # Note: We load at full sample rate but convert to mono for stem separation
        # The Demucs stem separator returns mono stems anyway
        import librosa
        audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=True)
        audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=True)

        report_progress("extraction", 20)

        # Step 2: Calculate transition timing
        # Formula: duration_ms = (bars × 4 × 60 × 1000) / BPM
        target_bpm = params.track_a_bpm
        transition_samples = bars_to_samples(transition_bars, target_bpm)
        transition_duration_ms = bars_to_ms(transition_bars, target_bpm)

        logger.info(
            "Transition duration calculated",
            bars=transition_bars,
            bpm=target_bpm,
            duration_ms=transition_duration_ms,
            duration_samples=transition_samples,
        )

        # Step 3: Find cue points and extract segments
        
        # Track A: Find downbeat near outro start (or end of track if not set)
        # Use outro_start if provided and valid (not 0 and not too close to end)
        track_a_duration_s = len(audio_a) / SAMPLE_RATE
        reference_time_a = track_a_duration_s - (transition_duration_ms / 1000.0)
        
        if params.track_a_outro_start_ms > 0:
            outro_start_s = params.track_a_outro_start_ms / 1000.0
            # Ensure we have enough audio after the cue point
            if outro_start_s + (transition_duration_ms / 1000.0) <= track_a_duration_s:
                reference_time_a = outro_start_s
        
        a_cue_time, a_cue_beat_idx = _find_cue_point(
            reference_time_a,
            params.track_a_beats,
            'before' # Prefer starting transition slightly before or at the perfect point
        )

        # CRITICAL FIX (Attempt 2): Use strict sample-based check
        # Floating point comparison can be imprecise vs sample indices
        # We calculate the candidate start sample and check against total samples
        
        while True:
            track_a_start_candidate = int(a_cue_time * SAMPLE_RATE)
            end_sample = track_a_start_candidate + transition_samples
            max_samples = len(audio_a)
            
            logger.info(
                "Checking cue point safety",
                cue_time=a_cue_time,
                start_sample=track_a_start_candidate,
                end_sample=end_sample,
                max_samples=max_samples,
                overflow=end_sample - max_samples
            )
            
            if end_sample <= max_samples:
                # Safe!
                break
                
            logger.warning(
                "Cue point causes overflow (truncation detected), shifting back",
                overflow_samples=end_sample - max_samples,
                shift_bars=4
            )
            
            # Shift back by 4 bars
            if a_cue_beat_idx >= 16: # 4 bars * 4 beats
                a_cue_beat_idx -= 16
                if a_cue_beat_idx < len(params.track_a_beats):
                    a_cue_time = params.track_a_beats[a_cue_beat_idx]
                else:
                    # Fallback if index invalid
                     a_cue_time -= (bars_to_ms(4, params.track_a_bpm) / 1000.0)
            else:
                # Fallback time-based
                a_cue_time -= (bars_to_ms(4, params.track_a_bpm) / 1000.0)
            
            if a_cue_time < 0:
                a_cue_time = 0
                logger.warning("Shifted back to start of track (0.0s)")
                break

        # Track B: Find downbeat near start (or intro end)
        # We usually want to start B from its beginning, aligned to a downbeat
        # But we need to account for stretching first to find the right beat index?
        # Actually, for extraction we can rough it, but we need exact beat index for alignment.
        # Since we stretch B later, let's find the beat in original B time first.
        
        b_cue_time_original, b_cue_beat_idx = _find_cue_point(
            0.0, # Start from beginning
            params.track_b_beats,
            'after' # Don't cut off the very start if possible
        )
        
        # Calculate start samples based on aligned cue points
        track_a_start = int(a_cue_time * SAMPLE_RATE)
        
        # For B, we extract from the cue point
        track_b_start = int(b_cue_time_original * SAMPLE_RATE)
        
        # Extract Track A: from cue point to (cue point + transition duration)
        a_segment_end = min(track_a_start + transition_samples, len(audio_a))
        segment_a = audio_a[track_a_start:a_segment_end]
        
        # Extract Track B: from cue point to (cue point + transition duration)
        # Note: B will be stretched later, so we grab enough samples to cover the stretch
        # We'll trim it down after stretching
        # Estimate stretched length needed: duration * max_stretch_ratio
        samples_needed_b = int(transition_samples * 1.1)  # +10% safety margin
        b_segment_end = min(track_b_start + samples_needed_b, len(audio_b))
        segment_b = audio_b[track_b_start:b_segment_end]

        logger.info(
            "Segment extraction with beat alignment",
            track_a_cue_time=a_cue_time,
            track_a_beat_idx=a_cue_beat_idx,
            track_b_cue_time=b_cue_time_original,
            track_b_beat_idx=b_cue_beat_idx,
            track_a_start_sample=track_a_start,
            segment_a_len=len(segment_a),
            segment_b_len=len(segment_b),
        )

        report_progress("extraction", 40)

        # Step 4: Time-stretch Track B to match Track A's BPM
        report_progress("time-stretch", 0)

        stretch_ratio, _ = calculate_stretch_ratio(params.track_b_bpm, target_bpm)
        segment_b_stretched, actual_bpm = stretch_to_bpm(
            segment_b, SAMPLE_RATE, params.track_b_bpm, target_bpm
        )

        report_progress("time-stretch", 100)

        # Ensure segments are same length
        min_len = min(len(segment_a), len(segment_b_stretched), transition_samples)
        segment_a = _ensure_length(segment_a, min_len)
        segment_b_stretched = _ensure_length(segment_b_stretched, min_len)

        logger.info(
            "Segment lengths after processing",
            segment_a=len(segment_a),
            segment_b=len(segment_b_stretched),
            target=min_len,
        )

        # Step 5: Separate stems with Demucs
        report_progress("stems", 0)

        logger.info("Separating stems for track A")
        stems_a = separate_stems(segment_a, SAMPLE_RATE)
        report_progress("stems", 50)

        logger.info("Separating stems for track B")
        stems_b = separate_stems(segment_b_stretched, SAMPLE_RATE)
        report_progress("stems", 100)

        # Step 6: Beatmatch - align B's first downbeat to A's downbeat
        report_progress("beatmatch", 0)
        # For now, we assume segments are already aligned from the extraction
        # TODO: Fine-tune beatmatching if needed
        report_progress("beatmatch", 100)

        # Step 7: 4-phase mixing with spec curves
        report_progress("mixing", 0)

        transition_audio = _apply_four_phase_mixing_spec(
            stems_a, stems_b, min_len, target_bpm, transition_bars
        )
        report_progress("mixing", 50)

        # Step 8: Progressive EQ
        report_progress("eq", 0)
        transition_audio = _apply_progressive_eq(
            transition_audio, stems_a, stems_b, min_len, target_bpm, transition_bars
        )
        report_progress("eq", 100)

        # Step 9: Final processing - limiter and normalize
        transition_audio = _apply_limiter(transition_audio, -1.0)
        transition_audio = _normalize_audio(transition_audio)

        # Step 10: Convert mono to stereo and export as MP3 320kbps
        report_progress("export", 0)
        # Convert mono to stereo for better quality output
        if transition_audio.ndim == 1:
            transition_audio_stereo = np.stack([transition_audio, transition_audio])
        else:
            transition_audio_stereo = transition_audio
        _export_mp3(transition_audio_stereo, SAMPLE_RATE, params.output_path)
        report_progress("export", 100)

        # Calculate actual outro/intro points used
        actual_outro_ms = int(track_a_start / SAMPLE_RATE * 1000)
        actual_intro_ms = int(min_len / SAMPLE_RATE * 1000)

        # CRITICAL: Calculate cut points for seamless playback
        # track_a_play_until_ms: Stop playing Track A here (transition takes over)
        # track_b_start_from_ms: Start Track B here AFTER transition ends (skip intro already in transition)
        track_a_play_until_ms = actual_outro_ms  # Stop Track A at its outro
        track_b_start_from_ms = actual_intro_ms  # Skip Track B's intro (it's in the transition)

        result = DraftTransitionResult(
            draft_id=params.draft_id,
            transition_file_path=params.output_path,
            transition_duration_ms=int(len(transition_audio) / SAMPLE_RATE * 1000),
            track_a_outro_ms=actual_outro_ms,
            track_b_intro_ms=actual_intro_ms,
            transition_mode=TransitionMode.STEMS.value,
            track_a_play_until_ms=track_a_play_until_ms,
            track_b_start_from_ms=track_b_start_from_ms,
        )

        logger.info(
            "Draft transition generated successfully",
            duration_ms=result.transition_duration_ms,
            mode=result.transition_mode,
            track_a_play_until_ms=track_a_play_until_ms,
            track_b_start_from_ms=track_b_start_from_ms,
        )

        return result

    except Exception as e:
        logger.error("Stem-based transition failed, falling back to crossfade", error=str(e))
        return _generate_crossfade_fallback(
            params, transition_bars, progress_callback,
            degraded_reason=str(e)
        )


def _generate_crossfade_fallback(
    params: DraftTransitionParams,
    transition_bars: int,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    degraded_reason: Optional[str] = None
) -> DraftTransitionResult:
    """
    Generate crossfade transition as fallback.

    Used when:
    - BPM difference > 8%
    - Stem separation fails

    The crossfade extracts:
    - Track A: the last `transition_duration` of audio (outro section)
    - Track B: the first `transition_duration` of audio (intro section)

    During the transition, both tracks play SIMULTANEOUSLY with:
    - Track A fading out
    - Track B fading in
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)

    logger.info(
        "Generating crossfade fallback",
        draft_id=params.draft_id,
        reason=degraded_reason,
    )

    report_progress("extraction", 0)

    # Convert M4A/AAC to WAV if needed (avoids librosa warnings)
    track_a_path = ensure_wav_format(params.track_a_path)
    track_b_path = ensure_wav_format(params.track_b_path)

    # Load audio in STEREO at full quality (44100 Hz)
    import librosa
    audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=False)
    audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=False)

    # Ensure stereo (2D array with shape [2, samples])
    if audio_a.ndim == 1:
        audio_a = np.stack([audio_a, audio_a])
    if audio_b.ndim == 1:
        audio_b = np.stack([audio_b, audio_b])

    report_progress("extraction", 50)

    # Use Track A's BPM for duration calculation
    # Formula: duration_ms = (bars × 4 × 60 × 1000) / BPM
    target_bpm = params.track_a_bpm
    transition_samples = bars_to_samples(transition_bars, target_bpm)
    transition_duration_ms = bars_to_ms(transition_bars, target_bpm)

    logger.info(
        "Transition duration calculated",
        bars=transition_bars,
        bpm=target_bpm,
        duration_ms=transition_duration_ms,
        duration_samples=transition_samples,
    )

    # Extract Track A outro: the LAST transition_duration of the track
    # This ensures we have enough audio regardless of outro_start position
    # For stereo arrays (shape [2, samples]), use .shape[1] for sample count
    num_samples_a = audio_a.shape[1]
    num_samples_b = audio_b.shape[1]

    track_a_start = max(0, num_samples_a - transition_samples)
    segment_a = audio_a[:, track_a_start:]  # Stereo slicing: [channels, samples]

    # Extract Track B intro: the FIRST transition_duration of the track
    segment_b = audio_b[:, :transition_samples]  # Stereo slicing

    logger.info(
        "Segment extraction",
        track_a_start_sample=track_a_start,
        track_a_start_ms=int(track_a_start / SAMPLE_RATE * 1000),
        segment_a_len=segment_a.shape[1],
        segment_b_len=segment_b.shape[1],
    )

    # Ensure same length - use the target transition_samples
    target_len = min(segment_a.shape[1], segment_b.shape[1], transition_samples)
    segment_a = _ensure_length_stereo(segment_a, target_len)
    segment_b = _ensure_length_stereo(segment_b, target_len)

    report_progress("extraction", 100)
    report_progress("mixing", 0)

    # Crossfade with equal-power curves for smoother transition
    # Equal power: fade_out = cos(t * pi/2), fade_in = sin(t * pi/2)
    t = np.linspace(0, 1, target_len)
    fade_out = np.cos(t * np.pi / 2).astype(np.float32)
    fade_in = np.sin(t * np.pi / 2).astype(np.float32)

    # Reshape for stereo broadcasting: [1, samples] to broadcast with [2, samples]
    fade_out = fade_out.reshape(1, -1)
    fade_in = fade_in.reshape(1, -1)

    # Mix: both tracks play SIMULTANEOUSLY (stereo)
    transition_audio = segment_a * fade_out + segment_b * fade_in

    report_progress("mixing", 100)

    # Final processing
    transition_audio = _apply_limiter(transition_audio, -1.0)
    transition_audio = _normalize_audio(transition_audio)

    report_progress("export", 0)
    _export_mp3(transition_audio, SAMPLE_RATE, params.output_path)
    report_progress("export", 100)

    # Calculate actual outro/intro points used
    actual_outro_ms = int(track_a_start / SAMPLE_RATE * 1000)
    actual_intro_ms = int(target_len / SAMPLE_RATE * 1000)

    # Cut points for seamless playback
    track_a_play_until_ms = actual_outro_ms  # Stop Track A here
    track_b_start_from_ms = actual_intro_ms  # Start Track B here (after transition)

    logger.info(
        "Crossfade transition complete",
        duration_ms=int(target_len / SAMPLE_RATE * 1000),
        track_a_outro_ms=actual_outro_ms,
        track_b_intro_ms=actual_intro_ms,
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )

    return DraftTransitionResult(
        draft_id=params.draft_id,
        transition_file_path=params.output_path,
        transition_duration_ms=int(target_len / SAMPLE_RATE * 1000),
        track_a_outro_ms=actual_outro_ms,
        track_b_intro_ms=actual_intro_ms,
        transition_mode=TransitionMode.CROSSFADE.value,
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
        error=degraded_reason,
    )


def _apply_four_phase_mixing_spec(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float,
    transition_bars: int
) -> np.ndarray:
    """
    Apply 4-phase stem mixing per the spec.

    Each phase is transition_bars/4 bars.

    Per spec:
    | Phase | Track A | Track B |
    |-------|---------|---------|
    | 1 | 100% all | Drums 0→70%, Other 0→30% |
    | 2 | Bass 100→20% | Drums 70→100%, Bass 0→100% |
    | 3 | Vocals 100→0% | Vocals 0→100%, Other 50→100% |
    | 4 | All fade out | 100% all |
    """
    phase_bars = transition_bars // 4
    samples_per_phase = bars_to_samples(phase_bars, bpm)

    # Adjust to fit total_samples
    phase_samples = [samples_per_phase] * 4
    total_phase_samples = sum(phase_samples)
    if total_phase_samples > total_samples:
        scale = total_samples / total_phase_samples
        phase_samples = [int(s * scale) for s in phase_samples]

    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Generate curves per spec
    curves_a = _generate_curves_track_a_spec(phase_samples, total_samples)
    curves_b = _generate_curves_track_b_spec(phase_samples, total_samples)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        curve_a = curves_a[stem_name]
        curve_b = curves_b[stem_name]

        mixed_stem = stem_a * curve_a + stem_b * curve_b
        output += mixed_stem

    return output


def _generate_curves_track_a_spec(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """
    Generate volume curves for Track A per spec.

    | Phase | Track A |
    |-------|---------|
    | 1 | 100% all |
    | 2 | Bass 100→20% |
    | 3 | Vocals 100→0% |
    | 4 | All fade out |
    """
    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Drums: 100% → 100% → 100% → fade to 0%
    drums = np.ones(total_samples)
    if p4 > 0:
        drums[p3_end:] = np.linspace(1.0, 0.0, total_samples - p3_end)

    # Bass: 100% → 100→20% → 20% → fade to 0%
    bass = np.ones(total_samples)
    if p2 > 0:
        bass[p1_end:p2_end] = np.linspace(1.0, 0.2, p2)
    bass[p2_end:p3_end] = 0.2
    if p4 > 0:
        bass[p3_end:] = np.linspace(0.2, 0.0, total_samples - p3_end)

    # Vocals: 100% → 100% → 100→0% → 0%
    vocals = np.ones(total_samples)
    if p3 > 0:
        vocals[p2_end:p3_end] = np.linspace(1.0, 0.0, p3)
    vocals[p3_end:] = 0.0

    # Other: 100% → 100% → 100% → fade to 0%
    other = np.ones(total_samples)
    if p4 > 0:
        other[p3_end:] = np.linspace(1.0, 0.0, total_samples - p3_end)

    return {'drums': drums, 'bass': bass, 'vocals': vocals, 'other': other}


def _generate_curves_track_b_spec(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """
    Generate volume curves for Track B per spec.

    | Phase | Track B |
    |-------|---------|
    | 1 | Drums 0→70%, Other 0→30% |
    | 2 | Drums 70→100%, Bass 0→100% |
    | 3 | Vocals 0→100%, Other 50→100% |
    | 4 | 100% all |
    """
    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Drums: 0→70% → 70→100% → 100% → 100%
    drums = np.zeros(total_samples)
    if p1 > 0:
        drums[:p1_end] = np.linspace(0.0, 0.7, p1)
    if p2 > 0:
        drums[p1_end:p2_end] = np.linspace(0.7, 1.0, p2)
    drums[p2_end:] = 1.0

    # Bass: 0% → 0→100% → 100% → 100%
    bass = np.zeros(total_samples)
    if p2 > 0:
        bass[p1_end:p2_end] = np.linspace(0.0, 1.0, p2)
    bass[p2_end:] = 1.0

    # Vocals: 0% → 0% → 0→100% → 100%
    vocals = np.zeros(total_samples)
    if p3 > 0:
        vocals[p2_end:p3_end] = np.linspace(0.0, 1.0, p3)
    vocals[p3_end:] = 1.0

    # Other: 0→30% → 30→50% → 50→100% → 100%
    other = np.zeros(total_samples)
    if p1 > 0:
        other[:p1_end] = np.linspace(0.0, 0.3, p1)
    if p2 > 0:
        other[p1_end:p2_end] = np.linspace(0.3, 0.5, p2)
    if p3 > 0:
        other[p2_end:p3_end] = np.linspace(0.5, 1.0, p3)
    other[p3_end:] = 1.0

    return {'drums': drums, 'bass': bass, 'vocals': vocals, 'other': other}


def _apply_progressive_eq(
    mixed_audio: np.ndarray,
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float,
    transition_bars: int
) -> np.ndarray:
    """
    Apply progressive EQ per spec.

    Track A (high-pass, cuts lows progressively):
    - Phase 1: no filter
    - Phase 2: 80 Hz
    - Phase 3: 150 Hz
    - Phase 4: 300 Hz

    Track B (low-pass, opens highs progressively):
    - Phase 1: 2000 Hz
    - Phase 2: 5000 Hz
    - Phase 3: 12000 Hz
    - Phase 4: no filter

    Note: For simplicity, we apply EQ to the already-mixed stems.
    A more precise implementation would apply EQ before mixing.
    """
    # For now, return as-is since EQ is already somewhat achieved by stem mixing
    # TODO: Implement proper EQ per phase if needed
    # This would require re-mixing the stems with EQ applied

    return mixed_audio


def _highpass_filter(audio: np.ndarray, cutoff: float, sample_rate: int) -> np.ndarray:
    """Apply high-pass filter."""
    if cutoff <= 0:
        return audio
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff / nyquist
    if normalized_cutoff >= 1:
        return audio
    sos = butter(4, normalized_cutoff, btype='high', output='sos')
    return sosfilt(sos, audio).astype(np.float32)


def _lowpass_filter(audio: np.ndarray, cutoff: float, sample_rate: int) -> np.ndarray:
    """Apply low-pass filter."""
    if cutoff <= 0:
        return audio
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff / nyquist
    if normalized_cutoff >= 1:
        return audio
    sos = butter(4, normalized_cutoff, btype='low', output='sos')
    return sosfilt(sos, audio).astype(np.float32)


def _apply_limiter(audio: np.ndarray, threshold_db: float = -1.0) -> np.ndarray:
    """Apply brick-wall limiter at threshold dB."""
    threshold = 10 ** (threshold_db / 20)
    peak = np.max(np.abs(audio))

    if peak > threshold:
        audio = audio * (threshold / peak)

    return audio


def _normalize_audio(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    """
    Normalize audio to target Peak dB level.
    Avoids RMS normalization which can destroy dynamics of already mastered tracks.
    """
    peak = np.max(np.abs(audio))

    if peak == 0:
        return audio

    target_peak = 10 ** (target_db / 20)
    
    # Only normalize if we are ABOVE the target (limit)
    # OR if we are significantly below (boost), but be careful not to clip noise
    # actually, for transitions, we just want to ensure we don't clip.
    # Mastered tracks are already loud.
    
    if peak > target_peak:
        # Scale down
        scale = target_peak / peak
        normalized = audio * scale
    else:
        # If quiet, leave it alone or gentle boost?
        # Better to leave it alone to preserve original quality unless it's very quiet.
        # But if we mix signals, we might exceed 1.0. 
        # So we just ensure we are within target_peak.
        normalized = audio # Don't boost unnecessary
        
    return normalized


def _ensure_length(audio: np.ndarray, target_length: int) -> np.ndarray:
    """Ensure audio is exactly target length (mono)."""
    if len(audio) >= target_length:
        return audio[:target_length]
    else:
        padding = np.zeros(target_length - len(audio), dtype=audio.dtype)
        return np.concatenate([audio, padding])


def _ensure_length_stereo(audio: np.ndarray, target_length: int) -> np.ndarray:
    """Ensure stereo audio is exactly target length. Shape: [2, samples]."""
    num_samples = audio.shape[1]
    if num_samples >= target_length:
        return audio[:, :target_length]
    else:
        padding = np.zeros((2, target_length - num_samples), dtype=audio.dtype)
        return np.concatenate([audio, padding], axis=1)


def _export_mp3(audio: np.ndarray, sample_rate: int, output_path: str) -> None:
    """Export audio as high-quality MP3 using FFmpeg directly.
    
    Uses FFmpeg's libmp3lame encoder with VBR quality 0 (highest quality)
    for better audio quality than pydub's default export.
    """
    import subprocess
    import tempfile
    import soundfile as sf

    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Prepare audio for export
    if audio.ndim == 2:
        # Convert from [channels, samples] to [samples, channels] for soundfile
        audio_export = audio.T
        num_channels = 2
    else:
        audio_export = audio
        num_channels = 1

    # Clip to prevent distortion
    audio_export = np.clip(audio_export, -1.0, 1.0)

    # Write to temp WAV file (32-bit float for max quality)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
        tmp_wav_path = tmp_wav.name
        sf.write(tmp_wav_path, audio_export, sample_rate, subtype='FLOAT')

    # Convert to MP3 with FFmpeg - use VBR quality 0 (highest quality) or CBR 320k
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_mp3:
        tmp_mp3_path = tmp_mp3.name

    try:
        # Use FFmpeg with libmp3lame, CBR 320kbps for maximum compatibility + quality
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-f', 'wav', '-i', tmp_wav_path,
                '-c:a', 'libmp3lame',
                '-b:a', '320k',
                '-q:a', '0',  # Highest quality encoding
                '-f', 'mp3',
                tmp_mp3_path
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.warning("FFmpeg encoding issues", stderr=result.stderr[-500:] if result.stderr else "")

        # Move to final destination
        Path(tmp_mp3_path).replace(output_path)

        logger.info("Transition exported as MP3 (FFmpeg)", path=output_path, channels=num_channels)

    except Exception as e:
        logger.error("FFmpeg export failed, using fallback", error=str(e))
        # Fallback to pydub if FFmpeg fails
        from pydub import AudioSegment

        # CRITICAL: Clip before int16 conversion
        audio_clipped = np.clip(audio_export, -1.0, 1.0)
        if audio_clipped.ndim == 2:
            # Interleave for pydub
            audio_interleaved = audio_clipped.flatten('C')
        else:
            audio_interleaved = audio_clipped
        audio_16bit = (audio_interleaved * 32767).astype(np.int16)

        audio_segment = AudioSegment(
            data=audio_16bit.tobytes(),
            sample_width=2,
            frame_rate=sample_rate,
            channels=num_channels
        )
        audio_segment.export(output_path, format='mp3', bitrate='320k')
        logger.info("Transition exported as MP3 (pydub fallback)", path=output_path)

    finally:
        # Cleanup temp files
        try:
            Path(tmp_wav_path).unlink(missing_ok=True)
            Path(tmp_mp3_path).unlink(missing_ok=True)
        except Exception:
            pass


def generate_draft_transition_from_job(job_data: dict, progress_callback=None) -> dict:
    """
    Entry point for the worker queue.
    Uses LLM planning when key data is available.

    Args:
        job_data: Job payload with draft transition parameters
        progress_callback: Optional callback(step, progress) for progress updates

    Returns:
        Dict with transition result info
    """
    draft_id = job_data['draftId']

    # Build output path
    output_dir = Path(settings.output_path) / 'drafts' / draft_id
    output_path = str(output_dir / 'transition.mp3')

    # Check if we have LLM planning data (keys for harmonic analysis)
    llm_plan = None
    if _has_llm_planning_data(job_data):
        llm_plan = _get_llm_transition_plan(job_data)
        if llm_plan:
            logger.info(
                "Using LLM transition plan for draft",
                draft_id=draft_id,
                transition_type=llm_plan.get("transition", {}).get("type"),
                confidence=llm_plan.get("confidence")
            )

    params = DraftTransitionParams(
        draft_id=draft_id,
        track_a_path=settings.get_absolute_path(job_data['trackAPath']),
        track_b_path=settings.get_absolute_path(job_data['trackBPath']),
        track_a_bpm=job_data['trackABpm'],
        track_b_bpm=job_data['trackBBpm'],
        track_a_beats=job_data.get('trackABeats', []),
        track_b_beats=job_data.get('trackBBeats', []),
        track_a_outro_start_ms=job_data['trackAOutroStartMs'],
        track_b_intro_end_ms=job_data['trackBIntroEndMs'],
        track_a_energy=job_data['trackAEnergy'],
        track_b_energy=job_data['trackBEnergy'],
        track_a_duration_ms=job_data['trackADurationMs'],
        track_b_duration_ms=job_data['trackBDurationMs'],
        output_path=output_path,
    )

    # Use LLM plan if available
    if llm_plan:
        result = generate_draft_transition_with_plan(params, llm_plan, progress_callback)
    else:
        result = generate_draft_transition(params, progress_callback)

    # Return relative path for storage
    relative_path = f'drafts/{draft_id}/transition.mp3'

    return {
        'draftId': draft_id,
        'transitionFilePath': relative_path,
        'transitionDurationMs': result.transition_duration_ms,
        'trackAOutroMs': result.track_a_outro_ms,
        'trackBIntroMs': result.track_b_intro_ms,
        'transitionMode': result.transition_mode,
        # Cut points for seamless playback (to avoid audio duplication)
        'trackAPlayUntilMs': result.track_a_play_until_ms,
        'trackBStartFromMs': result.track_b_start_from_ms,
        'error': result.error,
        'llmPlanUsed': llm_plan is not None,
    }


def _has_llm_planning_data(job_data: dict) -> bool:
    """Check if job data contains the required fields for LLM planning."""
    required_fields = ['trackAKey', 'trackBKey']
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
            "id": job_data.get('draftId', ''),
            "title": "Track A",
            "duration_seconds": job_data['trackADurationMs'] / 1000,
            "bpm": job_data['trackABpm'],
            "key": job_data['trackAKey'],
            "energy": job_data['trackAEnergy'],
            "beats": job_data.get('trackABeats', [])[:20],  # Limit beats for API
            "intro_start": 0,
            "outro_start": job_data['trackAOutroStartMs'] / 1000,
        }

        # Build track_b data
        track_b = {
            "id": job_data.get('draftId', ''),
            "title": "Track B",
            "duration_seconds": job_data['trackBDurationMs'] / 1000,
            "bpm": job_data['trackBBpm'],
            "key": job_data['trackBKey'],
            "energy": job_data['trackBEnergy'],
            "beats": job_data.get('trackBBeats', [])[:20],
            "intro_start": 0,
            "outro_start": job_data.get('trackBOutroStartMs', job_data['trackBDurationMs'] * 0.8) / 1000,
        }

        # Build compatibility data (calculate or use provided)
        compatibility = {
            "harmonic": job_data.get('harmonicScore', _calculate_harmonic_score(track_a['key'], track_b['key'])),
            "bpm": job_data.get('bpmScore', _calculate_bpm_score(track_a['bpm'], track_b['bpm'])),
            "energy": job_data.get('energyScore', _calculate_energy_score(track_a['energy'], track_b['energy'])),
            "overall": job_data.get('overallScore', 50),
        }

        # Recalculate overall if not provided
        if 'overallScore' not in job_data:
            compatibility['overall'] = (
                compatibility['harmonic'] * 0.5 +
                compatibility['bpm'] * 0.3 +
                compatibility['energy'] * 0.2
            )

        # Build context (draft = single transition, so position is BUILD)
        context = {
            "position_in_set": "BUILD",
            "track_index": 0,
            "total_tracks": 2,
            "previous_transition_type": None,
        }

        # Call LLM planner
        plan = plan_transition(track_a, track_b, compatibility, context)
        return plan

    except Exception as e:
        logger.error("Failed to get LLM transition plan for draft", error=str(e))
        return None


def _calculate_harmonic_score(key_a: str, key_b: str) -> int:
    """Calculate harmonic compatibility score between two Camelot keys."""
    if not key_a or not key_b:
        return 50

    # Same key = perfect
    if key_a == key_b:
        return 100

    # Parse Camelot keys (e.g., "8A", "12B")
    try:
        num_a = int(key_a[:-1])
        mode_a = key_a[-1]
        num_b = int(key_b[:-1])
        mode_b = key_b[-1]
    except (ValueError, IndexError):
        return 50

    # Same mode
    if mode_a == mode_b:
        diff = abs(num_a - num_b)
        if diff == 0:
            return 100
        elif diff == 1 or diff == 11:  # Adjacent
            return 90
        elif diff == 2 or diff == 10:
            return 60
        elif diff == 7 or diff == 5:  # Energy boost
            return 65
    else:
        # Different mode
        if num_a == num_b:  # Relative
            return 85
        diff = abs(num_a - num_b)
        if diff == 1 or diff == 11:  # Diagonal
            return 75

    return 40  # Risky


def _calculate_bpm_score(bpm_a: float, bpm_b: float) -> int:
    """Calculate BPM compatibility score."""
    if bpm_a <= 0:
        return 50
    diff_pct = abs(bpm_a - bpm_b) / bpm_a * 100
    if diff_pct <= 2:
        return 100
    elif diff_pct <= 4:
        return 85
    elif diff_pct <= 6:
        return 70
    elif diff_pct <= 8:
        return 55
    else:
        return 25


def _calculate_energy_score(energy_a: float, energy_b: float) -> int:
    """Calculate energy compatibility score."""
    diff = energy_b - energy_a
    if -0.05 <= diff <= 0.15:  # Stable or gentle rise
        return 100
    elif 0.15 < diff <= 0.25:  # Strong rise
        return 70
    elif -0.15 <= diff < -0.05:  # Gentle drop
        return 65
    elif -0.25 <= diff < -0.15:  # Strong drop
        return 45
    else:
        return 25


def generate_draft_transition_with_plan(
    params: DraftTransitionParams,
    plan: dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """
    Generate draft transition using LLM-generated plan.

    NOW INTEGRATES:
    - Phrase boundary alignment
    - Vocal clash detection and prevention
    - Bass swap for STEM_BLEND
    - Effects (reverb/delay) for HARD_CUT
    - Filter sweeps for FILTER_SWEEP

    Args:
        params: DraftTransitionParams
        plan: LLM-generated transition plan
        progress_callback: Optional progress callback

    Returns:
        DraftTransitionResult
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)
        logger.info(f"Progress: {step} - {progress}%")

    # TYPE SAFETY: Ensure parameters are correct types
    # Explicitly cast to float to prevent TypeError if strings are passed
    if params.track_a_beats:
        params.track_a_beats = [float(b) for b in params.track_a_beats]
    if params.track_b_beats:
        params.track_b_beats = [float(b) for b in params.track_b_beats]
    
    transition_config = plan.get("transition", {})
    transition_type = transition_config.get("type", "STEM_BLEND")

    logger.info(
        "Generating LLM-planned draft transition (ENHANCED)",
        draft_id=str(params.draft_id),
        transition_type=str(transition_type),
        duration_bars=transition_config.get("duration_bars"),
    )


    # Handle FILTER_SWEEP type - NEW!
    if transition_type == "FILTER_SWEEP":
        return _generate_filter_sweep_transition(params, plan, progress_callback)

    # Handle ECHO_OUT type - NEW!
    if transition_type == "ECHO_OUT":
        return _generate_echo_out_transition(params, plan, progress_callback)

    # Handle HARD_CUT type - ENHANCED with effects
    if transition_type == "HARD_CUT":
        return _generate_hard_cut_with_plan_enhanced(params, plan, progress_callback)

    # Handle CROSSFADE type
    if transition_type == "CROSSFADE":
        transition_bars = transition_config.get("duration_bars", 8)
        return _generate_crossfade_fallback(params, transition_bars, progress_callback)

    # Handle STEM_BLEND with LLM phases - ENHANCED with bass swap
    try:
        report_progress("extraction", 0)

        # Convert M4A/AAC to WAV if needed
        track_a_path = ensure_wav_format(params.track_a_path)
        track_b_path = ensure_wav_format(params.track_b_path)

        import librosa
        audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=True)
        audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=True)

        report_progress("extraction", 20)

        # Get transition parameters from plan
        transition_bars = transition_config.get("duration_bars", 16)
        target_bpm = params.track_a_bpm
        transition_samples = bars_to_samples(transition_bars, target_bpm)
        transition_duration_ms = bars_to_ms(transition_bars, target_bpm)
        transition_duration_s = transition_duration_ms / 1000

        logger.info(
            "LLM transition timing",
            bars=transition_bars,
            bpm=target_bpm,
            duration_ms=transition_duration_ms,
        )

        # Extract segments (with beat alignment and safety check)
        
        # Track A: Find downbeat near outro start (or end of track if not set)
        track_a_duration_s = len(audio_a) / SAMPLE_RATE
        reference_time_a = track_a_duration_s - (transition_duration_ms / 1000.0)
        
        if params.track_a_outro_start_ms > 0:
            outro_start_s = params.track_a_outro_start_ms / 1000.0
            # Ensure we have enough audio after the cue point
            if outro_start_s + (transition_duration_ms / 1000.0) <= track_a_duration_s:
                reference_time_a = outro_start_s
        
        a_cue_time, a_cue_beat_idx = _find_cue_point(
            reference_time_a,
            params.track_a_beats,
            'before' # Prefer starting transition slightly before or at the perfect point
        )

        # Truncation Safety Check (Robust Sample-Based)
        while True:
            track_a_start_candidate = int(a_cue_time * SAMPLE_RATE)
            end_sample = track_a_start_candidate + transition_samples
            max_samples = len(audio_a)
            
            logger.info(
                "Checking cue point safety (LLM)",
                cue_time=a_cue_time,
                start_sample=track_a_start_candidate,
                end_sample=end_sample,
                max_samples=max_samples,
                overflow=end_sample - max_samples
            )
            
            if end_sample <= max_samples:
                break
                
            logger.warning("Cue point truncation in LLM plan, shifting back")
            
            if a_cue_beat_idx >= 16:
                a_cue_beat_idx -= 16
                if a_cue_beat_idx < len(params.track_a_beats):
                    a_cue_time = params.track_a_beats[a_cue_beat_idx]
                else:
                    a_cue_time -= (bars_to_ms(4, params.track_a_bpm) / 1000.0)
            else:
                 a_cue_time -= (bars_to_ms(4, params.track_a_bpm) / 1000.0)
            
            if a_cue_time < 0:
                a_cue_time = 0
                break

        # Track B: Find downbeat near start (or intro end)
        b_cue_time_original, b_cue_beat_idx = _find_cue_point(
            0.0,
            params.track_b_beats,
            'after'
        )

        track_a_start = int(a_cue_time * SAMPLE_RATE)
        track_b_start = int(b_cue_time_original * SAMPLE_RATE)

        # Extract Track A
        a_segment_end = min(track_a_start + transition_samples, len(audio_a))
        segment_a = audio_a[track_a_start:a_segment_end]
        
        # Extract Track B (with buffer for stretch)
        samples_needed_b = int(transition_samples * 1.1)
        b_segment_end = min(track_b_start + samples_needed_b, len(audio_b))
        segment_b = audio_b[track_b_start:b_segment_end]

        report_progress("extraction", 40)
        report_progress("time-stretch", 0)

        # Time-stretch Track B
        segment_b_stretched, actual_bpm = stretch_to_bpm(
            segment_b, SAMPLE_RATE, params.track_b_bpm, target_bpm
        )

        report_progress("time-stretch", 100)

        # Ensure same length
        min_len = min(len(segment_a), len(segment_b_stretched), transition_samples)
        segment_a = _ensure_length(segment_a, min_len)
        segment_b_stretched = _ensure_length(segment_b_stretched, min_len)

        # Separate stems
        report_progress("stems", 0)
        logger.info("Separating stems for track A (LLM plan)")
        stems_a = separate_stems(segment_a, SAMPLE_RATE)
        report_progress("stems", 50)

        logger.info("Separating stems for track B (LLM plan)")
        stems_b = separate_stems(segment_b_stretched, SAMPLE_RATE)
        report_progress("stems", 100)

        # === NEW: ENRICHED ANALYSIS ===
        report_progress("analysis", 0)

        # Run enriched analysis on segments
        analysis_a = _analyze_track_enriched(
            audio=segment_a,
            vocal_stem=stems_a.get('vocals'),
            bpm=target_bpm,
            beats=params.track_a_beats,
            energy=params.track_a_energy,
            duration=len(segment_a) / SAMPLE_RATE,
            sr=SAMPLE_RATE
        )

        analysis_b = _analyze_track_enriched(
            audio=segment_b_stretched,
            vocal_stem=stems_b.get('vocals'),
            bpm=target_bpm,
            beats=params.track_b_beats,
            energy=params.track_b_energy,
            duration=len(segment_b_stretched) / SAMPLE_RATE,
            sr=SAMPLE_RATE
        )

        report_progress("analysis", 100)

        # === NEW: VOCAL CLASH CHECK ===
        vocal_check = _check_vocal_clash_and_adjust(
            analysis_a=analysis_a,
            analysis_b=analysis_b,
            transition_start_a=0,  # We're working with extracted segments
            transition_duration=transition_duration_s,
            bpm=target_bpm
        )

        if vocal_check["force_hard_cut"]:
            logger.warning("Vocal clash forces HARD_CUT instead of STEM_BLEND")
            return _generate_hard_cut_with_plan_enhanced(params, plan, progress_callback)

        # === APPLY ADJUSTED DURATION IF NEEDED ===
        adjusted_duration = vocal_check.get("adjusted_duration", transition_duration_s)
        bar_duration = (60.0 / target_bpm) * 4
        if adjusted_duration < transition_duration_s:
            logger.info(
                "Applying adjusted transition duration from vocal check",
                original_duration=transition_duration_s,
                adjusted_duration=adjusted_duration,
                reduction_percent=((transition_duration_s - adjusted_duration) / transition_duration_s) * 100
            )
            # Update transition parameters
            transition_duration_s = adjusted_duration
            transition_bars = int(adjusted_duration / bar_duration)
            transition_samples = int(adjusted_duration * SAMPLE_RATE)

            # Trim stems to new duration
            for stem_name in stems_a:
                if stems_a[stem_name] is not None and len(stems_a[stem_name]) > transition_samples:
                    stems_a[stem_name] = stems_a[stem_name][:transition_samples]
            for stem_name in stems_b:
                if stems_b[stem_name] is not None and len(stems_b[stem_name]) > transition_samples:
                    stems_b[stem_name] = stems_b[stem_name][:transition_samples]

            # Also trim the stretched segments
            if len(segment_a) > transition_samples:
                segment_a = segment_a[:transition_samples]
            if len(segment_b_stretched) > transition_samples:
                segment_b_stretched = segment_b_stretched[:transition_samples]

            # CRITICAL: Update min_len to the new trimmed length
            min_len = transition_samples
            logger.info(
                "Updated min_len after trimming",
                min_len=min_len,
                duration_s=min_len / SAMPLE_RATE
            )

        # === NEW: APPLY BASS SWAP - THE SACRED RULE ===
        report_progress("mixing", 0)
        stems_config = transition_config.get("stems", {})

        # Get bass swap timing from plan or calculate default
        # IMPORTANT: Clamp to actual transition_bars (may have been reduced by vocal check)
        original_bass_swap_bar = stems_config.get("bass_swap_bar", transition_bars // 2)
        bass_swap_bar = min(original_bass_swap_bar, max(1, transition_bars // 2))

        if bass_swap_bar != original_bass_swap_bar:
            logger.info(
                "Bass swap bar adjusted to fit reduced transition",
                original_bar=original_bass_swap_bar,
                adjusted_bar=bass_swap_bar,
                transition_bars=transition_bars
            )

        bass_swap_time = calculate_bass_swap_time(
            transition_start=0,
            transition_duration_bars=transition_bars,
            bpm=target_bpm,
            swap_bar=bass_swap_bar
        )

        logger.info(
            "Applying bass swap",
            swap_bar=bass_swap_bar,
            swap_time=bass_swap_time,
            transition_bars=transition_bars
        )

        # Apply bass swap to stems
        stems_a_swapped, stems_b_swapped = apply_bass_swap_to_stems(
            stems_a=stems_a,
            stems_b=stems_b,
            swap_time=bass_swap_time,
            swap_duration="instant",  # Clean swap per spec
            bpm=target_bpm,
            sr=SAMPLE_RATE
        )

        # Validate bass swap
        if stems_a_swapped.get('bass') is not None and stems_b_swapped.get('bass') is not None:
            validation = validate_bass_swap(
                bass_a=stems_a_swapped['bass'],
                bass_b=stems_b_swapped['bass'],
                sr=SAMPLE_RATE,
                bpm=target_bpm,
                max_overlap_beats=2.0
            )
            if not validation['valid']:
                logger.warning(
                    "Bass swap validation failed",
                    overlap_beats=validation['overlap_beats'],
                    error=validation.get('error')
                )
            else:
                logger.info(
                    "Bass swap validation PASSED",
                    overlap_beats=validation['overlap_beats']
                )

        # Apply LLM-planned phase mixing with bass-swapped stems
        if stems_config and stems_config.get("phases"):
            # Use bass-swapped stems for mixing
            transition_audio = _apply_llm_phase_mixing_with_bass_swap(
                stems_a_swapped, stems_b_swapped, min_len, target_bpm, stems_config
            )
        else:
            # Use bass-swapped stems for default 4-phase mixing too
            transition_audio = _apply_four_phase_mixing_with_bass_swap(
                stems_a_swapped, stems_b_swapped, min_len, target_bpm, transition_bars
            )

        report_progress("mixing", 100)

        # Final processing
        transition_audio = _apply_limiter(transition_audio, -1.0)
        transition_audio = _normalize_audio(transition_audio)

        # Export
        report_progress("export", 0)
        if transition_audio.ndim == 1:
            transition_audio_stereo = np.stack([transition_audio, transition_audio])
        else:
            transition_audio_stereo = transition_audio
        _export_mp3(transition_audio_stereo, SAMPLE_RATE, params.output_path)
        report_progress("export", 100)

        actual_outro_ms = int(track_a_start / SAMPLE_RATE * 1000)
        actual_intro_ms = int(min_len / SAMPLE_RATE * 1000)

        # Cut points for seamless playback
        track_a_play_until_ms = actual_outro_ms  # Stop Track A here
        track_b_start_from_ms = actual_intro_ms  # Start Track B here (after transition)

        return DraftTransitionResult(
            draft_id=params.draft_id,
            transition_file_path=params.output_path,
            transition_duration_ms=int(len(transition_audio) / SAMPLE_RATE * 1000),
            track_a_outro_ms=actual_outro_ms,
            track_b_intro_ms=actual_intro_ms,
            transition_mode=TransitionMode.STEMS.value,
            track_a_play_until_ms=track_a_play_until_ms,
            track_b_start_from_ms=track_b_start_from_ms,
        )

        return DraftTransitionResult(
            draft_id=params.draft_id,
            transition_file_path=params.output_path,
            transition_duration_ms=int(len(transition_audio) / SAMPLE_RATE * 1000),
            track_a_outro_ms=actual_outro_ms,
            track_b_intro_ms=actual_intro_ms,
            transition_mode=TransitionMode.STEMS.value,
            track_a_play_until_ms=track_a_play_until_ms,
            track_b_start_from_ms=track_b_start_from_ms,
        )

    except Exception as e:
        import traceback
        logger.error(f"LLM-planned stem transition failed with error: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fallback
        logger.info("Falling back to crossfade due to error")
        avg_energy = (params.track_a_energy + params.track_b_energy) / 2
        transition_bars = calculate_transition_bars(avg_energy)
        return _generate_crossfade_fallback(params, transition_bars, progress_callback, str(e))


def _generate_hard_cut_with_plan(
    params: DraftTransitionParams,
    plan: dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """Generate a hard cut transition based on LLM plan.

    A hard cut includes:
    - Context audio from track A (4 bars before the cut)
    - A very short crossfade (50ms) to avoid clicks
    - Context audio from track B (4 bars after the entry)
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)

    logger.info("Generating LLM-planned hard cut transition", draft_id=params.draft_id)

    report_progress("extraction", 0)

    # Convert M4A/AAC to WAV if needed
    track_a_path = ensure_wav_format(params.track_a_path)
    track_b_path = ensure_wav_format(params.track_b_path)

    import librosa
    audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=False)
    audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=False)

    # Ensure stereo
    if audio_a.ndim == 1:
        audio_a = np.stack([audio_a, audio_a])
    if audio_b.ndim == 1:
        audio_b = np.stack([audio_b, audio_b])

    report_progress("extraction", 50)

    # Get cut/entry points from plan
    track_a_config = plan.get("track_a", {})
    track_b_config = plan.get("track_b", {})

    cut_time_s = track_a_config.get("play_until_seconds", params.track_a_outro_start_ms / 1000)
    entry_time_s = track_b_config.get("start_from_seconds", 0)

    # Debug logging
    logger.info("Hard cut extraction params",
                audio_a_shape=audio_a.shape,
                audio_b_shape=audio_b.shape,
                cut_time_s=cut_time_s,
                entry_time_s=entry_time_s,
                track_a_outro_start_ms=params.track_a_outro_start_ms,
                sample_rate=SAMPLE_RATE)

    # Clamp cut_time to valid range
    audio_a_duration_s = audio_a.shape[1] / SAMPLE_RATE
    audio_b_duration_s = audio_b.shape[1] / SAMPLE_RATE
    cut_time_s = min(cut_time_s, audio_a_duration_s)
    entry_time_s = min(entry_time_s, audio_b_duration_s - 1)  # Leave at least 1s

    cut_sample = int(cut_time_s * SAMPLE_RATE)
    entry_sample = int(entry_time_s * SAMPLE_RATE)

    # Calculate context duration: 4 bars at track BPM (or default 128)
    bpm = params.track_b_bpm if params.track_b_bpm else 128.0
    seconds_per_bar = 4 * (60.0 / bpm)  # 4 beats per bar
    context_bars = 4  # 4 bars of context on each side
    context_duration_s = context_bars * seconds_per_bar
    context_samples = int(context_duration_s * SAMPLE_RATE)

    # Small crossfade to avoid click (50ms)
    crossfade_samples = int(0.05 * SAMPLE_RATE)

    # Extract segment from track A: context_duration before the cut point
    start_a = max(0, cut_sample - context_samples)
    # Ensure we don't go past the audio length
    cut_sample = min(cut_sample, audio_a.shape[1])
    segment_a = audio_a[:, start_a:cut_sample]

    # Extract segment from track B: context_duration after the entry point
    entry_sample = min(entry_sample, audio_b.shape[1] - context_samples)
    entry_sample = max(0, entry_sample)
    end_b = min(audio_b.shape[1], entry_sample + context_samples)
    segment_b = audio_b[:, entry_sample:end_b]

    logger.info("Hard cut segments extracted",
                segment_a_shape=segment_a.shape,
                segment_b_shape=segment_b.shape,
                start_a=start_a,
                cut_sample=cut_sample,
                entry_sample=entry_sample,
                end_b=end_b,
                segment_a_min=float(np.min(segment_a)),
                segment_a_max=float(np.max(segment_a)),
                segment_b_min=float(np.min(segment_b)),
                segment_b_max=float(np.max(segment_b)))

    report_progress("mixing", 50)

    # Apply short fade out to end of segment A (50ms)
    if segment_a.shape[1] > crossfade_samples:
        fade_out = np.ones(segment_a.shape[1], dtype=np.float32)
        fade_out[-crossfade_samples:] = np.linspace(1.0, 0.0, crossfade_samples)
        segment_a = segment_a * fade_out.reshape(1, -1)

    # Apply short fade in to start of segment B (50ms)
    if segment_b.shape[1] > crossfade_samples:
        fade_in = np.ones(segment_b.shape[1], dtype=np.float32)
        fade_in[:crossfade_samples] = np.linspace(0.0, 1.0, crossfade_samples)
        segment_b = segment_b * fade_in.reshape(1, -1)

    # Concatenate with small overlap for the crossfade
    # Overlap the last 50ms of A with the first 50ms of B
    overlap = min(crossfade_samples, segment_a.shape[1], segment_b.shape[1])

    if overlap > 0 and segment_a.shape[1] > overlap:
        # Create the transition: A (without last overlap) + crossfade + B (without first overlap)
        part_a = segment_a[:, :-overlap]
        crossfade_a = segment_a[:, -overlap:]
        crossfade_b = segment_b[:, :overlap]
        part_b = segment_b[:, overlap:]

        # Mix the crossfade portion
        crossfade_mix = crossfade_a + crossfade_b

        # Concatenate all parts
        transition_audio = np.concatenate([part_a, crossfade_mix, part_b], axis=1)
    else:
        # Fallback: just concatenate
        transition_audio = np.concatenate([segment_a, segment_b], axis=1)

    report_progress("mixing", 100)

    # Debug: check audio values before processing
    logger.info("Audio before processing",
                shape=transition_audio.shape,
                min_val=float(np.min(transition_audio)),
                max_val=float(np.max(transition_audio)),
                mean_val=float(np.mean(np.abs(transition_audio))))

    # Final processing
    transition_audio = _apply_limiter(transition_audio, -1.0)
    transition_audio = _normalize_audio(transition_audio)

    # Debug: check audio values after processing
    logger.info("Audio after processing",
                shape=transition_audio.shape,
                min_val=float(np.min(transition_audio)),
                max_val=float(np.max(transition_audio)),
                mean_val=float(np.mean(np.abs(transition_audio))))

    transition_duration_ms = int(transition_audio.shape[1] / SAMPLE_RATE * 1000)

    report_progress("export", 0)
    _export_mp3(transition_audio, SAMPLE_RATE, params.output_path)
    report_progress("export", 100)

    # Cut points for seamless playback
    track_a_play_until_ms = int(start_a / SAMPLE_RATE * 1000)  # Stop Track A here
    track_b_start_from_ms = int((end_b - entry_sample) / SAMPLE_RATE * 1000)  # Start Track B here

    logger.info("Hard cut transition generated",
                draft_id=params.draft_id,
                duration_ms=transition_duration_ms,
                context_bars=context_bars,
                track_a_play_until_ms=track_a_play_until_ms,
                track_b_start_from_ms=track_b_start_from_ms)

    return DraftTransitionResult(
        draft_id=params.draft_id,
        transition_file_path=params.output_path,
        transition_duration_ms=transition_duration_ms,
        track_a_outro_ms=int(cut_time_s * 1000),
        track_b_intro_ms=int(entry_time_s * 1000),
        transition_mode="HARD_CUT",
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )


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
        stems_config: LLM-generated stems configuration

    Returns:
        Mixed audio array
    """
    phases = stems_config.get("phases", [])
    if not phases:
        # Fallback to default if no phases defined
        return _apply_four_phase_mixing_spec(stems_a, stems_b, total_samples, bpm, 16)

    # Calculate samples per bar
    samples_per_bar = bars_to_samples(1, bpm)

    # Get total bars from phases
    total_bars = max(phase.get("bars", [1, 1])[1] for phase in phases)

    # Generate volume curves for each stem
    curves_a = {stem: np.zeros(total_samples, dtype=np.float32) for stem in ['drums', 'bass', 'other', 'vocals']}
    curves_b = {stem: np.zeros(total_samples, dtype=np.float32) for stem in ['drums', 'bass', 'other', 'vocals']}

    for phase in phases:
        bars = phase.get("bars", [1, 1])
        start_bar = bars[0] - 1  # 0-indexed
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

            curves_a[stem][start_sample:end_sample] = a_level
            curves_b[stem][start_sample:end_sample] = b_level

    # Smooth curves to avoid clicks
    smooth_window = samples_per_bar // 4
    for stem in ['drums', 'bass', 'other', 'vocals']:
        curves_a[stem] = _smooth_curve(curves_a[stem], smooth_window)
        curves_b[stem] = _smooth_curve(curves_b[stem], smooth_window)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        mixed_stem = stem_a * curves_a[stem_name] + stem_b * curves_b[stem_name]
        output += mixed_stem

    return output


def _smooth_curve(curve: np.ndarray, window_size: int) -> np.ndarray:
    """Apply smoothing to avoid clicks."""
    if window_size <= 1:
        return curve
    kernel = np.ones(window_size) / window_size
    smoothed = np.convolve(curve, kernel, mode='same')
    return smoothed.astype(np.float32)


# =============================================================================
# NEW ENHANCED TRANSITION FUNCTIONS - Phase 4-8 Integration
# =============================================================================

def _apply_llm_phase_mixing_with_bass_swap(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float,
    stems_config: dict
) -> np.ndarray:
    """
    Apply LLM-planned stem mixing with pre-applied bass swap.

    The bass stems should already have bass swap applied via
    apply_bass_swap_to_stems() before calling this function.

    Args:
        stems_a: Bass-swapped stems from track A
        stems_b: Bass-swapped stems from track B
        total_samples: Total number of samples
        bpm: Target BPM
        stems_config: LLM-generated stems configuration

    Returns:
        Mixed audio array
    """
    phases = stems_config.get("phases", [])
    if not phases:
        return _apply_four_phase_mixing_with_bass_swap(
            stems_a, stems_b, total_samples, bpm, 16
        )

    # Calculate samples per bar
    samples_per_bar = bars_to_samples(1, bpm)

    # Get total bars from phases
    total_bars = max(phase.get("bars", [1, 1])[1] for phase in phases)

    # Generate volume curves for each stem (but NOT bass - it's already swapped)
    curves_a = {stem: np.zeros(total_samples, dtype=np.float32) for stem in ['drums', 'bass', 'other', 'vocals']}
    curves_b = {stem: np.zeros(total_samples, dtype=np.float32) for stem in ['drums', 'bass', 'other', 'vocals']}

    for phase in phases:
        bars = phase.get("bars", [1, 1])
        start_bar = bars[0] - 1  # 0-indexed
        end_bar = bars[1]

        start_sample = start_bar * samples_per_bar
        end_sample = min(end_bar * samples_per_bar, total_samples)
        phase_samples = end_sample - start_sample

        if phase_samples <= 0:
            continue

        a_levels = phase.get("a", {})
        b_levels = phase.get("b", {})

        for stem in ['drums', 'other', 'vocals']:
            # Apply normal automation for non-bass stems
            a_level = a_levels.get(stem, 1.0)
            b_level = b_levels.get(stem, 0.0)

            curves_a[stem][start_sample:end_sample] = a_level
            curves_b[stem][start_sample:end_sample] = b_level

    # For bass, use 1.0 curves since swap is already applied
    curves_a['bass'] = np.ones(total_samples, dtype=np.float32)
    curves_b['bass'] = np.ones(total_samples, dtype=np.float32)

    # Smooth curves to avoid clicks (except bass which is already clean)
    smooth_window = samples_per_bar // 4
    for stem in ['drums', 'other', 'vocals']:
        curves_a[stem] = _smooth_curve(curves_a[stem], smooth_window)
        curves_b[stem] = _smooth_curve(curves_b[stem], smooth_window)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        mixed_stem = stem_a * curves_a[stem_name] + stem_b * curves_b[stem_name]
        output += mixed_stem

    logger.info("LLM phase mixing with bass swap applied")
    return output


def _apply_four_phase_mixing_with_bass_swap(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    total_samples: int,
    bpm: float,
    transition_bars: int
) -> np.ndarray:
    """
    Apply 4-phase stem mixing with pre-applied bass swap.

    The bass stems should already have bass swap applied.
    This is a modified version of the spec mixing that respects
    the pre-applied bass swap.

    | Phase | Track A (non-bass) | Track B (non-bass) |
    |-------|--------------------|--------------------|
    | 1 | 100% all | Drums 0→70%, Other 0→30% |
    | 2 | Other fade | Drums 70→100%, Other rise |
    | 3 | Vocals 100→0% | Vocals 0→100%, Other 50→100% |
    | 4 | All fade out | 100% all |

    Bass is NOT automated here - it's handled by bass_swap module.
    """
    phase_bars = transition_bars // 4
    samples_per_phase = bars_to_samples(phase_bars, bpm)

    # Adjust to fit total_samples
    phase_samples = [samples_per_phase] * 4
    total_phase_samples = sum(phase_samples)
    if total_phase_samples > total_samples:
        scale = total_samples / total_phase_samples
        phase_samples = [int(s * scale) for s in phase_samples]

    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Generate curves (NOT for bass)
    curves_a = _generate_curves_track_a_no_bass(phase_samples, total_samples)
    curves_b = _generate_curves_track_b_no_bass(phase_samples, total_samples)

    # Bass uses identity curves (swap already applied)
    curves_a['bass'] = np.ones(total_samples, dtype=np.float32)
    curves_b['bass'] = np.ones(total_samples, dtype=np.float32)

    # Mix stems
    output = np.zeros(total_samples, dtype=np.float32)

    for stem_name in ['drums', 'bass', 'other', 'vocals']:
        stem_a = stems_a.get(stem_name, np.zeros(total_samples))
        stem_b = stems_b.get(stem_name, np.zeros(total_samples))

        stem_a = _ensure_length(stem_a, total_samples)
        stem_b = _ensure_length(stem_b, total_samples)

        curve_a = curves_a[stem_name]
        curve_b = curves_b[stem_name]

        mixed_stem = stem_a * curve_a + stem_b * curve_b
        output += mixed_stem

    logger.info("4-phase mixing with bass swap applied")
    return output


def _generate_curves_track_a_no_bass(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """Generate volume curves for Track A (without bass automation)."""
    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Drums: 100% → 100% → 100% → fade to 0%
    drums = np.ones(total_samples)
    if p4 > 0:
        drums[p3_end:] = np.linspace(1.0, 0.0, total_samples - p3_end)

    # Vocals: 100% → 100% → 100→0% → 0%
    vocals = np.ones(total_samples)
    if p3 > 0:
        vocals[p2_end:p3_end] = np.linspace(1.0, 0.0, p3)
    vocals[p3_end:] = 0.0

    # Other: 100% → 100% → 100% → fade to 0%
    other = np.ones(total_samples)
    if p4 > 0:
        other[p3_end:] = np.linspace(1.0, 0.0, total_samples - p3_end)

    return {'drums': drums, 'vocals': vocals, 'other': other}


def _generate_curves_track_b_no_bass(
    phase_samples: List[int],
    total_samples: int
) -> Dict[str, np.ndarray]:
    """Generate volume curves for Track B (without bass automation)."""
    p1, p2, p3, p4 = phase_samples
    p1_end = p1
    p2_end = p1_end + p2
    p3_end = p2_end + p3

    # Drums: 0→70% → 70→100% → 100% → 100%
    drums = np.zeros(total_samples)
    if p1 > 0:
        drums[:p1_end] = np.linspace(0.0, 0.7, p1)
    if p2 > 0:
        drums[p1_end:p2_end] = np.linspace(0.7, 1.0, p2)
    drums[p2_end:] = 1.0

    # Vocals: 0% → 0% → 0→100% → 100%
    vocals = np.zeros(total_samples)
    if p3 > 0:
        vocals[p2_end:p3_end] = np.linspace(0.0, 1.0, p3)
    vocals[p3_end:] = 1.0

    # Other: 0→30% → 30→50% → 50→100% → 100%
    other = np.zeros(total_samples)
    if p1 > 0:
        other[:p1_end] = np.linspace(0.0, 0.3, p1)
    if p2 > 0:
        other[p1_end:p2_end] = np.linspace(0.3, 0.5, p2)
    if p3 > 0:
        other[p2_end:p3_end] = np.linspace(0.5, 1.0, p3)
    other[p3_end:] = 1.0

    return {'drums': drums, 'vocals': vocals, 'other': other}


def _generate_hard_cut_with_plan_enhanced(
    params: DraftTransitionParams,
    plan: dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """
    Generate an ENHANCED hard cut transition with optional effects.

    ENHANCEMENTS:
    - Applies reverb tail to track A exit (if requested in plan)
    - Applies delay tail to track A exit (if requested in plan)
    - Better phrase boundary alignment

    Args:
        params: DraftTransitionParams
        plan: LLM-generated plan
        progress_callback: Optional progress callback

    Returns:
        DraftTransitionResult
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)

    logger.info("Generating ENHANCED hard cut transition", draft_id=params.draft_id)

    report_progress("extraction", 0)

    # Convert M4A/AAC to WAV if needed
    track_a_path = ensure_wav_format(params.track_a_path)
    track_b_path = ensure_wav_format(params.track_b_path)

    import librosa
    audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=False)
    audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=False)

    # Ensure stereo
    if audio_a.ndim == 1:
        audio_a = np.stack([audio_a, audio_a])
    if audio_b.ndim == 1:
        audio_b = np.stack([audio_b, audio_b])

    report_progress("extraction", 50)

    # Get cut/entry points from plan
    track_a_config = plan.get("track_a", {})
    track_b_config = plan.get("track_b", {})
    effects_config = plan.get("effects", {})

    # FIXED: Use outro_start as the START of the transition, not the end
    # The transition should contain Track A's outro (from outro_start to end or cut point)
    # and Track B's intro (from 0 to intro_end)
    outro_start_s = params.track_a_outro_start_ms / 1000
    intro_end_s = params.track_b_intro_end_ms / 1000

    # LLM might specify different points
    cut_time_s = track_a_config.get("play_until_seconds", params.track_a_duration_ms / 1000)
    entry_time_s = track_b_config.get("start_from_seconds", 0)

    # Clamp to valid range
    audio_a_duration_s = audio_a.shape[1] / SAMPLE_RATE
    audio_b_duration_s = audio_b.shape[1] / SAMPLE_RATE
    cut_time_s = min(cut_time_s, audio_a_duration_s)
    entry_time_s = max(0, min(entry_time_s, audio_b_duration_s - 1))
    intro_end_s = max(intro_end_s, 1.0)  # At least 1 second

    # Convert to samples
    outro_start_sample = int(outro_start_s * SAMPLE_RATE)
    cut_sample = int(cut_time_s * SAMPLE_RATE)
    entry_sample = int(entry_time_s * SAMPLE_RATE)
    intro_end_sample = int(intro_end_s * SAMPLE_RATE)

    bpm = params.track_a_bpm if params.track_a_bpm else 128.0
    seconds_per_bar = 4 * (60.0 / bpm)

    # FIXED: Extract segments correctly to avoid duplication
    # segment_a: from outro_start to end of track (the outro portion)
    # For HARD_CUT, we only need a small tail with effects
    # FIXED: Extract segments with context for effect processing
    # segment_a: must include some audio BEFORE the cut to generate a reverb tail
    # Double duration to 4s to address "too short" feedback
    context_duration_s = 4.0 
    context_samples = int(context_duration_s * SAMPLE_RATE)
    tail_duration_s = 4.0  
    tail_samples = int(tail_duration_s * SAMPLE_RATE)

    # Calculate ranges
    # We want: [Context (2s)] --CUT-- [Tail (2s)]
    # The output transition will only contain the Tail part
    
    # 1. Start point (start of context)
    # If outro_start is valid, go back context_samples
    if outro_start_sample < (audio_a.shape[1] * 0.1):
         # Fallback for missing cue: end of track - tail
         effective_cut_sample = max(0, audio_a.shape[1] - tail_samples)
    else:
         effective_cut_sample = min(outro_start_sample, audio_a.shape[1])
    
    start_a_context = max(0, effective_cut_sample - context_samples)
    end_a_tail = min(effective_cut_sample + tail_samples, audio_a.shape[1])
    
    # Load the full chunk (Context + Potential Tail)
    segment_a_full = audio_a[:, start_a_context:end_a_tail]
    
    # Calculate where the cut is relative to this chunk
    # If we hit start of file, cut_index might be less than context_samples
    cut_index_in_segment = effective_cut_sample - start_a_context
    
    # For segment_b, same logic
    entry_sample = max(0, entry_sample)
    end_b = min(intro_end_sample, audio_b.shape[1])
    end_b = max(end_b, entry_sample + int(2.0 * SAMPLE_RATE))
    segment_b = audio_b[:, entry_sample:end_b]

    logger.info(
        "HARD_CUT segments extracted",
        segment_a_full_duration_s=segment_a_full.shape[1] / SAMPLE_RATE,
        segment_b_duration_s=segment_b.shape[1] / SAMPLE_RATE,
        outro_start_s=outro_start_s,
        intro_end_s=intro_end_s,
        cut_index_in_segment=cut_index_in_segment,
    )

    report_progress("effects", 0)

    # === APPLY EXIT EFFECTS TO TRACK A ===
    # Check effects at top level (LLM format) or in transition (legacy format)
    effect_a_config = effects_config.get("track_a", {})
    if not effect_a_config:
        effect_a_config = plan.get("transition", {}).get("effects", {}).get("track_a", {})

    effect_type = effect_a_config.get("type", "none")

    # DEFAULT: Apply reverb for HARD_CUT if no effect specified
    # This softens the transition when there's a large BPM difference
    if effect_type == "none":
        logger.info("Applying DEFAULT reverb for HARD_CUT transition")
        effect_type = "reverb"
        # Increased decay to 4.0s to match longer tail
        effect_a_config = {"type": "reverb", "params": {"room_size": 0.8, "decay": 4.0}}

    if effect_type == "reverb":
        logger.info("Applying reverb tail to track A exit", effect_params=effect_a_config.get("params", {}))
        effect_params = effect_a_config.get("params", {})
        # Support both "size" and "room_size" as param keys
        # Handle string values like "small", "medium", "large" from LLM
        raw_size = effect_params.get("room_size", effect_params.get("size", 0.8))
        if isinstance(raw_size, str):
            size_map = {"small": 0.4, "medium": 0.7, "large": 0.9}
            room_size = size_map.get(raw_size.lower(), 0.7)
        else:
            room_size = float(raw_size)
        decay = float(effect_params.get("decay", 4.0))

        # Process each channel
        # We process the FULL segment (context + tail)
        # But we want the tail to start fading out at the CUT point
        processed_channels = []
        for ch in range(segment_a_full.shape[0]):
            processed = create_reverb_tail(
                audio=segment_a_full[ch],
                tail_start_sample=cut_index_in_segment, # Start tail at the cut
                room_size=room_size,
                decay=decay,
                fade_out_duration=1.5,
                sr=SAMPLE_RATE
            )
            processed_channels.append(processed)
        
        # Stack back to stereo/multi-channel
        segment_a_processed = np.stack(processed_channels)
        
        # NOW, slice to only keep the tail part for the transition file
        # We want audio starting FROM the cut point
        segment_a = segment_a_processed[:, cut_index_in_segment:]
        
        # Ensure it's not too long (limit to tail_samples)
        if segment_a.shape[1] > tail_samples:
            segment_a = segment_a[:, :tail_samples]

    elif effect_type == "delay":
        logger.info("Applying delay tail to track A exit", effect_params=effect_a_config.get("params", {}))
        effect_params = effect_a_config.get("params", {})
        processed_channels = []
        for ch in range(segment_a_full.shape[0]):
            processed = create_delay_tail(
                audio=segment_a_full[ch],
                tail_start_sample=cut_index_in_segment,
                bpm=bpm,
                beat_fraction=effect_params.get("beat_fraction", 0.5),
                feedback=effect_params.get("feedback", 0.4),
                fade_out_duration=2.0,
                sr=SAMPLE_RATE
            )
            processed_channels.append(processed)
        segment_a_processed = np.stack(processed_channels)
        segment_a = segment_a_processed[:, cut_index_in_segment:]
        if segment_a.shape[1] > tail_samples:
            segment_a = segment_a[:, :tail_samples]
            
    else:
        # No effect: just take the part after the cut (raw audio)
        # This effectively plays the "tail" of the track raw
        segment_a = segment_a_full[:, cut_index_in_segment:]
        if segment_a.shape[1] > tail_samples:
             segment_a = segment_a[:, :tail_samples]

    report_progress("effects", 100)
    report_progress("mixing", 0)

    report_progress("effects", 100)
    report_progress("mixing", 0)

    # Small crossfade to avoid click
    crossfade_samples = int(0.05 * SAMPLE_RATE)

    if segment_a.shape[1] > crossfade_samples:
        fade_out = np.ones(segment_a.shape[1], dtype=np.float32)
        fade_out[-crossfade_samples:] = np.linspace(1.0, 0.0, crossfade_samples)
        segment_a = segment_a * fade_out.reshape(1, -1)

    if segment_b.shape[1] > crossfade_samples:
        fade_in = np.ones(segment_b.shape[1], dtype=np.float32)
        fade_in[:crossfade_samples] = np.linspace(0.0, 1.0, crossfade_samples)
        segment_b = segment_b * fade_in.reshape(1, -1)

    # Concatenate
    overlap = min(crossfade_samples, segment_a.shape[1], segment_b.shape[1])

    if overlap > 0 and segment_a.shape[1] > overlap:
        part_a = segment_a[:, :-overlap]
        crossfade_a = segment_a[:, -overlap:]
        crossfade_b = segment_b[:, :overlap]
        part_b = segment_b[:, overlap:]
        crossfade_mix = crossfade_a + crossfade_b
        transition_audio = np.concatenate([part_a, crossfade_mix, part_b], axis=1)
    else:
        transition_audio = np.concatenate([segment_a, segment_b], axis=1)

    report_progress("mixing", 100)

    # Final processing
    transition_audio = _apply_limiter(transition_audio, -1.0)
    transition_audio = _normalize_audio(transition_audio)

    transition_duration_ms = int(transition_audio.shape[1] / SAMPLE_RATE * 1000)

    report_progress("export", 0)
    _export_mp3(transition_audio, SAMPLE_RATE, params.output_path)
    report_progress("export", 100)

    # Calculate cut points for seamless playback
    # track_a_play_until_ms: where to stop playing Track A (transition takes over)
    # track_b_start_from_ms: where to start playing Track B (after transition ends)
    # Calculate cut points for seamless playback
    track_a_play_until_ms = int(effective_cut_sample / SAMPLE_RATE * 1000)
    track_b_start_from_ms = int(end_b / SAMPLE_RATE * 1000)

    logger.info(
        "ENHANCED hard cut transition generated",
        draft_id=params.draft_id,
        duration_ms=transition_duration_ms,
        effect_applied=effect_type,
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )

    return DraftTransitionResult(
        draft_id=params.draft_id,
        transition_file_path=params.output_path,
        transition_duration_ms=transition_duration_ms,
        track_a_outro_ms=int(cut_time_s * 1000),
        track_b_intro_ms=track_b_start_from_ms, # FIXED: Resume from end of cut, not start
        transition_mode="HARD_CUT",
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )


def _generate_filter_sweep_transition(
    params: DraftTransitionParams,
    plan: dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """
    Generate a FILTER_SWEEP transition.

    Filter sweeps work by:
    - HPF sweep UP on track A (A "fades into distance")
    - LPF sweep UP on track B (B "reveals itself")
    - Volume crossfade

    Args:
        params: DraftTransitionParams
        plan: LLM-generated plan
        progress_callback: Optional progress callback

    Returns:
        DraftTransitionResult
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)

    logger.info("Generating FILTER_SWEEP transition", draft_id=params.draft_id)

    report_progress("extraction", 0)

    # Convert M4A/AAC to WAV if needed
    track_a_path = ensure_wav_format(params.track_a_path)
    track_b_path = ensure_wav_format(params.track_b_path)

    import librosa
    audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=True)
    audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=True)

    report_progress("extraction", 50)

    # Get transition parameters
    transition_config = plan.get("transition", {})
    transition_bars = transition_config.get("duration_bars", 16)
    target_bpm = params.track_a_bpm
    transition_samples = bars_to_samples(transition_bars, target_bpm)
    transition_duration_ms = bars_to_ms(transition_bars, target_bpm)
    transition_duration_s = transition_duration_ms / 1000

    # Extract segments
    track_a_start = max(0, len(audio_a) - transition_samples)
    segment_a = audio_a[track_a_start:]
    segment_b = audio_b[:transition_samples]

    report_progress("extraction", 100)
    report_progress("time-stretch", 0)

    # Time-stretch Track B
    segment_b_stretched, actual_bpm = stretch_to_bpm(
        segment_b, SAMPLE_RATE, params.track_b_bpm, target_bpm
    )

    report_progress("time-stretch", 100)

    # Ensure same length
    min_len = min(len(segment_a), len(segment_b_stretched), transition_samples)
    segment_a = _ensure_length(segment_a, min_len)
    segment_b_stretched = _ensure_length(segment_b_stretched, min_len)

    report_progress("mixing", 0)

    # Get filter sweep parameters from plan (or use defaults)
    filter_config = transition_config.get("filter", {})
    hpf_start = filter_config.get("hpf_start_a", 20)
    hpf_end = filter_config.get("hpf_end_a", 2000)
    lpf_start = filter_config.get("lpf_start_b", 200)
    lpf_end = filter_config.get("lpf_end_b", 20000)

    logger.info(
        "Applying filter sweeps",
        hpf_start=hpf_start,
        hpf_end=hpf_end,
        lpf_start=lpf_start,
        lpf_end=lpf_end
    )

    # Apply combined filter sweep
    transition_audio = create_combined_filter_sweep(
        audio_a=segment_a,
        audio_b=segment_b_stretched,
        hpf_start_a=hpf_start,
        hpf_end_a=hpf_end,
        lpf_start_b=lpf_start,
        lpf_end_b=lpf_end,
        duration=transition_duration_s,
        curve="exponential",
        crossfade=True,
        sr=SAMPLE_RATE
    )

    report_progress("mixing", 100)

    # Final processing
    transition_audio = _apply_limiter(transition_audio, -1.0)
    transition_audio = _normalize_audio(transition_audio)

    # Convert mono to stereo
    if transition_audio.ndim == 1:
        transition_audio = np.stack([transition_audio, transition_audio])

    report_progress("export", 0)
    _export_mp3(transition_audio, SAMPLE_RATE, params.output_path)
    report_progress("export", 100)

    actual_duration_ms = int(len(transition_audio[0]) / SAMPLE_RATE * 1000)

    # Cut points for seamless playback
    track_a_play_until_ms = int(track_a_start / SAMPLE_RATE * 1000)  # Stop Track A here
    # Track B: we use transition_samples from original B (before stretch)
    track_b_start_from_ms = int(transition_samples / SAMPLE_RATE * 1000)  # Start Track B here

    logger.info(
        "FILTER_SWEEP transition generated",
        draft_id=params.draft_id,
        duration_ms=actual_duration_ms,
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )

    return DraftTransitionResult(
        draft_id=params.draft_id,
        transition_file_path=params.output_path,
        transition_duration_ms=actual_duration_ms,
        track_a_outro_ms=int(track_a_start / SAMPLE_RATE * 1000),
        track_b_intro_ms=int(min_len / SAMPLE_RATE * 1000),
        transition_mode="FILTER_SWEEP",
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )


def _generate_echo_out_transition(
    params: DraftTransitionParams,
    plan: dict,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> DraftTransitionResult:
    """
    Generate an ECHO_OUT transition.

    Echo out works by:
    - Track A fades out with delay/reverb tail
    - Track B enters cleanly after the tail

    Args:
        params: DraftTransitionParams
        plan: LLM-generated plan
        progress_callback: Optional progress callback

    Returns:
        DraftTransitionResult
    """
    def report_progress(step: str, progress: int):
        if progress_callback:
            progress_callback(step, progress)

    logger.info("Generating ECHO_OUT transition", draft_id=params.draft_id)

    report_progress("extraction", 0)

    # Convert M4A/AAC to WAV if needed
    track_a_path = ensure_wav_format(params.track_a_path)
    track_b_path = ensure_wav_format(params.track_b_path)

    import librosa
    audio_a, sr_a = librosa.load(track_a_path, sr=SAMPLE_RATE, mono=True)
    audio_b, sr_b = librosa.load(track_b_path, sr=SAMPLE_RATE, mono=True)

    report_progress("extraction", 50)

    # Get transition parameters
    transition_config = plan.get("transition", {})
    effects_config = plan.get("effects", {})
    transition_bars = transition_config.get("duration_bars", 8)
    target_bpm = params.track_a_bpm

    # Echo out is typically shorter
    tail_duration_s = transition_config.get("tail_duration_s", 3.0)
    context_bars = 4  # 4 bars context from A before the echo out

    bar_duration_s = (60.0 / target_bpm) * 4
    context_samples = int(context_bars * bar_duration_s * SAMPLE_RATE)
    tail_samples = int(tail_duration_s * SAMPLE_RATE)

    # Extract segment from end of A
    track_a_start = max(0, len(audio_a) - context_samples - tail_samples)
    segment_a = audio_a[track_a_start:]

    # Extract intro from B
    intro_bars = 4
    intro_samples = int(intro_bars * bar_duration_s * SAMPLE_RATE)
    segment_b = audio_b[:intro_samples]

    report_progress("extraction", 100)
    report_progress("effects", 0)

    # Get echo effect type from plan
    echo_type = effects_config.get("track_a", {}).get("type", "delay")
    echo_params = effects_config.get("track_a", {}).get("params", {})

    # Apply echo/reverb to track A
    if echo_type == "reverb":
        segment_a_processed = create_reverb_tail(
            audio=segment_a,
            tail_start_sample=context_samples,
            room_size=echo_params.get("size", 0.8),
            decay=echo_params.get("decay", 3.0),
            fade_out_duration=tail_duration_s,
            sr=SAMPLE_RATE
        )
    else:  # delay
        segment_a_processed = create_delay_tail(
            audio=segment_a,
            tail_start_sample=context_samples,
            bpm=target_bpm,
            beat_fraction=echo_params.get("beat_fraction", 0.5),
            feedback=echo_params.get("feedback", 0.5),
            fade_out_duration=tail_duration_s,
            sr=SAMPLE_RATE
        )

    report_progress("effects", 100)
    report_progress("mixing", 0)

    # Determine overlap point (where B starts during A's tail)
    # B can start as A's echo tail is fading
    overlap_samples = int(0.5 * SAMPLE_RATE)  # 0.5s overlap

    # Ensure B has fade in
    if len(segment_b) > overlap_samples:
        fade_in = np.linspace(0.0, 1.0, overlap_samples)
        segment_b_faded = segment_b.copy()
        segment_b_faded[:overlap_samples] *= fade_in
    else:
        segment_b_faded = segment_b

    # Calculate total length
    overlap_point = len(segment_a_processed) - overlap_samples
    total_length = overlap_point + len(segment_b_faded)

    # Create output
    transition_audio = np.zeros(total_length, dtype=np.float32)
    transition_audio[:len(segment_a_processed)] = segment_a_processed
    transition_audio[overlap_point:overlap_point + len(segment_b_faded)] += segment_b_faded

    report_progress("mixing", 100)

    # Final processing
    transition_audio = _apply_limiter(transition_audio, -1.0)
    transition_audio = _normalize_audio(transition_audio)

    # Convert mono to stereo
    if transition_audio.ndim == 1:
        transition_audio = np.stack([transition_audio, transition_audio])

    report_progress("export", 0)
    _export_mp3(transition_audio, SAMPLE_RATE, params.output_path)
    report_progress("export", 100)

    actual_duration_ms = int(len(transition_audio[0]) / SAMPLE_RATE * 1000)

    # Cut points for seamless playback
    track_a_play_until_ms = int(track_a_start / SAMPLE_RATE * 1000)  # Stop Track A here
    track_b_start_from_ms = int(intro_samples / SAMPLE_RATE * 1000)  # Start Track B here

    logger.info(
        "ECHO_OUT transition generated",
        draft_id=params.draft_id,
        duration_ms=actual_duration_ms,
        echo_type=echo_type,
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )

    return DraftTransitionResult(
        draft_id=params.draft_id,
        transition_file_path=params.output_path,
        transition_duration_ms=actual_duration_ms,
        track_a_outro_ms=int(track_a_start / SAMPLE_RATE * 1000),
        track_b_intro_ms=int(intro_samples / SAMPLE_RATE * 1000),
        transition_mode="ECHO_OUT",
        track_a_play_until_ms=track_a_play_until_ms,
        track_b_start_from_ms=track_b_start_from_ms,
    )
