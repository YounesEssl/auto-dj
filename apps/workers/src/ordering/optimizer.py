"""
Track ordering optimizer

Uses a combination of:
- Camelot wheel compatibility for harmonic mixing
- Energy progression for set flow
- BPM compatibility for smooth transitions
"""

from typing import Any, Dict, List

import structlog

from src.ordering.scoring import score_transition

logger = structlog.get_logger()


def optimize_track_order(
    tracks: List[Dict[str, Any]]
) -> List[str]:
    """
    Optimize the order of tracks for the best mixing flow.

    Uses a greedy nearest-neighbor algorithm with harmonic compatibility scoring.

    Args:
        tracks: List of track dictionaries with analysis data

    Returns:
        List of track IDs in optimal order
    """
    if len(tracks) <= 1:
        return [t["id"] for t in tracks]

    logger.info("Starting track order optimization", track_count=len(tracks))

    # Build adjacency matrix of transition scores
    n = len(tracks)
    scores = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                scores[i][j] = score_transition(tracks[i], tracks[j])

    # Greedy nearest neighbor algorithm
    # Start with the track that has the best average outgoing score
    avg_scores = [
        sum(scores[i]) / (n - 1) if n > 1 else 0
        for i in range(n)
    ]
    current = avg_scores.index(max(avg_scores))

    ordered = [current]
    remaining = set(range(n)) - {current}

    while remaining:
        # Find the best next track
        best_score = -1
        best_next = -1

        for candidate in remaining:
            if scores[current][candidate] > best_score:
                best_score = scores[current][candidate]
                best_next = candidate

        ordered.append(best_next)
        remaining.remove(best_next)
        current = best_next

    # Convert indices to track IDs
    ordered_ids = [tracks[i]["id"] for i in ordered]

    logger.info("Track order optimized", order=ordered_ids)
    return ordered_ids
