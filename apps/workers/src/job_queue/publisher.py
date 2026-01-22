"""
Publisher for sending job results back to the API using BullMQ
"""

from typing import Any, Dict, Optional

import structlog
from bullmq import Queue

from src.config import settings

logger = structlog.get_logger()

# Global queue instance
_results_queue: Optional[Queue] = None


def _get_results_queue() -> Queue:
    """Get or create the results queue."""
    global _results_queue
    if _results_queue is None:
        redis_opts = {
            "host": settings.redis_host,
            "port": settings.redis_port,
        }
        if settings.redis_password:
            redis_opts["password"] = settings.redis_password

        _results_queue = Queue(settings.queue_results, {"connection": redis_opts})
    return _results_queue


async def publish_result(
    result_type: str,
    project_id: Optional[str] = None,
    track_id: Optional[str] = None,
    transition_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
):
    """
    Publish a job result to the results queue for the API to consume.

    Args:
        result_type: Type of result ('analyze', 'transition_audio', 'mix', or 'draft_transition')
        project_id: Project identifier
        track_id: Track identifier (for analyze results)
        transition_id: Transition identifier (for transition_audio results)
        draft_id: Draft identifier (for draft_transition results)
        result: Result data
        error: Error message if job failed
    """
    queue = _get_results_queue()

    payload: Dict[str, Any] = {
        "type": result_type,
    }

    if project_id:
        payload["projectId"] = project_id

    if track_id:
        payload["trackId"] = track_id

    if transition_id:
        payload["transitionId"] = transition_id

    if draft_id:
        payload["draftId"] = draft_id

    if result:
        payload["result"] = result

    if error:
        payload["error"] = error

    # Add job to BullMQ queue
    await queue.add("result", payload)

    logger.info(
        "Published result",
        result_type=result_type,
        project_id=project_id,
        track_id=track_id,
        transition_id=transition_id,
        draft_id=draft_id,
        has_error=error is not None,
    )


async def publish_progress(
    project_id: Optional[str] = None,
    transition_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    stage: str = "",
    progress: int = 0,
    message: str = "",
):
    """
    Publish a progress update to the results queue for real-time tracking.

    Args:
        project_id: Project identifier
        transition_id: Transition identifier
        draft_id: Draft identifier
        stage: Current stage (extraction, time-stretch, stems, beatmatch, mixing, export)
        progress: Progress percentage (0-100)
        message: Human-readable progress message
    """
    queue = _get_results_queue()

    payload: Dict[str, Any] = {
        "type": "progress",
        "stage": stage,
        "progress": progress,
        "message": message,
    }

    if project_id:
        payload["projectId"] = project_id

    if transition_id:
        payload["transitionId"] = transition_id

    if draft_id:
        payload["draftId"] = draft_id

    # Add job to BullMQ queue
    await queue.add("progress", payload)

    logger.debug(
        "Published progress",
        stage=stage,
        progress=progress,
        project_id=project_id,
        transition_id=transition_id,
        draft_id=draft_id,
    )
