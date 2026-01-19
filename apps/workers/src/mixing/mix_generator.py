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
    Generate professional DJ-style transition between two tracks.

    Steps:
    1. Calculate transition duration based on energy
    2. Extract outro of Track A and intro of Track B
    3. Separate stems with Demucs
    4. Time-stretch Track B to match Track A's BPM
    5. Align beats (beatmatching)
    6. Mix with 4-phase crossfade and EQ
    7. Export
    """
    logger.info(
        "Generating transition",
        from_track=track_a.id,
        to_track=track_b.id,
        bpm_a=track_a.bpm,
        bpm_b=track_b.bpm
    )

    # Step 1: Calculate duration
    transition_bars = calculate_transition_duration_bars(track_a.energy, track_b.energy)
    transition_duration_ms = bars_to_ms(transition_bars, track_a.bpm)
    transition_samples = ms_to_samples(transition_duration_ms)

    logger.info(
        "Transition parameters",
        bars=transition_bars,
        duration_ms=transition_duration_ms,
        target_bpm=track_a.bpm
    )

    if progress_callback:
        progress_callback("Loading audio", 5)

    # Step 2: Load and extract segments
    audio_a, sr_a = load_audio(track_a.file_path)
    audio_b, sr_b = load_audio(track_b.file_path)

    # Calculate extraction points
    outro_start_ms = track_a.outro_start_ms
    if outro_start_ms is None or outro_start_ms <= 0:
        outro_start_ms = get_default_outro_start_ms(track_a.bpm, track_a.duration_ms)

    intro_end_ms = track_b.intro_end_ms
    if intro_end_ms is None or intro_end_ms <= 0:
        intro_end_ms = get_default_intro_end_ms(track_b.bpm, track_b.duration_ms)

    # Extract segments (use transition_duration or available length)
    outro_start_sample = ms_to_samples(int(outro_start_ms), sr_a)
    outro_end_sample = min(
        outro_start_sample + ms_to_samples(transition_duration_ms, sr_a),
        len(audio_a)
    )

    intro_end_sample = min(
        ms_to_samples(transition_duration_ms, sr_b),
        ms_to_samples(int(intro_end_ms), sr_b),
        len(audio_b)
    )

    segment_a = audio_a[outro_start_sample:outro_end_sample]
    segment_b = audio_b[0:intro_end_sample]

    logger.info(
        "Extracted segments",
        segment_a_samples=len(segment_a),
        segment_b_samples=len(segment_b)
    )

    if progress_callback:
        progress_callback("Separating stems (Track A)", 10)

    # Step 3: Separate stems
    stems_a = separate_stems(segment_a, sr_a)

    if progress_callback:
        progress_callback("Separating stems (Track B)", 40)

    stems_b = separate_stems(segment_b, sr_b)

    if progress_callback:
        progress_callback("Processing audio", 70)

    # Step 4: Time-stretch Track B to match BPM
    stretch_ratio, is_within_limits = calculate_stretch_ratio(track_b.bpm, track_a.bpm)

    if not is_within_limits:
        logger.warning(
            "BPM difference too large, using simple crossfade",
            bpm_a=track_a.bpm,
            bpm_b=track_b.bpm,
            ratio=stretch_ratio
        )
        # Fallback: simple crossfade without time-stretch
        stretched_stems_b = stems_b
    else:
        # Time-stretch each stem
        stretched_stems_b = {}
        for stem_name, stem_audio in stems_b.items():
            stretched_stems_b[stem_name] = time_stretch(stem_audio, sr_b, stretch_ratio)

    # Step 5: Align lengths (make both segment sets same duration)
    target_samples = transition_samples

    # Pad or trim stems to target length
    aligned_stems_a = _align_stems_length(stems_a, target_samples)
    aligned_stems_b = _align_stems_length(stretched_stems_b, target_samples)

    if progress_callback:
        progress_callback("Mixing transition", 80)

    # Step 6: Mix with 4-phase crossfade
    mixed = mix_stems_4_phase(
        aligned_stems_a,
        aligned_stems_b,
        transition_bars,
        track_a.bpm,
        SAMPLE_RATE
    )

    # Step 7: Apply limiter to prevent clipping
    mixed = apply_limiter(mixed, -1.0)  # Limit to -1dB

    if progress_callback:
        progress_callback("Saving transition", 95)

    # Save to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, mixed.T, SAMPLE_RATE)

    logger.info(
        "Transition generated",
        output_path=output_path,
        duration_ms=transition_duration_ms
    )

    if progress_callback:
        progress_callback("Complete", 100)

    return TransitionResult(
        audio=mixed,
        sample_rate=SAMPLE_RATE,
        duration_ms=transition_duration_ms
    )


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
        Dict with segments info and generated file paths
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
        'transition_files': {}
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
                            overall_pct = int(((current_transition - 1) / total_transitions + pct / 100 / total_transitions) * 100)
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

                    except Exception as e:
                        logger.error("Transition generation failed", error=str(e), track_a=track_a.id, track_b=track_b.id)
                        segment_data['audioError'] = str(e)

        results['segments'].append(segment_data)

    logger.info("Mix generation complete", project_id=project_id, segments=len(results['segments']))

    return results
