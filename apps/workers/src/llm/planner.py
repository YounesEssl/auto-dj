"""
LLM-based Transition Planner

Uses Claude to intelligently plan transitions between tracks based on
audio analysis data, harmonic compatibility, and set context.
"""

import anthropic
import json
import structlog
from pathlib import Path
from typing import Optional

from src.config import settings

logger = structlog.get_logger()

# Path to system prompt
PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "AUTODJ_BRAIN_PROMPT.md"


def _load_system_prompt() -> str:
    """Load the system prompt from file."""
    return PROMPT_PATH.read_text()


def plan_transition(
    track_a: dict,
    track_b: dict,
    compatibility: dict,
    context: dict
) -> dict:
    """
    Call Claude to plan the optimal transition between two tracks.

    Args:
        track_a: Analysis of outgoing track (bpm, key, energy, outro_start, etc.)
        track_b: Analysis of incoming track
        compatibility: Compatibility scores (harmonic, bpm, energy, overall)
        context: Set context (position_in_set, track_index, total_tracks)

    Returns:
        Detailed transition plan as JSON dict
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_input = json.dumps({
        "context": context,
        "track_a": track_a,
        "track_b": track_b,
        "compatibility": compatibility
    }, indent=2)

    logger.info(
        "planning_transition",
        track_a_key=track_a.get("key"),
        track_b_key=track_b.get("key"),
        track_a_bpm=track_a.get("bpm"),
        track_b_bpm=track_b.get("bpm"),
        compatibility_overall=compatibility.get("overall"),
        position=context.get("position_in_set")
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=_load_system_prompt(),
            messages=[{"role": "user", "content": user_input}]
        )

        # Parse the JSON response
        response_text = response.content[0].text

        # Strip markdown code blocks if present (```json ... ```)
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            # Remove opening ```json or ```
            first_newline = cleaned_text.find("\n")
            if first_newline != -1:
                cleaned_text = cleaned_text[first_newline + 1:]
            # Remove closing ```
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3].strip()

        plan = json.loads(cleaned_text)

        logger.info(
            "transition_planned",
            type=plan.get("transition", {}).get("type"),
            confidence=plan.get("confidence"),
            duration_bars=plan.get("transition", {}).get("duration_bars"),
            warnings_count=len(plan.get("warnings", []))
        )

        return plan

    except json.JSONDecodeError as e:
        logger.error(
            "llm_response_not_json",
            error=str(e),
            response_preview=response_text[:200] if 'response_text' in dir() else None
        )
        return _fallback_plan(track_a, track_b, compatibility)
    except anthropic.APIError as e:
        logger.error("anthropic_api_error", error=str(e))
        return _fallback_plan(track_a, track_b, compatibility)
    except Exception as e:
        logger.error("llm_call_failed", error=str(e), error_type=type(e).__name__)
        return _fallback_plan(track_a, track_b, compatibility)


def _fallback_plan(track_a: dict, track_b: dict, compatibility: dict) -> dict:
    """
    Fallback plan if the LLM call fails.

    Uses simple rules based on compatibility scores to generate
    a basic but safe transition plan.
    """
    harmonic = compatibility.get("harmonic", 50)
    bpm_score = compatibility.get("bpm", 50)

    # Calculate BPM delta percentage
    bpm_a = track_a.get("bpm", 120)
    bpm_b = track_b.get("bpm", 120)
    bpm_delta_pct = abs(bpm_a - bpm_b) / bpm_a * 100 if bpm_a > 0 else 0

    # Determine transition type based on compatibility
    if harmonic < 60 or bpm_delta_pct > 6:
        transition_type = "HARD_CUT"
        duration_bars = 0
        duration_seconds = 0
    elif harmonic >= 85 and bpm_delta_pct <= 2:
        transition_type = "STEM_BLEND"
        duration_bars = 16
        duration_seconds = duration_bars * 4 * (60 / bpm_a)  # bars * beats_per_bar * seconds_per_beat
    elif harmonic >= 70 and bpm_delta_pct <= 4:
        transition_type = "STEM_BLEND"
        duration_bars = 8
        duration_seconds = duration_bars * 4 * (60 / bpm_a)
    else:
        transition_type = "CROSSFADE"
        duration_bars = 8
        duration_seconds = duration_bars * 4 * (60 / bpm_a)

    # Get outro_start as transition start point
    outro_start = track_a.get("outro_start", track_a.get("duration_seconds", 300) * 0.8)
    duration_a = track_a.get("duration_seconds", 300)

    # Build fallback stems phases for STEM_BLEND
    stems = None
    volume = None
    if transition_type == "STEM_BLEND":
        if duration_bars == 16:
            stems = {
                "strategy": "PROGRESSIVE_SWAP",
                "phases": [
                    {"phase": 1, "bars": [1, 4], "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}, "b": {"drums": 0.3, "bass": 0.0, "other": 0.0, "vocals": 0.0}},
                    {"phase": 2, "bars": [5, 8], "a": {"drums": 1.0, "bass": 1.0, "other": 0.6, "vocals": 0.5}, "b": {"drums": 0.5, "bass": 0.0, "other": 0.4, "vocals": 0.0}},
                    {"phase": 3, "bars": [9, 12], "a": {"drums": 0.5, "bass": 0.0, "other": 0.3, "vocals": 0.2}, "b": {"drums": 0.8, "bass": 1.0, "other": 0.7, "vocals": 0.5}},
                    {"phase": 4, "bars": [13, 16], "a": {"drums": 0.2, "bass": 0.0, "other": 0.0, "vocals": 0.0}, "b": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}}
                ],
                "bass_swap_bar": 9
            }
            volume = {
                "track_a": [{"bar": 1, "level": 1.0}, {"bar": 8, "level": 0.85}, {"bar": 12, "level": 0.4}, {"bar": 16, "level": 0.0}],
                "track_b": [{"bar": 1, "level": 0.25}, {"bar": 8, "level": 0.5}, {"bar": 12, "level": 0.85}, {"bar": 16, "level": 1.0}]
            }
        else:  # 8 bars
            stems = {
                "strategy": "PROGRESSIVE_SWAP",
                "phases": [
                    {"phase": 1, "bars": [1, 2], "a": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}, "b": {"drums": 0.3, "bass": 0.0, "other": 0.0, "vocals": 0.0}},
                    {"phase": 2, "bars": [3, 4], "a": {"drums": 1.0, "bass": 1.0, "other": 0.6, "vocals": 0.6}, "b": {"drums": 0.5, "bass": 0.0, "other": 0.4, "vocals": 0.0}},
                    {"phase": 3, "bars": [5, 6], "a": {"drums": 0.6, "bass": 0.0, "other": 0.3, "vocals": 0.3}, "b": {"drums": 0.8, "bass": 1.0, "other": 0.7, "vocals": 0.5}},
                    {"phase": 4, "bars": [7, 8], "a": {"drums": 0.2, "bass": 0.0, "other": 0.0, "vocals": 0.0}, "b": {"drums": 1.0, "bass": 1.0, "other": 1.0, "vocals": 1.0}}
                ],
                "bass_swap_bar": 5
            }
            volume = {
                "track_a": [{"bar": 1, "level": 1.0}, {"bar": 4, "level": 0.8}, {"bar": 6, "level": 0.4}, {"bar": 8, "level": 0.0}],
                "track_b": [{"bar": 1, "level": 0.3}, {"bar": 4, "level": 0.6}, {"bar": 6, "level": 0.9}, {"bar": 8, "level": 1.0}]
            }

    # Build effects based on transition type
    # Use track_a/track_b keys to match LLM prompt structure
    effects = {
        "track_a": {"type": "none", "params": {}},
        "track_b": {"type": "none", "params": {}}
    }
    if transition_type == "HARD_CUT":
        # Always apply reverb for HARD_CUT to soften the transition
        effects["track_a"] = {
            "type": "reverb",
            "params": {"room_size": 0.8, "decay": 2.0, "mix": 0.6}
        }

    logger.warning(
        "using_fallback_plan",
        transition_type=transition_type,
        harmonic=harmonic,
        bpm_delta_pct=bpm_delta_pct
    )

    return {
        "summary": "Fallback plan - LLM unavailable",
        "confidence": 0.5,
        "track_a": {
            "play_from_seconds": 0,
            "play_until_seconds": min(outro_start + duration_seconds, duration_a),
            "cut_reason": "Fallback: outro + transition duration"
        },
        "track_b": {
            "start_from_seconds": 0,
            "entry_reason": "Fallback: start from beginning"
        },
        "transition": {
            "type": transition_type,
            "start_time_in_a": outro_start,
            "duration_seconds": duration_seconds,
            "duration_bars": duration_bars,
            "stems": stems,
            "volume": volume,
        },
        # Effects at top level to match LLM prompt structure
        "effects": effects,
        "warnings": [{"type": "FALLBACK_USED", "message": "LLM call failed, using basic fallback"}]
    }


def determine_set_position(track_index: int, total_tracks: int) -> str:
    """
    Determine the position in the DJ set based on track index.

    Args:
        track_index: Current track index (0-based)
        total_tracks: Total number of tracks in the set

    Returns:
        Position string: WARMUP, BUILD, PEAK, or COOLDOWN
    """
    if total_tracks <= 1:
        return "BUILD"

    position_ratio = track_index / (total_tracks - 1)

    if position_ratio < 0.2:
        return "WARMUP"
    elif position_ratio < 0.5:
        return "BUILD"
    elif position_ratio < 0.8:
        return "PEAK"
    else:
        return "COOLDOWN"
