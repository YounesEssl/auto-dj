"""
Stem separation module using Demucs v4

Separates audio into:
- Drums
- Bass
- Vocals
- Other (melody, synths, etc.)
"""

from typing import Dict, Optional, Tuple
from pathlib import Path
import tempfile
import os

import numpy as np
import soundfile as sf
import structlog

from src.config import settings

logger = structlog.get_logger()

# Lazy import for Demucs
_demucs_available = None
_separator = None


def _check_demucs() -> bool:
    """Check if Demucs is available."""
    global _demucs_available
    if _demucs_available is None:
        try:
            import torch
            from demucs import pretrained
            _demucs_available = True
            logger.info("Demucs available for stem separation")
        except ImportError:
            _demucs_available = False
            logger.warning("Demucs not available - stem separation will be simulated")
    return _demucs_available


class StemSeparator:
    """
    Wrapper for Demucs stem separation.
    Uses htdemucs_ft model for best quality on music.
    """

    STEM_NAMES = ['drums', 'bass', 'other', 'vocals']

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the stem separator.

        Args:
            model_name: Demucs model to use (default: htdemucs_ft)
        """
        self.model_name = model_name or settings.demucs_model
        self.model = None
        self.device = None

    def load_model(self):
        """Load the Demucs model."""
        if not _check_demucs():
            logger.warning("Demucs not available, using passthrough mode")
            return

        import torch
        from demucs import pretrained

        logger.info("Loading Demucs model", model=self.model_name)

        self.model = pretrained.get_model(self.model_name)

        # Select best available device: CUDA > MPS (Apple Silicon) > CPU
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
            self.model = self.model.cuda()
            logger.info("Using CUDA for Demucs")
        elif torch.backends.mps.is_available():
            self.device = torch.device('mps')
            self.model = self.model.to(self.device)
            logger.info("Using MPS (Apple Silicon) for Demucs")
        else:
            self.device = torch.device('cpu')
            logger.info("Using CPU for Demucs")

        self.model.eval()
        logger.info("Demucs model loaded successfully")

    def separate(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> Dict[str, np.ndarray]:
        """
        Separate audio into stems.

        Args:
            audio: Input audio as numpy array (mono or stereo)
            sample_rate: Sample rate of the audio

        Returns:
            Dictionary mapping stem names to audio arrays
        """
        if not _check_demucs():
            # Return original audio as all stems (passthrough)
            logger.warning("Using passthrough mode - no actual separation")
            return {name: audio.copy() for name in self.STEM_NAMES}

        if self.model is None:
            self.load_model()

        import torch
        from demucs.apply import apply_model

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Convert mono to stereo if needed
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=0)
        elif audio.ndim == 2 and audio.shape[0] > audio.shape[1]:
            # Shape is (samples, channels), transpose to (channels, samples)
            audio = audio.T

        # Ensure stereo
        if audio.shape[0] == 1:
            audio = np.concatenate([audio, audio], axis=0)

        # Resample to model's sample rate if needed (Demucs expects 44100)
        if sample_rate != 44100:
            import librosa
            audio = np.stack([
                librosa.resample(audio[0], orig_sr=sample_rate, target_sr=44100),
                librosa.resample(audio[1], orig_sr=sample_rate, target_sr=44100),
            ])
            sample_rate = 44100

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio).float()
        audio_tensor = audio_tensor.unsqueeze(0)  # Add batch dim: (1, 2, samples)

        # Move tensor to same device as model
        if self.device.type != 'cpu':
            audio_tensor = audio_tensor.to(self.device)

        logger.info("Separating stems", audio_shape=audio_tensor.shape)

        # Apply model
        with torch.no_grad():
            sources = apply_model(
                self.model,
                audio_tensor,
                device=self.device,
                progress=False,
                num_workers=0,
            )

        # Extract stems: sources shape is (1, num_sources, 2, samples)
        stems = {}
        for i, name in enumerate(self.STEM_NAMES):
            stem_audio = sources[0, i].cpu().numpy()  # (2, samples)
            # Convert to mono by averaging channels
            stem_mono = np.mean(stem_audio, axis=0)
            stems[name] = stem_mono

        logger.info("Stem separation complete", stems=list(stems.keys()))
        return stems

    def separate_segment(
        self,
        audio: np.ndarray,
        sample_rate: int,
        start_time: float,
        end_time: float
    ) -> Dict[str, np.ndarray]:
        """
        Separate a specific segment of audio.

        Args:
            audio: Full audio array
            sample_rate: Sample rate
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Dictionary of stem arrays for the segment
        """
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)

        # Clamp to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(audio), end_sample)

        segment = audio[start_sample:end_sample]
        return self.separate(segment, sample_rate)


# Global separator instance (lazy loaded)
_global_separator: Optional[StemSeparator] = None


def get_separator() -> StemSeparator:
    """Get or create the global stem separator instance."""
    global _global_separator
    if _global_separator is None:
        _global_separator = StemSeparator()
    return _global_separator


def separate_stems(
    audio: np.ndarray,
    sample_rate: int
) -> Dict[str, np.ndarray]:
    """
    Convenience function to separate audio into stems.

    Args:
        audio: Input audio
        sample_rate: Sample rate

    Returns:
        Dictionary of stems: {'drums', 'bass', 'other', 'vocals'}
    """
    separator = get_separator()
    return separator.separate(audio, sample_rate)


def separate_stems_segment(
    audio: np.ndarray,
    sample_rate: int,
    start_time: float,
    end_time: float
) -> Dict[str, np.ndarray]:
    """
    Separate a specific segment of audio into stems.

    Args:
        audio: Full audio array
        sample_rate: Sample rate
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        Dictionary of stem arrays for the segment
    """
    separator = get_separator()
    return separator.separate_segment(audio, sample_rate, start_time, end_time)
