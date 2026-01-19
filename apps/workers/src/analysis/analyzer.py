"""
Main audio analyzer orchestrating all analysis tasks
Uses parallel execution for independent analysis steps
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Tuple

import structlog

from src.analysis.bpm import detect_bpm_with_alternatives
from src.analysis.key import detect_key
from src.analysis.energy import calculate_energy
from src.analysis.structure import detect_structure
from src.analysis.camelot import key_to_camelot
from src.analysis.mixability import analyze_mixability
from src.utils.audio import load_audio, get_audio_duration

logger = structlog.get_logger()


def _detect_bpm_task(audio, sample_rate) -> Tuple[str, Dict[str, Any]]:
    """BPM detection task for parallel execution."""
    result = detect_bpm_with_alternatives(audio, sample_rate)
    logger.info("BPM detected", bpm=result["bpm"], confidence=result["confidence"], beats_count=len(result.get("beats", [])))
    return ("bpm", result)


def _detect_key_task(audio, sample_rate) -> Tuple[str, Tuple[str, float]]:
    """Key detection task for parallel execution."""
    result = detect_key(audio, sample_rate)
    camelot = key_to_camelot(result[0])
    logger.info("Key detected", key=result[0], camelot=camelot, confidence=result[1])
    return ("key", (result[0], result[1], camelot))


def _calculate_energy_task(audio, sample_rate) -> Tuple[str, Tuple[float, float, float]]:
    """Energy calculation task for parallel execution."""
    result = calculate_energy(audio, sample_rate)
    logger.info("Energy calculated", energy=result[0], danceability=result[1])
    return ("energy", result)


def analyze_track(file_path: str) -> Dict[str, Any]:
    """
    Perform comprehensive audio analysis on a track.
    Uses parallel execution for BPM, Key, and Energy detection.

    Args:
        file_path: Path to the audio file

    Returns:
        Dictionary containing all analysis results
    """
    logger.info("Starting track analysis", file_path=file_path)

    # Load audio file (sequential - required by all tasks)
    audio, sample_rate = load_audio(file_path)
    duration = get_audio_duration(audio, sample_rate)
    logger.info("Audio loaded", duration=duration, sample_rate=sample_rate)

    # Run BPM, Key, and Energy detection in parallel
    # These are independent and can run concurrently
    # Using threads because the heavy computation is in C libraries (releases GIL)
    results = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_detect_bpm_task, audio, sample_rate): "bpm",
            executor.submit(_detect_key_task, audio, sample_rate): "key",
            executor.submit(_calculate_energy_task, audio, sample_rate): "energy",
        }

        for future in as_completed(futures):
            task_name = futures[future]
            try:
                name, result = future.result()
                results[name] = result
            except Exception as e:
                logger.error(f"Task {task_name} failed", error=str(e))
                raise

    # Extract results
    bpm_result = results["bpm"]
    bpm = bpm_result["bpm"]
    bpm_confidence = bpm_result["confidence"]
    beats = bpm_result.get("beats", [])
    key, key_confidence, camelot = results["key"]
    energy, danceability, loudness = results["energy"]

    # Detect song structure (depends on BPM, so runs after parallel tasks)
    structure = detect_structure(audio, sample_rate, bpm)
    logger.info("Structure detected", sections=len(structure.get("sections", [])))

    # Mixability analysis (uses lightweight vocal detection)
    intro_end = structure.get("intro", {}).get("end") or min(16, duration * 0.1)
    outro_start = structure.get("outro", {}).get("start") or max(0, duration - 16)

    mixability = analyze_mixability(
        audio, sample_rate, intro_end, outro_start, duration, beats
    )

    # Compile results
    result = {
        "duration": round(duration, 2),  # Track duration in seconds
        "bpm": round(bpm, 2),
        "bpmConfidence": round(bpm_confidence, 3),
        "key": key,
        "keyConfidence": round(key_confidence, 3),
        "camelot": camelot,
        "energy": round(energy, 3),
        "danceability": round(danceability, 3),
        "loudness": round(loudness, 2),
        "beats": beats,  # Beat timestamps in seconds for beat-matching
        "introStart": structure.get("intro", {}).get("start"),
        "introEnd": structure.get("intro", {}).get("end"),
        "outroStart": structure.get("outro", {}).get("start"),
        "outroEnd": structure.get("outro", {}).get("end") or duration,
        "structureJson": structure,
        # Mixability
        "introInstrumentalMs": mixability["introInstrumentalMs"],
        "outroInstrumentalMs": mixability["outroInstrumentalMs"],
        "vocalPercentage": mixability["vocalPercentage"],
        "vocalIntensity": mixability["vocalIntensity"],
        "maxBlendInDurationMs": mixability["maxBlendInDurationMs"],
        "maxBlendOutDurationMs": mixability["maxBlendOutDurationMs"],
        "bestMixInPointMs": mixability["bestMixInPointMs"],
        "bestMixOutPointMs": mixability["bestMixOutPointMs"],
        "mixFriendly": mixability["mixFriendly"],
        "mixabilityWarnings": mixability["mixabilityWarnings"],
    }

    logger.info("Analysis complete", result=result)
    return result
