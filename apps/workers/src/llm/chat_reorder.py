"""
Chat-based Track Reordering using Mistral AI

Allows users to request track reordering through natural language,
such as "put the energetic tracks in the middle" or "I want track X at the end".
"""

from mistralai import Mistral
import json
import structlog
from pathlib import Path
from typing import Optional

from src.config import settings

logger = structlog.get_logger()

# Path to system prompt for chat reordering
CHAT_REORDER_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "CHAT_REORDER_PROMPT.md"


def _load_chat_reorder_prompt() -> str:
    """Load the system prompt for chat-based reordering."""
    return CHAT_REORDER_PROMPT_PATH.read_text()


def chat_reorder(
    user_message: str,
    tracks: list[dict],
    current_order: list[str],
    conversation_history: list[dict],
) -> dict:
    """
    Process a user chat message to reorder tracks based on preferences.

    Args:
        user_message: The user's natural language request
        tracks: List of track data with analysis (id, title, artist, bpm, key, energy, etc.)
        current_order: Current order of track IDs
        conversation_history: Previous messages in the conversation

    Returns:
        dict with:
        - response: AI's text response to the user
        - new_order: Suggested new track order (list of track IDs), or None if no change
        - reasoning: Explanation of why this order was chosen
        - changes_made: List of specific changes made
    """
    client = Mistral(api_key=settings.mistral_api_key)

    # Build track info for context
    tracks_info = []
    track_map = {t["id"]: t for t in tracks}

    for i, track_id in enumerate(current_order):
        track = track_map.get(track_id)
        if track:
            tracks_info.append({
                "position": i + 1,
                "id": track["id"],
                "title": track.get("title") or track.get("original_name", "Unknown"),
                "artist": track.get("artist", "Unknown"),
                "bpm": track.get("bpm"),
                "key": track.get("key"),
                "camelot": track.get("camelot"),
                "energy": track.get("energy"),
                "duration_seconds": track.get("duration"),
            })

    # Build the context for the AI
    context = json.dumps({
        "tracks_in_current_order": tracks_info,
        "total_tracks": len(tracks_info),
    }, indent=2)

    # Build messages array
    messages = [
        {"role": "system", "content": _load_chat_reorder_prompt()},
    ]

    # Add conversation history
    for msg in conversation_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add context as a system message before the user message
    messages.append({
        "role": "user",
        "content": f"""Voici l'état actuel du set:

{context}

Ma demande: {user_message}"""
    })

    logger.info(
        "chat_reorder_request",
        user_message=user_message[:100],
        tracks_count=len(tracks_info),
        history_length=len(conversation_history),
    )

    response_text = None
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            max_tokens=2048,
            messages=messages,
            response_format={"type": "json_object"},
        )

        response_text = response.choices[0].message.content

        # Parse the JSON response (should be clean JSON with response_format)
        result = json.loads(response_text)

        logger.info(
            "chat_reorder_response",
            has_new_order=result.get("new_order") is not None,
            changes_count=len(result.get("changes_made", [])),
        )

        return result

    except json.JSONDecodeError as e:
        logger.error(
            "chat_reorder_json_error",
            error=str(e),
            response_text=response_text,
        )
        # Return a conversational fallback
        return {
            "response": "Je n'ai pas pu traiter ta demande correctement. Peux-tu reformuler ta demande de maniere plus precise?",
            "new_order": None,
            "reasoning": None,
            "changes_made": [],
        }

    except Exception as e:
        logger.error("chat_reorder_error", error=str(e), error_type=type(e).__name__)
        return {
            "response": "Une erreur s'est produite. Reessaie dans quelques instants.",
            "new_order": None,
            "reasoning": None,
            "changes_made": [],
        }


def validate_reorder_request(
    user_message: str,
    tracks: list[dict],
) -> dict:
    """
    Quick validation of a reorder request before processing.

    Returns:
        dict with:
        - valid: bool
        - error: error message if invalid
    """
    if not user_message or len(user_message.strip()) < 3:
        return {"valid": False, "error": "Message trop court"}

    if len(tracks) < 2:
        return {"valid": False, "error": "Il faut au moins 2 morceaux pour reordonner"}

    if len(user_message) > 2000:
        return {"valid": False, "error": "Message trop long (max 2000 caracteres)"}

    return {"valid": True, "error": None}
