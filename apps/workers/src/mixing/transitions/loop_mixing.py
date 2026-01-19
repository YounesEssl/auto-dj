"""
Loop Mixing - Extend or create sections.

Looping allows:
- Extending an intro too short for a longer blend
- Maintaining a breakdown to build more tension
- Creating custom patterns

STANDARD LOOP SIZES:
- 1 bar: Rhythmic effects
- 2 bars: Short loop, maintains groove
- 4 bars: Standard, natural feel
- 8 bars: Complete section
- 16 bars: Full phrase
"""

import numpy as np
from typing import Optional
import structlog

logger = structlog.get_logger()


def create_loop(
    audio: np.ndarray,
    loop_start: float,
    loop_length_bars: int,
    bpm: float,
    repetitions: int,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a perfect tempo-synced loop.

    Args:
        audio: Source audio
        loop_start: Start time of loop section (seconds)
        loop_length_bars: Length of loop in bars
        bpm: Tempo
        repetitions: Number of times to repeat the loop
        sr: Sample rate

    Returns:
        Repeated loop audio
    """
    bar_duration = (60.0 / bpm) * 4
    loop_duration = loop_length_bars * bar_duration
    loop_samples = int(loop_duration * sr)

    start_sample = int(loop_start * sr)
    end_sample = start_sample + loop_samples

    # Validate bounds
    if start_sample >= len(audio):
        logger.warning("Loop start beyond audio length")
        return audio

    if end_sample > len(audio):
        end_sample = len(audio)
        loop_samples = end_sample - start_sample

    # Extract loop section
    loop_audio = audio[start_sample:end_sample].copy()

    # Apply crossfade at loop boundaries to avoid clicks
    fade_samples = int(0.01 * sr)  # 10ms fade
    fade_samples = min(fade_samples, loop_samples // 4)

    if fade_samples > 0:
        # Fade in at start
        fade_in = np.linspace(0, 1, fade_samples)
        loop_audio[:fade_samples] *= fade_in

        # Fade out at end
        fade_out = np.linspace(1, 0, fade_samples)
        loop_audio[-fade_samples:] *= fade_out

    # Create seamless loop using overlap-add
    # For clean looping, crossfade the end into the start
    if loop_samples > fade_samples * 2:
        crossfade_region = fade_samples
        # The end of one repetition fades into the start of the next
        loop_end = loop_audio[-crossfade_region:].copy()
        loop_start_region = loop_audio[:crossfade_region].copy()

        # Create crossfade
        cf_fade_out = np.linspace(1, 0, crossfade_region)
        cf_fade_in = np.linspace(0, 1, crossfade_region)

        loop_transition = loop_end * cf_fade_out + loop_start_region * cf_fade_in
    else:
        crossfade_region = 0
        loop_transition = np.array([])

    # Build repeated loop
    # Each repetition is: full loop minus crossfade region
    single_rep_samples = loop_samples - crossfade_region if crossfade_region > 0 else loop_samples

    if repetitions <= 1:
        return loop_audio

    # First repetition is full
    result_parts = [loop_audio]

    # Subsequent repetitions use crossfade transition
    for i in range(1, repetitions):
        if crossfade_region > 0:
            # Remove end of previous (already faded)
            result_parts[-1] = result_parts[-1][:-crossfade_region]
            # Add transition
            result_parts.append(loop_transition)
            # Add rest of loop (after the crossfade start region)
            result_parts.append(loop_audio[crossfade_region:])
        else:
            result_parts.append(loop_audio)

    extended = np.concatenate(result_parts)

    return extended


def extend_section(
    audio: np.ndarray,
    section_start: float,
    section_end: float,
    target_duration_bars: int,
    bpm: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Extend a section (intro, outro, breakdown) to a desired duration.

    Args:
        audio: Full track audio
        section_start: Start of section to extend (seconds)
        section_end: End of section to extend (seconds)
        target_duration_bars: Desired duration in bars
        bpm: Tempo
        sr: Sample rate

    Returns:
        Full audio with extended section
    """
    bar_duration = (60.0 / bpm) * 4
    current_duration = section_end - section_start
    current_bars = current_duration / bar_duration
    target_duration = target_duration_bars * bar_duration

    if target_duration <= current_duration:
        # No extension needed
        return audio

    # Calculate how many repetitions we need
    repetitions_needed = int(np.ceil(target_duration / current_duration))

    # Create the loop
    extended_section = create_loop(
        audio=audio,
        loop_start=section_start,
        loop_length_bars=int(np.ceil(current_bars)),
        bpm=bpm,
        repetitions=repetitions_needed,
        sr=sr
    )

    # Trim to exact target duration
    target_samples = int(target_duration * sr)
    if len(extended_section) > target_samples:
        extended_section = extended_section[:target_samples]

    # Build the result: before section + extended section + after section
    section_start_sample = int(section_start * sr)
    section_end_sample = int(section_end * sr)

    before = audio[:section_start_sample]
    after = audio[section_end_sample:]

    result = np.concatenate([before, extended_section, after])

    return result


def create_seamless_loop(
    audio: np.ndarray,
    loop_start: float,
    loop_end: float,
    crossfade_duration: float = 0.05,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a seamlessly looping audio segment.

    Uses crossfade at the boundaries to ensure clean looping.

    Args:
        audio: Source audio
        loop_start: Start time (seconds)
        loop_end: End time (seconds)
        crossfade_duration: Crossfade duration at boundaries (seconds)
        sr: Sample rate

    Returns:
        Seamlessly loopable audio segment
    """
    start_sample = int(loop_start * sr)
    end_sample = int(loop_end * sr)
    crossfade_samples = int(crossfade_duration * sr)

    # Validate
    if start_sample >= len(audio) or end_sample > len(audio):
        return audio[start_sample:min(end_sample, len(audio))]

    if end_sample - start_sample < crossfade_samples * 2:
        return audio[start_sample:end_sample]

    loop = audio[start_sample:end_sample].copy()

    # Create crossfade region
    # The end of the loop fades out while the start fades in
    fade_out = np.linspace(1, 0, crossfade_samples)
    fade_in = np.linspace(0, 1, crossfade_samples)

    # Apply fades
    loop[:crossfade_samples] *= fade_in
    loop[-crossfade_samples:] *= fade_out

    # Create the transition segment (end + start crossfaded)
    end_segment = audio[end_sample - crossfade_samples:end_sample].copy()
    start_segment = audio[start_sample:start_sample + crossfade_samples].copy()

    transition = end_segment * fade_out + start_segment * fade_in

    # The seamless loop is: middle part + transition that connects to start
    middle = loop[crossfade_samples:-crossfade_samples]
    seamless = np.concatenate([middle, transition])

    return seamless


def create_loop_transition(
    audio_a: np.ndarray,
    audio_b: np.ndarray,
    loop_section_a: tuple,
    loop_repetitions: int,
    transition_duration_bars: int,
    bpm: float,
    sr: int = 44100
) -> np.ndarray:
    """
    Create a transition using a loop from track A.

    Extends a section of A using looping, then transitions to B.

    Args:
        audio_a: Outgoing track
        audio_b: Incoming track
        loop_section_a: (start, end) times of section to loop
        loop_repetitions: Number of loop repetitions
        transition_duration_bars: Duration of transition into B
        bpm: Tempo
        sr: Sample rate

    Returns:
        Transition with looped section
    """
    loop_start, loop_end = loop_section_a
    loop_duration = loop_end - loop_start
    loop_bars = int(np.ceil(loop_duration / ((60.0 / bpm) * 4)))

    # Create the looped section
    looped_section = create_loop(
        audio_a,
        loop_start=loop_start,
        loop_length_bars=loop_bars,
        bpm=bpm,
        repetitions=loop_repetitions,
        sr=sr
    )

    # Get audio before the loop point
    loop_start_sample = int(loop_start * sr)
    before_loop = audio_a[:loop_start_sample]

    # Transition from looped section to B
    bar_duration = (60.0 / bpm) * 4
    trans_duration = transition_duration_bars * bar_duration
    trans_samples = int(trans_duration * sr)

    # Create crossfade from loop to B
    if trans_samples <= len(looped_section) and trans_samples <= len(audio_b):
        # Equal power crossfade
        t = np.linspace(0, np.pi / 2, trans_samples)
        fade_out = np.cos(t)
        fade_in = np.sin(t)

        loop_end_portion = looped_section[-trans_samples:] * fade_out
        b_start_portion = audio_b[:trans_samples] * fade_in

        transition = loop_end_portion + b_start_portion

        # Build result
        result = np.concatenate([
            before_loop,
            looped_section[:-trans_samples],
            transition,
            audio_b[trans_samples:]
        ])
    else:
        # Simple concatenation
        result = np.concatenate([before_loop, looped_section, audio_b])

    return result


def find_best_loop_point(
    audio: np.ndarray,
    target_bars: int,
    bpm: float,
    search_start: float = 0,
    search_end: Optional[float] = None,
    sr: int = 44100
) -> tuple:
    """
    Find the best loop point for seamless looping.

    Analyzes audio to find a point where the loop will sound natural.

    Args:
        audio: Source audio
        target_bars: Desired loop length in bars
        bpm: Tempo
        search_start: Start of search region (seconds)
        search_end: End of search region (seconds)
        sr: Sample rate

    Returns:
        Tuple of (loop_start, loop_end) in seconds
    """
    import librosa

    bar_duration = (60.0 / bpm) * 4
    target_duration = target_bars * bar_duration
    target_samples = int(target_duration * sr)

    if search_end is None:
        search_end = len(audio) / sr - target_duration

    search_start_sample = int(search_start * sr)
    search_end_sample = int(search_end * sr)

    # Calculate RMS energy profile
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]

    best_score = float('inf')
    best_start = search_start_sample

    # Search for the best loop point (where start and end have similar energy)
    step_samples = int(0.5 * sr)  # Search every 0.5 seconds

    for start in range(search_start_sample, search_end_sample, step_samples):
        end = start + target_samples
        if end > len(audio):
            break

        # Compare energy at loop boundaries
        start_frame = start // 512
        end_frame = end // 512

        if start_frame < len(rms) and end_frame < len(rms):
            # Energy difference at boundary
            energy_diff = abs(rms[start_frame] - rms[end_frame])

            # Also check spectral similarity (simplified)
            if energy_diff < best_score:
                best_score = energy_diff
                best_start = start

    best_end = best_start + target_samples

    return (best_start / sr, best_end / sr)
