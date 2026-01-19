"""Audio analysis module"""

from src.analysis.analyzer import analyze_track
from src.analysis.bpm import detect_bpm
from src.analysis.key import detect_key
from src.analysis.energy import calculate_energy
from src.analysis.camelot import key_to_camelot

__all__ = [
    "analyze_track",
    "detect_bpm",
    "detect_key",
    "calculate_energy",
    "key_to_camelot",
]
