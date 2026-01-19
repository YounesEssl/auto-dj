"""
Professional BPM and Beat Detection Module
Uses madmom RNN deep learning for industry-standard accuracy (~95%)
Falls back to librosa if madmom unavailable
"""

from typing import Tuple, List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()

# Try to import madmom (deep learning beat tracking)
try:
    import madmom
    from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor
    from madmom.features.tempo import TempoEstimationProcessor
    MADMOM_AVAILABLE = True
    logger.info("Madmom loaded - using RNN deep learning for BPM")
except ImportError:
    MADMOM_AVAILABLE = False
    logger.warning("Madmom not available - falling back to librosa")
    import librosa

# Typical BPM ranges for DJ music
PREFERRED_BPM_RANGE = (85, 145)


def detect_bpm(audio: np.ndarray, sample_rate: int) -> Tuple[float, float]:
    """
    Detect the BPM (tempo) of an audio signal.

    Uses madmom RNN when available (professional accuracy),
    falls back to librosa otherwise.

    Returns:
        Tuple of (bpm, confidence)
    """
    result = detect_bpm_with_alternatives(audio, sample_rate)
    return result["bpm"], result["confidence"]


def detect_bpm_with_alternatives(audio: np.ndarray, sample_rate: int) -> dict:
    """
    Detect BPM with beat positions and alternatives.
    """
    if MADMOM_AVAILABLE:
        return _detect_bpm_madmom(audio, sample_rate)
    else:
        return _detect_bpm_librosa(audio, sample_rate)


def _detect_bpm_madmom(audio: np.ndarray, sample_rate: int) -> dict:
    """
    Detect BPM using madmom's RNN beat tracker.
    This is the same technology used by professional DJ software.
    """
    try:
        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Resample to madmom's expected rate if needed
        if sample_rate != 44100:
            import librosa
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=44100)
            sample_rate = 44100

        # RNN Beat Processor - uses trained neural network
        beat_processor = RNNBeatProcessor()

        # Process audio to get beat activations
        beat_activations = beat_processor(audio)

        # DBN (Dynamic Bayesian Network) for beat tracking
        beat_tracker = DBNBeatTrackingProcessor(fps=100)
        beats = beat_tracker(beat_activations)

        if len(beats) < 2:
            logger.warning("Not enough beats detected, falling back to librosa")
            return _detect_bpm_librosa(audio, sample_rate)

        # Calculate BPM from beat intervals
        beat_intervals = np.diff(beats)

        # Filter outliers (beats too close or too far apart)
        valid_intervals = beat_intervals[
            (beat_intervals > 0.25) & (beat_intervals < 2.0)
        ]

        if len(valid_intervals) == 0:
            return _detect_bpm_librosa(audio, sample_rate)

        # Primary BPM from median interval (robust to outliers)
        median_interval = np.median(valid_intervals)
        primary_bpm = 60.0 / median_interval

        # Also try tempo estimation processor for alternatives
        tempo_processor = TempoEstimationProcessor(fps=100)
        tempo_estimates = tempo_processor(beat_activations)

        # Get top tempo candidates
        alternatives = []
        if len(tempo_estimates) > 0:
            for tempo, strength in tempo_estimates[:3]:
                if abs(tempo - primary_bpm) > 5:  # Different from primary
                    alternatives.append(float(tempo))

        # Adjust to preferred range if needed (half/double time)
        adjusted_bpm = _adjust_to_preferred_range(primary_bpm)

        # Calculate confidence from beat consistency
        confidence = _calculate_madmom_confidence(valid_intervals)

        # Boost confidence if adjusted BPM matches a tempo estimate
        for tempo, strength in tempo_estimates[:3]:
            if abs(adjusted_bpm - tempo) < 3:
                confidence = min(0.98, confidence * 1.1)
                break

        logger.debug(
            "BPM detected (madmom RNN)",
            bpm=adjusted_bpm,
            raw_bpm=primary_bpm,
            confidence=confidence,
            beats_count=len(beats),
            alternatives=alternatives[:3]
        )

        return {
            "bpm": round(float(adjusted_bpm), 1),
            "confidence": round(float(confidence), 3),
            "alternatives": [round(float(t), 1) for t in alternatives[:3]],
            "beats": beats.tolist(),  # Beat positions in seconds
            "raw_bpm": round(float(primary_bpm), 1)
        }

    except Exception as e:
        logger.error("Madmom BPM detection failed, falling back to librosa", error=str(e))
        return _detect_bpm_librosa(audio, sample_rate)


def _detect_bpm_librosa(audio: np.ndarray, sample_rate: int) -> dict:
    """
    Fallback BPM detection using librosa.
    """
    import librosa

    try:
        # Beat tracking
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sample_rate)

        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            tempo = float(tempo)

        # Get beat times
        beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate)

        # Calculate confidence from beat consistency
        if len(beat_times) > 2:
            intervals = np.diff(beat_times)
            cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
            confidence = max(0.3, min(0.85, 1.0 - cv * 1.5))
        else:
            confidence = 0.3

        # Adjust to preferred range
        adjusted_bpm = _adjust_to_preferred_range(tempo)

        logger.debug(
            "BPM detected (librosa fallback)",
            bpm=adjusted_bpm,
            raw_bpm=tempo,
            confidence=confidence
        )

        return {
            "bpm": round(float(adjusted_bpm), 1),
            "confidence": round(float(confidence), 3),
            "alternatives": [],
            "beats": beat_times.tolist(),
            "raw_bpm": round(float(tempo), 1)
        }

    except Exception as e:
        logger.error("Librosa BPM detection failed", error=str(e))
        return {
            "bpm": 120.0,
            "confidence": 0.3,
            "alternatives": [],
            "beats": [],
            "raw_bpm": 120.0
        }


def _adjust_to_preferred_range(bpm: float) -> float:
    """
    Adjust BPM to preferred DJ range using half/double time.
    """
    if bpm < PREFERRED_BPM_RANGE[0]:
        # Try doubling
        if PREFERRED_BPM_RANGE[0] <= bpm * 2 <= PREFERRED_BPM_RANGE[1]:
            return bpm * 2
    elif bpm > PREFERRED_BPM_RANGE[1]:
        # Try halving
        if PREFERRED_BPM_RANGE[0] <= bpm / 2 <= PREFERRED_BPM_RANGE[1]:
            return bpm / 2
    return bpm


def _calculate_madmom_confidence(beat_intervals: np.ndarray) -> float:
    """
    Calculate confidence from madmom beat intervals.
    """
    if len(beat_intervals) < 3:
        return 0.5

    # Use coefficient of variation
    cv = np.std(beat_intervals) / np.mean(beat_intervals)

    # Lower CV = more consistent = higher confidence
    # Madmom is generally more accurate, so we use a higher base
    confidence = max(0.5, min(0.95, 1.0 - cv * 1.2))

    return float(confidence)


def get_beat_grid(audio: np.ndarray, sample_rate: int) -> Optional[List[float]]:
    """
    Get precise beat positions for the track.
    Useful for beat-matching and quantization.
    """
    result = detect_bpm_with_alternatives(audio, sample_rate)
    return result.get("beats", [])


def suggest_dj_tempo(bpm: float, alternatives: List[float]) -> float:
    """
    Suggest the best tempo for DJ mixing.
    Prefers tempos in the 115-135 range.
    """
    all_tempos = [bpm] + alternatives
    ideal_center = 124

    scored = [(t, abs(t - ideal_center)) for t in all_tempos]
    scored.sort(key=lambda x: x[1])

    return scored[0][0]
