"""
Professional Stem Separation Module using Demucs v4
Separates audio into: drums, bass, vocals, other
Used for advanced mixing and mashup creation
"""

from typing import Dict, Optional, Tuple
from pathlib import Path
import numpy as np
import structlog
import tempfile
import os

logger = structlog.get_logger()

# Try to import demucs
try:
    import torch
    import torchaudio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    DEMUCS_AVAILABLE = True
    logger.info("Demucs v4 loaded for stem separation")
except ImportError as e:
    DEMUCS_AVAILABLE = False
    logger.warning("Demucs not available for stem separation", error=str(e))


# Demucs model cache
_demucs_model = None


def get_demucs_model():
    """
    Get cached Demucs model (loads on first call).
    Uses htdemucs (hybrid transformer) for best quality.
    """
    global _demucs_model
    if _demucs_model is None and DEMUCS_AVAILABLE:
        try:
            # htdemucs is the best quality model
            # htdemucs_ft is fine-tuned version (slightly better but slower)
            _demucs_model = get_model('htdemucs')
            _demucs_model.eval()

            # Select best available device: CUDA > MPS (Apple Silicon) > CPU
            if torch.cuda.is_available():
                _demucs_model = _demucs_model.cuda()
                logger.info("Demucs model loaded on CUDA")
            elif torch.backends.mps.is_available():
                _demucs_model = _demucs_model.to('mps')
                logger.info("Demucs model loaded on MPS (Apple Silicon)")
            else:
                logger.info("Demucs model loaded on CPU")
        except Exception as e:
            logger.error("Failed to load Demucs model", error=str(e))
            return None
    return _demucs_model


def separate_stems(
    audio: np.ndarray,
    sample_rate: int,
    output_dir: Optional[str] = None
) -> Dict[str, np.ndarray]:
    """
    Separate audio into stems using Demucs v4.

    Args:
        audio: Audio signal as numpy array (can be mono or stereo)
        sample_rate: Sample rate of the audio
        output_dir: Optional directory to save stems as files

    Returns:
        Dictionary with stems: {
            'drums': np.ndarray,
            'bass': np.ndarray,
            'vocals': np.ndarray,
            'other': np.ndarray  # guitars, synths, etc.
        }
    """
    if not DEMUCS_AVAILABLE:
        logger.error("Demucs not available - cannot separate stems")
        return {}

    try:
        model = get_demucs_model()
        if model is None:
            return {}

        # Convert to torch tensor
        # Demucs expects (batch, channels, samples)
        if audio.ndim == 1:
            # Mono -> stereo
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0).repeat(2, 1)
        else:
            # Already stereo (samples, channels) -> (channels, samples)
            audio_tensor = torch.from_numpy(audio.T).float()

        # Add batch dimension
        audio_tensor = audio_tensor.unsqueeze(0)

        # Resample to model's expected rate (44100)
        if sample_rate != model.samplerate:
            audio_tensor = torchaudio.functional.resample(
                audio_tensor,
                sample_rate,
                model.samplerate
            )

        # Move to same device as model
        device = next(model.parameters()).device
        audio_tensor = audio_tensor.to(device)

        # Apply model
        with torch.no_grad():
            sources = apply_model(model, audio_tensor, device=device)

        # sources shape: (batch, sources, channels, samples)
        # Model outputs: drums, bass, other, vocals (in that order for htdemucs)
        source_names = model.sources

        stems = {}
        for i, name in enumerate(source_names):
            stem_audio = sources[0, i].cpu().numpy()

            # Resample back if needed
            if sample_rate != model.samplerate:
                stem_tensor = torch.from_numpy(stem_audio)
                stem_tensor = torchaudio.functional.resample(
                    stem_tensor,
                    model.samplerate,
                    sample_rate
                )
                stem_audio = stem_tensor.numpy()

            # Convert to mono if original was mono
            if audio.ndim == 1:
                stem_audio = np.mean(stem_audio, axis=0)
            else:
                # (channels, samples) -> (samples, channels)
                stem_audio = stem_audio.T

            stems[name] = stem_audio

        # Save stems if output directory provided
        if output_dir:
            _save_stems(stems, sample_rate, output_dir)

        logger.info(
            "Stem separation complete",
            stems=list(stems.keys()),
            sample_rate=sample_rate
        )

        return stems

    except Exception as e:
        logger.error("Stem separation failed", error=str(e))
        return {}


def _save_stems(
    stems: Dict[str, np.ndarray],
    sample_rate: int,
    output_dir: str
) -> Dict[str, str]:
    """
    Save stems to audio files.
    """
    import soundfile as sf

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = {}
    for name, audio in stems.items():
        file_path = output_path / f"{name}.wav"
        sf.write(str(file_path), audio, sample_rate)
        saved_files[name] = str(file_path)
        logger.debug(f"Saved stem: {name}", path=str(file_path))

    return saved_files


def separate_stems_to_files(
    input_path: str,
    output_dir: str,
    model_name: str = 'htdemucs'
) -> Dict[str, str]:
    """
    Separate stems from an audio file and save to directory.

    Args:
        input_path: Path to input audio file
        output_dir: Directory to save stems
        model_name: Demucs model to use ('htdemucs' recommended)

    Returns:
        Dictionary mapping stem names to file paths
    """
    if not DEMUCS_AVAILABLE:
        logger.error("Demucs not available")
        return {}

    try:
        import soundfile as sf

        # Load audio
        audio, sample_rate = sf.read(input_path)

        # Separate
        stems = separate_stems(audio, sample_rate)

        if not stems:
            return {}

        # Save
        return _save_stems(stems, sample_rate, output_dir)

    except Exception as e:
        logger.error("Stem separation from file failed", error=str(e), path=input_path)
        return {}


def get_instrumental(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Get instrumental version (remove vocals).
    """
    stems = separate_stems(audio, sample_rate)
    if not stems:
        return audio

    # Combine everything except vocals
    instrumental_stems = ['drums', 'bass', 'other']
    instrumental = None

    for stem_name in instrumental_stems:
        if stem_name in stems:
            if instrumental is None:
                instrumental = stems[stem_name].copy()
            else:
                instrumental += stems[stem_name]

    return instrumental if instrumental is not None else audio


def get_acapella(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Get acapella version (vocals only).
    """
    stems = separate_stems(audio, sample_rate)
    return stems.get('vocals', audio)


def get_drums(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Get drums only.
    """
    stems = separate_stems(audio, sample_rate)
    return stems.get('drums', audio)


def get_bass(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Get bass only.
    """
    stems = separate_stems(audio, sample_rate)
    return stems.get('bass', audio)


def is_available() -> bool:
    """
    Check if stem separation is available.
    """
    return DEMUCS_AVAILABLE


def get_model_info() -> Dict:
    """
    Get information about the loaded model.
    """
    if not DEMUCS_AVAILABLE:
        return {"available": False}

    model = get_demucs_model()
    if model is None:
        return {"available": False, "error": "Model failed to load"}

    return {
        "available": True,
        "model": "htdemucs",
        "sources": model.sources,
        "sample_rate": model.samplerate,
        "device": str(next(model.parameters()).device)
    }
