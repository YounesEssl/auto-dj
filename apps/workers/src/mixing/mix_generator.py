"""
Professional Mix Generator

Creates proper DJ-style mixes with:
- Solo segments (original track portions)
- Transition segments (overlapping mixes with stems, beatmatch, EQ)

The mix is structured as:
Track A solo → Transition A→B → Track B solo → Transition B→C → ...
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import soundfile as sf
import structlog

from src.config import settings
from src.utils.audio import load_audio
from src.mixing.stems import separate_stems
from src.mixing.beatmatch import time_stretch, calculate_stretch_ratio, MAX_STRETCH_RATIO, MIN_STRETCH_RATIO

logger = structlog.get_logger()

# Constants
SAMPLE_RATE = 44100
BEATS_PER_BAR = 4


@dataclass
class TrackData:
    """Track data with analysis results."""
    id: str
    file_path: str
    duration_ms: float
    bpm: float
    energy: float
    beats: List[float]  # Beat positions in seconds
    intro_end_ms: float
    outro_start_ms: float


@dataclass
class SegmentInfo:
    """Information about a segment in the mix."""
    position: int
    type: str  # 'SOLO' or 'TRANSITION'
    track_id: Optional[str]
    transition_id: Optional[str]
    start_ms: int
    end_ms: int
    duration_ms: int


@dataclass
class TransitionResult:
    """Result of transition generation."""
    audio: np.ndarray
    sample_rate: int
    duration_ms: int
    track_a_cut_ms: int = 0
    track_b_start_ms: int = 0


def calculate_transition_duration_bars(energy_a: float, energy_b: float) -> int:
    """
    Calculate transition duration in bars based on average energy.

    Higher energy = shorter transition (more impact)
    Lower energy = longer transition (more gradual)
    """
    avg_energy = (energy_a + energy_b) / 2

    if avg_energy >= 0.8:
        return 16  # High energy: quick 16-bar transition
    elif avg_energy >= 0.5:
        return 24  # Medium energy: 24-bar transition
    else:
        return 32  # Low energy: gradual 32-bar transition


def bars_to_ms(bars: int, bpm: float) -> int:
    """Convert bars to milliseconds."""
    # bars * beats_per_bar * (60000 ms/min) / bpm
    return int(bars * BEATS_PER_BAR * 60000 / bpm)


def ms_to_samples(ms: int, sample_rate: int = SAMPLE_RATE) -> int:
    """Convert milliseconds to samples."""
    return int(ms * sample_rate / 1000)


def get_default_intro_end_ms(bpm: float, duration_ms: float) -> float:
    """Calculate default intro end (16 bars from start)."""
    intro_bars = 16
    intro_ms = bars_to_ms(intro_bars, bpm)
    return min(intro_ms, duration_ms * 0.25)  # Max 25% of track


def get_default_outro_start_ms(bpm: float, duration_ms: float) -> float:
    """Calculate default outro start (16 bars before end)."""
    outro_bars = 16
    outro_ms = bars_to_ms(outro_bars, bpm)
    return max(duration_ms - outro_ms, duration_ms * 0.75)  # Min 75% into track


def calculate_segments(tracks: List[TrackData]) -> List[SegmentInfo]:
    """
    Calculate all segments for the mix.

    For N tracks, generates:
    - Track 1 solo (0 → outro_start)
    - Transition 1→2
    - Track 2 solo (intro_end → outro_start)
    - Transition 2→3
    - ...
    - Track N solo (intro_end → end)
    """
    if len(tracks) < 2:
        if len(tracks) == 1:
            # Single track: just play the whole thing
            return [SegmentInfo(
                position=0,
                type='SOLO',
                track_id=tracks[0].id,
                transition_id=None,
                start_ms=0,
                end_ms=int(tracks[0].duration_ms),
                duration_ms=int(tracks[0].duration_ms)
            )]
        return []

    segments: List[SegmentInfo] = []
    position = 0

    for i, track in enumerate(tracks):
        is_first = i == 0
        is_last = i == len(tracks) - 1

        # Calculate intro_end and outro_start with fallbacks
        intro_end_ms = track.intro_end_ms
        if intro_end_ms is None or intro_end_ms <= 0:
            intro_end_ms = get_default_intro_end_ms(track.bpm, track.duration_ms)

        outro_start_ms = track.outro_start_ms
        if outro_start_ms is None or outro_start_ms <= 0 or outro_start_ms >= track.duration_ms:
            outro_start_ms = get_default_outro_start_ms(track.bpm, track.duration_ms)

        # Solo segment start
        if is_first:
            solo_start_ms = 0  # First track: start from beginning
        else:
            solo_start_ms = int(intro_end_ms)  # Other tracks: after intro

        # Solo segment end
        if is_last:
            solo_end_ms = int(track.duration_ms)  # Last track: play to end
        else:
            solo_end_ms = int(outro_start_ms)  # Other tracks: until outro

        # Add solo segment
        if solo_end_ms > solo_start_ms:
            segments.append(SegmentInfo(
                position=position,
                type='SOLO',
                track_id=track.id,
                transition_id=None,
                start_ms=solo_start_ms,
                end_ms=solo_end_ms,
                duration_ms=solo_end_ms - solo_start_ms
            ))
            position += 1

        # Add transition to next track (if not last)
        if not is_last:
            next_track = tracks[i + 1]

            # Calculate transition duration based on energy
            transition_bars = calculate_transition_duration_bars(track.energy, next_track.energy)
            transition_duration_ms = bars_to_ms(transition_bars, track.bpm)

            # The transition covers:
            # - Track A: from outro_start to outro_start + transition_duration (or end)
            # - Track B: from 0 to intro_end (or transition_duration)

            segments.append(SegmentInfo(
                position=position,
                type='TRANSITION',
                track_id=None,
                transition_id=f"{track.id}_{next_track.id}",  # Composite ID
                start_ms=0,  # Transition audio starts at 0
                end_ms=transition_duration_ms,
                duration_ms=transition_duration_ms
            ))
            position += 1

    return segments


def find_nearest_downbeat(beats: List[float], target_time: float) -> float:
    """Find the nearest downbeat (beat_index % 4 == 0) to target time."""
    if not beats:
        return target_time

    # Find downbeats (every 4th beat)
    downbeats = [beats[i] for i in range(0, len(beats), 4)]

    if not downbeats:
        return target_time

    # Find nearest
    nearest = min(downbeats, key=lambda b: abs(b - target_time))
    return nearest


def generate_transition_audio(
    track_a: TrackData,
    track_b: TrackData,
    output_path: str,
    progress_callback: Optional[callable] = None
) -> TransitionResult:
    """
    Generate transition by delegating to the Draft Engine (Unified Logic).
    """
    # Step 1: Prepare params for Draft Engine
    # We use the Draft Engine because it has the Smart Logic (LLM, Bass Swap, Smart Start/End)
    from src.mixing.draft_transition_generator import (
        generate_draft_transition,
        DraftTransitionParams,
        DraftTransitionResult
    )

    logger.info(
        "Delegating transition to Draft Engine (Unified)",
        from_track=track_a.id,
        to_track=track_b.id
    )
    
    # Map TrackData to DraftTransitionParams
    draft_params = DraftTransitionParams(
        draft_id=f"mix_{track_a.id}_{track_b.id}",
        track_a_path=track_a.file_path,
        track_b_path=track_b.file_path,
        track_a_bpm=track_a.bpm,
        track_b_bpm=track_b.bpm,
        track_a_beats=track_a.beats,
        track_b_beats=track_b.beats,
        track_a_outro_start_ms=int(track_a.outro_start_ms),
        track_b_intro_end_ms=int(track_b.intro_end_ms),
        track_a_energy=track_a.energy,
        track_b_energy=track_b.energy,
        track_a_duration_ms=int(track_a.duration_ms),
        track_b_duration_ms=int(track_b.duration_ms),
        output_path=output_path
    )
    
    # Step 2: Generate using Draft Engine
    # This ensures consistency: Draft results = Full Mix results
    result: DraftTransitionResult = generate_draft_transition(
        draft_params,
        progress_callback=progress_callback
    )
    
    # Step 3: Load the generated audio to return it as numpy array
    try:
        # Load at 44100Hz
        audio, sr = sf.read(output_path)
        
        # Ensure 2D array (samples, channels)
        if len(audio.shape) == 1:
            audio = np.stack([audio, audio], axis=1)
        elif audio.shape[0] == 2 and audio.shape[1] > 2:
            # Transpose if channels are first dimension
            audio = audio.T
            
        return TransitionResult(
            audio=audio,
            sample_rate=sr,
            duration_ms=result.transition_duration_ms,
            track_a_cut_ms=result.track_a_play_until_ms,
            track_b_start_ms=result.track_b_start_from_ms
        )
        
    except Exception as e:
        logger.error("Failed to load generated transition", error=str(e))
        raise


def _align_stems_length(stems: Dict[str, np.ndarray], target_samples: int) -> Dict[str, np.ndarray]:
    """Align all stems to target length (pad or trim)."""
    aligned = {}
    for stem_name, stem_audio in stems.items():
        if len(stem_audio.shape) == 1:
            # Mono: reshape to (samples, 1)
            stem_audio = stem_audio.reshape(-1, 1)

        current_samples = stem_audio.shape[0]

        if current_samples < target_samples:
            # Pad with zeros
            padding = np.zeros((target_samples - current_samples, stem_audio.shape[1]))
            aligned[stem_name] = np.vstack([stem_audio, padding])
        else:
            # Trim
            aligned[stem_name] = stem_audio[:target_samples]

    return aligned


def mix_stems_4_phase(
    stems_a: Dict[str, np.ndarray],
    stems_b: Dict[str, np.ndarray],
    transition_bars: int,
    bpm: float,
    sample_rate: int
) -> np.ndarray:
    """
    Mix two sets of stems using 4-phase professional DJ transition.

    Phase 1 (bars 1-4): A full, B drums fade in 0→70%, B other fade in 0→30%
    Phase 2 (bars 5-8): A bass fade 100→20%, B drums 70→100%, B bass fade 0→100%
    Phase 3 (bars 9-12): A vocals fade 100→0%, B vocals fade 0→100%, B other 50→100%
    Phase 4 (bars 13-16): A all fade out, B all 100%
    """
    phase_bars = transition_bars // 4
    phase_samples = ms_to_samples(bars_to_ms(phase_bars, bpm), sample_rate)
    total_samples = phase_samples * 4

    # Ensure we have all stem types, fill with zeros if missing
    stem_names = ['drums', 'bass', 'vocals', 'other']

    def get_stem(stems: Dict, name: str) -> np.ndarray:
        if name in stems:
            return stems[name]
        # Return zeros with same shape as any existing stem
        for s in stems.values():
            return np.zeros_like(s)
        return np.zeros((total_samples, 2))

    # Get stems (default to stereo)
    drums_a = get_stem(stems_a, 'drums')
    bass_a = get_stem(stems_a, 'bass')
    vocals_a = get_stem(stems_a, 'vocals')
    other_a = get_stem(stems_a, 'other')

    drums_b = get_stem(stems_b, 'drums')
    bass_b = get_stem(stems_b, 'bass')
    vocals_b = get_stem(stems_b, 'vocals')
    other_b = get_stem(stems_b, 'other')

    # Initialize output
    output = np.zeros((total_samples, 2))

    for phase in range(4):
        start = phase * phase_samples
        end = start + phase_samples

        # Create fade curves for this phase
        fade_in = np.linspace(0, 1, phase_samples).reshape(-1, 1)
        fade_out = np.linspace(1, 0, phase_samples).reshape(-1, 1)

        # Slice stems for this phase
        da, ba, va, oa = drums_a[start:end], bass_a[start:end], vocals_a[start:end], other_a[start:end]
        db, bb, vb, ob = drums_b[start:end], bass_b[start:end], vocals_b[start:end], other_b[start:end]

        if phase == 0:
            # Phase 1: A full, B drums 0→70%, B other 0→30%
            output[start:end] += da + ba + va + oa  # A at 100%
            output[start:end] += db * fade_in * 0.7  # B drums fade to 70%
            output[start:end] += ob * fade_in * 0.3  # B other fade to 30%

        elif phase == 1:
            # Phase 2: A bass 100→20%, A others full, B drums 70→100%, B bass 0→100%
            output[start:end] += da + va + oa  # A drums, vocals, other at 100%
            output[start:end] += ba * (1 - fade_in * 0.8)  # A bass fade to 20%
            output[start:end] += db * (0.7 + fade_in * 0.3)  # B drums 70→100%
            output[start:end] += bb * fade_in  # B bass fade to 100%
            output[start:end] += ob * 0.3  # B other stay at 30%

        elif phase == 2:
            # Phase 3: A vocals 100→0%, A bass 20%, B vocals 0→100%, B other 30→100%
            output[start:end] += da * 0.5  # A drums drop to 50%
            output[start:end] += ba * 0.2  # A bass stay at 20%
            output[start:end] += va * fade_out  # A vocals fade out
            output[start:end] += oa * 0.5  # A other drop to 50%
            output[start:end] += db  # B drums at 100%
            output[start:end] += bb  # B bass at 100%
            output[start:end] += vb * fade_in  # B vocals fade in
            output[start:end] += ob * (0.3 + fade_in * 0.7)  # B other 30→100%

        else:  # phase == 3
            # Phase 4: A all fade out, B at 100%
            output[start:end] += da * fade_out * 0.5  # A drums fade from 50%
            output[start:end] += ba * fade_out * 0.2  # A bass fade from 20%
            output[start:end] += oa * fade_out * 0.5  # A other fade from 50%
            output[start:end] += db + bb + vb + ob  # B all at 100%

    return output.T  # Return as (channels, samples)


def apply_limiter(audio: np.ndarray, threshold_db: float = -1.0) -> np.ndarray:
    """Apply brick-wall limiter to prevent clipping."""
    threshold = 10 ** (threshold_db / 20)

    # Find peaks
    peak = np.max(np.abs(audio))

    if peak > threshold:
        # Apply gain reduction
        gain = threshold / peak
        audio = audio * gain
        logger.debug("Limiter applied", peak=peak, gain=gain)

    return audio





def generate_mix_for_project(
    project_id: str,
    tracks_data: List[Dict[str, Any]],
    transitions_data: List[Dict[str, Any]],
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Generate the full mix for a project.

    Args:
        project_id: Project ID
        tracks_data: List of track data with analysis
        transitions_data: List of transition metadata
        progress_callback: Optional callback(message, percent)

    Returns:
        Dict with segments info, generated file paths, and final output file
    """
    logger.info("Starting mix generation", project_id=project_id, track_count=len(tracks_data))

    # Convert to TrackData objects
    tracks = []
    for td in tracks_data:
        analysis = td.get('analysis', {})
        duration_ms = (td.get('duration') or 0) * 1000  # Convert to ms

        tracks.append(TrackData(
            id=td['id'],
            file_path=td['filePath'],
            duration_ms=duration_ms,
            bpm=analysis.get('bpm', 120),
            energy=analysis.get('energy', 0.5),
            beats=analysis.get('beats', []),
            intro_end_ms=(analysis.get('introEnd') or 0) * 1000 if analysis.get('introEnd') else 0,
            outro_start_ms=(analysis.get('outroStart') or 0) * 1000 if analysis.get('outroStart') else 0
        ))

    # Calculate segments
    segments = calculate_segments(tracks)

    logger.info("Calculated segments", segment_count=len(segments))

    # Generate transition audio files
    output_dir = Path(settings.output_path) / 'mix_segments' / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        'segments': [],
        'transition_files': {},
        'outputFile': None,
        'totalDurationMs': 0
    }

    transition_segments = [s for s in segments if s.type == 'TRANSITION']
    total_transitions = len(transition_segments)

    for i, segment in enumerate(segments):
        segment_data = {
            'position': segment.position,
            'type': segment.type,
            'trackId': segment.track_id,
            'transitionId': segment.transition_id,
            'startMs': segment.start_ms,
            'endMs': segment.end_ms,
            'durationMs': segment.duration_ms,
            'audioFilePath': None
        }

        if segment.type == 'TRANSITION':
            # Find the two tracks for this transition
            trans_idx = [s for s in segments[:segment.position] if s.type == 'SOLO']
            if len(trans_idx) >= 1:
                track_a_idx = len(trans_idx) - 1
                track_b_idx = track_a_idx + 1

                if track_b_idx < len(tracks):
                    track_a = tracks[track_a_idx]
                    track_b = tracks[track_b_idx]

                    # Generate transition audio
                    output_file = output_dir / f"transition_{track_a.id}_{track_b.id}.wav"

                    current_transition = transition_segments.index(segment) + 1

                    def trans_progress(msg, pct):
                        if progress_callback:
                            # Transitions use 0-70% of progress
                            overall_pct = int(((current_transition - 1) / total_transitions + pct / 100 / total_transitions) * 70)
                            progress_callback(f"Transition {current_transition}/{total_transitions}: {msg}", overall_pct)

                    try:
                        result = generate_transition_audio(
                            track_a, track_b,
                            str(output_file),
                            trans_progress
                        )

                        relative_path = f"mix_segments/{project_id}/{output_file.name}"
                        segment_data['audioFilePath'] = relative_path
                        segment_data['durationMs'] = result.duration_ms
                        results['transition_files'][segment.transition_id] = relative_path
                        
                        # CRITICAL FIX: Update adjacent Solo segments to prevent duplicate audio
                        # 1. Update previous segment (Solo A) end point
                        if results['segments']:
                            prev_segment = results['segments'][-1]
                            if prev_segment['type'] == 'SOLO' and prev_segment['trackId'] == track_a.id:
                                # Cut A where the transition actually started using A
                                # Note: track_a_cut_ms from draft engine is where A *stops* playing in the transition context
                                # But we want where Solo A stops. 
                                # If transition uses A from X to Y, Solo A should stop at X.
                                # Wait, track_a_cut_ms usually means "Play A until X".
                                # Draft result: track_a_play_until_ms = where the *transition file* handles A.
                                # Actually, track_a_play_until_ms = Outro Start usually? 
                                # No, the transition file contains A from [OutroStart] to [OutroEnd].
                                # So Solo A must end at [OutroStart].
                                # Let's check what track_a_cut_ms represents in draft engine.
                                # In draft_transition_generator: track_a_cut_ms = int(a_cue_time * 1000) + duration_ms ? 
                                # No, track_a_cut_ms = track_a_play_until_ms = where we STOP playing the solo track.
                                # The transition starts exactly there.
                                
                                # Use the value returned by the engine as the cut point.
                                prev_segment['endMs'] = result.track_a_cut_ms
                                prev_segment['durationMs'] = max(0, prev_segment['endMs'] - prev_segment['startMs'])
                                logger.info("Adjusted Solo A end", track=track_a.id, end_ms=result.track_a_cut_ms)
                        
                        # 2. Update next segment (Solo B) start point
                        if i + 1 < len(segments):
                            next_segment = segments[i+1]
                            if next_segment.type == 'SOLO' and next_segment.track_id == track_b.id:
                                # Start B where the transition actually ends/releases B
                                next_segment.start_ms = result.track_b_start_ms
                                next_segment.duration_ms = max(0, next_segment.end_ms - next_segment.start_ms)
                                logger.info("Adjusted Solo B start", track=track_b.id, start_ms=result.track_b_start_ms)

                    except Exception as e:
                        logger.error("Transition generation failed", error=str(e), track_a=track_a.id, track_b=track_b.id)
                        segment_data['audioError'] = str(e)

        results['segments'].append(segment_data)

    # Skip concatenation as requested by user
    # The frontend will play segments individually using the adjusted start/end times
    logger.info("Mix generation complete (segments only)", project_id=project_id, segments=len(results['segments']))
    
    return results

