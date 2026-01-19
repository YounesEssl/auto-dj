"""
Mixability Analysis - Calcule les capacités de mix d'un track.
Utilise detect_vocals() en mode heuristique (sans Demucs) pour la rapidité.
"""

import numpy as np
from typing import Any, Dict, List, Optional
import structlog

from src.analysis.vocal_detector import detect_vocals, get_vocal_free_regions

logger = structlog.get_logger()

# Seuils
SHORT_DURATION_MS = 8000   # < 8s = court
IDEAL_DURATION_MS = 15000  # > 15s = idéal


def analyze_mixability(
    audio: np.ndarray,
    sample_rate: int,
    intro_end: float,
    outro_start: float,
    duration: float,
    beats: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Analyse la mixabilité d'un track."""

    logger.info("Analyzing mixability", duration=duration)

    # Détection vocale (mode heuristique, sans Demucs)
    vocals = detect_vocals(audio, sample_rate, vocal_stem=None)
    vocal_free = get_vocal_free_regions(vocals, min_duration=2.0, track_duration=duration)

    # Calcul intro/outro instrumental
    intro_instrumental_ms = _calc_intro_instrumental(vocals, intro_end)
    outro_instrumental_ms = _calc_outro_instrumental(vocals, outro_start, duration)

    # Classification vocale
    vocal_pct = vocals.get("vocal_percentage", 0)
    vocal_intensity = _classify_intensity(vocal_pct)

    # Capacités de blend
    max_blend_in = intro_instrumental_ms
    max_blend_out = outro_instrumental_ms

    # Points de mix recommandés
    best_mix_in = int(intro_end * 1000)
    best_mix_out = int(outro_start * 1000)

    # Assessment
    mix_friendly, warnings = _assess(
        intro_instrumental_ms, outro_instrumental_ms, vocal_pct
    )

    result = {
        "introInstrumentalMs": intro_instrumental_ms,
        "outroInstrumentalMs": outro_instrumental_ms,
        "vocalPercentage": round(vocal_pct, 1),
        "vocalIntensity": vocal_intensity,
        "maxBlendInDurationMs": max_blend_in,
        "maxBlendOutDurationMs": max_blend_out,
        "bestMixInPointMs": best_mix_in,
        "bestMixOutPointMs": best_mix_out,
        "mixFriendly": mix_friendly,
        "mixabilityWarnings": warnings,
    }

    logger.info("Mixability analysis complete", **result)
    return result


def _calc_intro_instrumental(vocals: Dict, intro_end: float) -> int:
    """Durée de l'intro sans vocaux (ms)."""
    if not vocals.get("has_vocals"):
        return int(intro_end * 1000)

    sections = vocals.get("vocal_sections", [])
    if not sections:
        return int(intro_end * 1000)

    first_vocal = sections[0]["start"]
    return int(min(first_vocal, intro_end) * 1000)


def _calc_outro_instrumental(vocals: Dict, outro_start: float, duration: float) -> int:
    """Durée de l'outro sans vocaux (ms)."""
    if not vocals.get("has_vocals"):
        return int((duration - outro_start) * 1000)

    sections = vocals.get("vocal_sections", [])
    if not sections:
        return int((duration - outro_start) * 1000)

    last_vocal = sections[-1]["end"]
    outro_start_actual = max(last_vocal, outro_start)
    return int(max(0, duration - outro_start_actual) * 1000)


def _classify_intensity(vocal_pct: float) -> str:
    """Classifie l'intensité vocale."""
    if vocal_pct < 10:
        return "NONE"
    elif vocal_pct < 30:
        return "LOW"
    elif vocal_pct < 60:
        return "MEDIUM"
    else:
        return "HIGH"


def _assess(intro_ms: int, outro_ms: int, vocal_pct: float) -> tuple[bool, List[str]]:
    """Évalue la mixabilité et génère les warnings."""
    warnings = []
    mix_friendly = True

    if intro_ms < 4000:
        warnings.append(f"Very short intro ({intro_ms/1000:.1f}s)")
        mix_friendly = False
    elif intro_ms < SHORT_DURATION_MS:
        warnings.append(f"Short intro ({intro_ms/1000:.1f}s)")

    if outro_ms < 4000:
        warnings.append(f"Very short outro ({outro_ms/1000:.1f}s)")
        mix_friendly = False
    elif outro_ms < SHORT_DURATION_MS:
        warnings.append(f"Short outro ({outro_ms/1000:.1f}s)")

    if vocal_pct > 80:
        warnings.append(f"High vocal content ({vocal_pct:.0f}%)")
        mix_friendly = False
    elif vocal_pct > 60:
        warnings.append(f"Moderate vocal content ({vocal_pct:.0f}%)")

    return mix_friendly, warnings
