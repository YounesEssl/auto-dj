"""
Professional Musical Key Detection Module
Uses essentia (Spotify-level accuracy) with librosa fallback
"""

from typing import Tuple, Dict, List, Optional
import numpy as np
import structlog

logger = structlog.get_logger()

# Try to import essentia (available in Docker with Python 3.11)
try:
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
    logger.info("Essentia loaded - using professional key detection")
except ImportError:
    ESSENTIA_AVAILABLE = False
    logger.warning("Essentia not available - falling back to librosa")
    import librosa

# Pitch classes
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Key profiles for librosa fallback
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def detect_key(audio: np.ndarray, sample_rate: int) -> Tuple[str, float]:
    """
    Detect the musical key of an audio signal.

    Uses essentia's KeyExtractor when available (professional accuracy),
    falls back to librosa-based detection otherwise.

    Returns:
        Tuple of (key_string, confidence)
    """
    if ESSENTIA_AVAILABLE:
        return _detect_key_essentia(audio, sample_rate)
    else:
        return _detect_key_librosa(audio, sample_rate)


def _detect_key_essentia(audio: np.ndarray, sample_rate: int) -> Tuple[str, float]:
    """
    Detect key using essentia's professional algorithms.
    Uses the same algorithms as Spotify, Beatport, etc.
    """
    try:
        # Ensure audio is float32 and mono
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Resample to 44100 if needed (essentia's default)
        if sample_rate != 44100:
            resampler = es.Resample(inputSampleRate=sample_rate, outputSampleRate=44100)
            audio = resampler(audio)

        # Use essentia's KeyExtractor (combines multiple algorithms)
        key_extractor = es.KeyExtractor(profileType='edma')  # EDMA profile for electronic music
        key, scale, strength = key_extractor(audio)

        # Format key string
        key_str = f"{key}{'m' if scale == 'minor' else ''}"

        # Strength is 0-1, use as confidence
        confidence = float(strength)

        # Also try with different profiles for comparison
        profiles_results = []
        for profile in ['temperley', 'krumhansl', 'edma']:
            try:
                extractor = es.KeyExtractor(profileType=profile)
                k, s, st = extractor(audio)
                profiles_results.append({
                    'key': f"{k}{'m' if s == 'minor' else ''}",
                    'strength': st,
                    'profile': profile
                })
            except:
                pass

        # If EDMA result differs from majority, boost confidence if they agree
        if profiles_results:
            votes = {}
            for r in profiles_results:
                votes[r['key']] = votes.get(r['key'], 0) + r['strength']

            # Find most voted key
            best_key_vote = max(votes.items(), key=lambda x: x[1])
            if best_key_vote[0] == key_str:
                # Boost confidence if profiles agree
                confidence = min(0.98, confidence * 1.15)

            logger.debug(
                "Essentia key analysis",
                primary=key_str,
                confidence=round(confidence, 3),
                profile_votes=votes
            )

        logger.info(
            "Key detected (essentia)",
            key=key_str,
            confidence=round(confidence, 3)
        )

        return key_str, round(confidence, 3)

    except Exception as e:
        logger.error("Essentia key detection failed, falling back to librosa", error=str(e))
        return _detect_key_librosa(audio, sample_rate)


def _detect_key_librosa(audio: np.ndarray, sample_rate: int) -> Tuple[str, float]:
    """
    Fallback key detection using librosa and Krumhansl-Schmuckler algorithm.
    """
    import librosa

    try:
        # Compute chromagram
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sample_rate)
        chroma_avg = np.mean(chroma, axis=1)
        chroma_avg = chroma_avg / (np.sum(chroma_avg) + 1e-8)

        best_key = None
        best_correlation = -1
        best_mode = "major"

        # Normalize profiles
        major_norm = MAJOR_PROFILE / np.sum(MAJOR_PROFILE)
        minor_norm = MINOR_PROFILE / np.sum(MINOR_PROFILE)

        for i, pitch in enumerate(PITCH_CLASSES):
            major_rotated = np.roll(major_norm, i)
            minor_rotated = np.roll(minor_norm, i)

            major_corr = np.corrcoef(chroma_avg, major_rotated)[0, 1]
            minor_corr = np.corrcoef(chroma_avg, minor_rotated)[0, 1]

            if major_corr > best_correlation:
                best_correlation = major_corr
                best_key = pitch
                best_mode = "major"

            if minor_corr > best_correlation:
                best_correlation = minor_corr
                best_key = pitch
                best_mode = "minor"

        confidence = float(max(0, (best_correlation + 1) / 2))
        key_str = f"{best_key}{'m' if best_mode == 'minor' else ''}"

        logger.debug(
            "Key detected (librosa)",
            key=key_str,
            mode=best_mode,
            correlation=round(best_correlation, 3),
            confidence=round(confidence, 3),
        )

        return key_str, round(float(confidence), 3)

    except Exception as e:
        logger.error("Librosa key detection failed", error=str(e))
        return "Am", 0.3


