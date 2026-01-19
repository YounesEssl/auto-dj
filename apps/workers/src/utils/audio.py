"""
Audio file utilities for loading, saving, and manipulating audio
"""

from typing import List, Tuple
from pathlib import Path
import subprocess

import numpy as np
import librosa
import soundfile as sf
import structlog

logger = structlog.get_logger()


def ensure_wav_format(audio_path: str) -> str:
    """
    Convert audio file to WAV format if necessary.

    This avoids warnings from librosa/pysoundfile when loading M4A/AAC files.
    Uses ffmpeg for conversion.

    Args:
        audio_path: Path to the audio file

    Returns:
        Path to the WAV file (original path if already WAV, or converted path)
    """
    path = Path(audio_path)

    # If already WAV, return as-is
    if path.suffix.lower() == '.wav':
        return audio_path

    # Check if a WAV version already exists
    wav_path = path.with_suffix('.wav')
    if wav_path.exists():
        logger.debug("Using existing WAV file", wav_path=str(wav_path))
        return str(wav_path)

    logger.info("Converting M4A to WAV", source=path.name)

    # Convert with ffmpeg
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-i', audio_path,
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '44100',           # 44.1kHz
                '-ac', '2',               # Stereo
                '-y',                     # Overwrite if exists
                '-loglevel', 'error',     # Only show errors
                str(wav_path)
            ],
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(
            "Converted to WAV",
            original=path.name,
            wav_path=str(wav_path)
        )
        return str(wav_path)

    except subprocess.CalledProcessError as e:
        logger.warning(
            "FFmpeg conversion failed, using original file",
            error=e.stderr,
            file=audio_path
        )
        return audio_path
    except FileNotFoundError:
        logger.warning(
            "FFmpeg not found, using original file",
            file=audio_path
        )
        return audio_path


def load_audio(
    file_path: str,
    target_sr: int = 22050,
    mono: bool = True
) -> Tuple[np.ndarray, int]:
    """
    Load an audio file and return as numpy array.

    Args:
        file_path: Path to the audio file
        target_sr: Target sample rate (default 22050 for analysis)
        mono: Convert to mono if True

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    logger.info("Loading audio", file_path=file_path, target_sr=target_sr)

    # Convert to WAV if needed (avoids librosa/pysoundfile warnings for M4A/AAC)
    wav_path = ensure_wav_format(file_path)

    try:
        # Use librosa for loading
        audio, sr = librosa.load(wav_path, sr=target_sr, mono=mono)

        logger.info(
            "Audio loaded successfully",
            duration=len(audio) / sr,
            sample_rate=sr,
            samples=len(audio)
        )

        return audio, sr

    except Exception as e:
        logger.error("Failed to load audio", file_path=file_path, error=str(e))
        raise


def save_audio(
    audio: np.ndarray,
    file_path: str,
    sample_rate: int = 44100,
    format: str = "wav"
) -> str:
    """
    Save audio data to a file.

    Args:
        audio: Audio data as numpy array
        file_path: Output file path
        sample_rate: Sample rate of the audio
        format: Output format (wav, flac)

    Returns:
        Path to saved file
    """
    logger.info("Saving audio", file_path=file_path, format=format)

    try:
        sf.write(file_path, audio, sample_rate)
        logger.info("Audio saved", file_path=file_path)
        return file_path
    except Exception as e:
        logger.error("Failed to save audio", file_path=file_path, error=str(e))
        raise


def get_audio_duration(audio: np.ndarray, sample_rate: int) -> float:
    """
    Get duration of audio in seconds.

    Args:
        audio: Audio data
        sample_rate: Sample rate

    Returns:
        Duration in seconds
    """
    return len(audio) / sample_rate


def concatenate_audio(segments: List[np.ndarray]) -> np.ndarray:
    """
    Concatenate multiple audio segments.

    Args:
        segments: List of audio arrays

    Returns:
        Concatenated audio
    """
    return np.concatenate(segments)


def normalize_audio(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """
    Normalize audio to a target peak level.

    Args:
        audio: Input audio
        target_db: Target peak level in dB

    Returns:
        Normalized audio
    """
    peak = np.max(np.abs(audio))
    if peak > 0:
        target_peak = 10 ** (target_db / 20)
        audio = audio * (target_peak / peak)
    return audio


def apply_fade(
    audio: np.ndarray,
    fade_in_samples: int = 0,
    fade_out_samples: int = 0
) -> np.ndarray:
    """
    Apply fade in/out to audio.

    Args:
        audio: Input audio
        fade_in_samples: Number of samples for fade in
        fade_out_samples: Number of samples for fade out

    Returns:
        Audio with fades applied
    """
    audio = audio.copy()

    if fade_in_samples > 0:
        fade_in = np.linspace(0, 1, fade_in_samples)
        audio[:fade_in_samples] *= fade_in

    if fade_out_samples > 0:
        fade_out = np.linspace(1, 0, fade_out_samples)
        audio[-fade_out_samples:] *= fade_out

    return audio


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to a different sample rate.

    Args:
        audio: Input audio
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio
    """
    if orig_sr == target_sr:
        return audio
    return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