def detect_key_with_alternatives(audio: np.ndarray, sample_rate: int) -> dict:
    """
    Detect key with alternative possibilities.
    """
    if ESSENTIA_AVAILABLE:
        return _detect_key_with_alternatives_essentia(audio, sample_rate)
    else:
        return _detect_key_with_alternatives_librosa(audio, sample_rate)


def _detect_key_with_alternatives_essentia(audio: np.ndarray, sample_rate: int) -> dict:
    """Get key alternatives using essentia."""
    try:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if sample_rate != 44100:
            resampler = es.Resample(inputSampleRate=sample_rate, outputSampleRate=44100)
            audio = resampler(audio)

        # Get results from multiple profiles
        results = []
        for profile in ['edma', 'temperley', 'krumhansl', 'shaath']:
            try:
                extractor = es.KeyExtractor(profileType=profile)
                key, scale, strength = extractor(audio)
                key_str = f"{key}{'m' if scale == 'minor' else ''}"
                results.append({
                    'key': key_str,
                    'confidence': float(strength),
                    'profile': profile
                })
            except:
                pass

        if not results:
            return {"key": "Am", "confidence": 0.3, "alternatives": []}

        # Aggregate votes
        key_scores: Dict[str, float] = {}
        for r in results:
            key_scores[r['key']] = key_scores.get(r['key'], 0) + r['confidence']

        sorted_keys = sorted(key_scores.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_keys[0]
        total = sum(s for _, s in sorted_keys)

        return {
            "key": primary[0],
            "confidence": round(primary[1] / len(results), 3),
            "alternatives": [
                {"key": k, "confidence": round(s / total, 3)}
                for k, s in sorted_keys[1:4]
            ]
        }

    except Exception as e:
        logger.error("Essentia alternatives detection failed", error=str(e))
        return {"key": "Am", "confidence": 0.3, "alternatives": []}


def _detect_key_with_alternatives_librosa(audio: np.ndarray, sample_rate: int) -> dict:
    """Get key alternatives using librosa."""
    import librosa

    try:
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sample_rate)
        chroma_avg = np.mean(chroma, axis=1)
        chroma_avg = chroma_avg / (np.sum(chroma_avg) + 1e-8)

        results = []
        major_norm = MAJOR_PROFILE / np.sum(MAJOR_PROFILE)
        minor_norm = MINOR_PROFILE / np.sum(MINOR_PROFILE)

        for i, pitch in enumerate(PITCH_CLASSES):
            major_rotated = np.roll(major_norm, i)
            minor_rotated = np.roll(minor_norm, i)

            major_corr = np.corrcoef(chroma_avg, major_rotated)[0, 1]
            minor_corr = np.corrcoef(chroma_avg, minor_rotated)[0, 1]

            results.append({"key": pitch, "correlation": major_corr})
            results.append({"key": f"{pitch}m", "correlation": minor_corr})

        results.sort(key=lambda x: x["correlation"], reverse=True)

        primary = results[0]
        confidence = float(max(0, (primary["correlation"] + 1) / 2))

        return {
            "key": primary["key"],
            "confidence": round(confidence, 3),
            "alternatives": [
                {"key": r["key"], "confidence": round(max(0, (r["correlation"] + 1) / 2), 3)}
                for r in results[1:4]
            ]
        }

    except Exception as e:
        logger.error("Librosa alternatives detection failed", error=str(e))
        return {"key": "Am", "confidence": 0.3, "alternatives": []}


def get_relative_key(key: str) -> str:
    """Get the relative major/minor key."""
    is_minor = key.endswith("m")
    root = key[:-1] if is_minor else key

    try:
        root_idx = PITCH_CLASSES.index(root)
    except ValueError:
        return key

    if is_minor:
        relative_idx = (root_idx + 3) % 12
        return PITCH_CLASSES[relative_idx]
    else:
        relative_idx = (root_idx - 3) % 12
        return f"{PITCH_CLASSES[relative_idx]}m"
