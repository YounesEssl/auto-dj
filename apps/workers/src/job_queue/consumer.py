"""
Job consumer for processing audio analysis, transitions, and mixing jobs using BullMQ
"""

import asyncio
from typing import Any, Dict

import structlog
from bullmq import Worker

from src.config import settings
from src.job_queue.publisher import publish_result
from src.analysis.analyzer import analyze_track
from src.mixing.mix_generator import generate_mix_for_project
from src.mixing.transition_generator import generate_transition_from_job
from src.mixing.draft_transition_generator import generate_draft_transition_from_job

logger = structlog.get_logger()


async def process_analyze_job(job_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    Process an audio analysis job.

    Args:
        job_data: Job payload containing projectId, trackId, filePath
        job_id: Unique job identifier

    Returns:
        Analysis results
    """
    project_id = job_data["projectId"]
    track_id = job_data["trackId"]
    file_path = job_data["filePath"]

    # Convert relative path to absolute
    absolute_path = settings.get_absolute_path(file_path)

    logger.info(
        "Processing analyze job",
        job_id=job_id,
        project_id=project_id,
        track_id=track_id,
        file_path=absolute_path,
    )

    try:
        # Run analysis in thread pool to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_track, absolute_path)

        # Publish result back to API
        await publish_result(
            result_type="analyze",
            project_id=project_id,
            track_id=track_id,
            result=result,
        )

        logger.info("Analysis complete", track_id=track_id, bpm=result.get("bpm"))
        return result

    except Exception as e:
        logger.error("Analysis failed", track_id=track_id, error=str(e))
        await publish_result(
            result_type="analyze",
            project_id=project_id,
            track_id=track_id,
            error=str(e),
        )
        raise


async def process_transition_job(job_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    Process a transition audio generation job.

    Args:
        job_data: Job payload containing transition parameters
        job_id: Unique job identifier

    Returns:
        Transition generation results
    """
    project_id = job_data["projectId"]
    transition_id = job_data["transitionId"]

    logger.info(
        "Processing transition job",
        job_id=job_id,
        project_id=project_id,
        transition_id=transition_id,
    )

    try:
        # Run transition generation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, generate_transition_from_job, job_data
        )

        # Publish result back to API
        await publish_result(
            result_type="transition_audio",
            project_id=project_id,
            transition_id=transition_id,
            result=result,
        )

        logger.info("Transition generation complete", transition_id=transition_id)
        return result

    except Exception as e:
        logger.error("Transition generation failed", transition_id=transition_id, error=str(e))
        await publish_result(
            result_type="transition_audio",
            project_id=project_id,
            transition_id=transition_id,
            error=str(e),
        )
        raise


async def process_mix_job(job_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    Process a mix generation job.

    Args:
        job_data: Job payload containing projectId, tracks (with analysis), transitions
        job_id: Unique job identifier

    Returns:
        Mix generation results with segments
    """
    project_id = job_data["projectId"]
    tracks_data = job_data.get("tracks", [])
    transitions_data = job_data.get("transitions", [])

    logger.info(
        "Processing mix job",
        job_id=job_id,
        project_id=project_id,
        track_count=len(tracks_data),
    )

    try:
        # Run mix generation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            generate_mix_for_project,
            project_id,
            tracks_data,
            transitions_data
        )

        # Publish result back to API
        await publish_result(
            result_type="mix",
            project_id=project_id,
            result=result,
        )

        logger.info(
            "Mix generation complete",
            project_id=project_id,
            segment_count=len(result.get("segments", []))
        )
        return result

    except Exception as e:
        logger.error("Mix generation failed", project_id=project_id, error=str(e))
        await publish_result(
            result_type="mix",
            project_id=project_id,
            error=str(e),
        )
        raise


async def process_draft_transition_job(job_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    Process a draft transition generation job.

    Args:
        job_data: Job payload containing draft transition parameters
        job_id: Unique job identifier

    Returns:
        Draft transition generation results
    """
    draft_id = job_data["draftId"]

    logger.info(
        "Processing draft transition job",
        job_id=job_id,
        draft_id=draft_id,
    )

    try:
        # Run draft transition generation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, generate_draft_transition_from_job, job_data
        )

        # Publish result back to API
        await publish_result(
            result_type="draft_transition",
            draft_id=draft_id,
            result=result,
        )

        logger.info("Draft transition generation complete", draft_id=draft_id)
        return result

    except Exception as e:
        logger.error("Draft transition generation failed", draft_id=draft_id, error=str(e))
        await publish_result(
            result_type="draft_transition",
            draft_id=draft_id,
            error=str(e),
        )
        raise


async def analyze_job_processor(job, token):
    """BullMQ job processor for analyze queue"""
    logger.info("Received analyze job", job_id=job.id, data=job.data)
    result = await process_analyze_job(job.data, job.id)
    return result


async def transition_job_processor(job, token):
    """BullMQ job processor for transitions queue"""
    logger.info("Received transition job", job_id=job.id, data=job.data)
    result = await process_transition_job(job.data, job.id)
    return result


async def mix_job_processor(job, token):
    """BullMQ job processor for mix queue"""
    logger.info("Received mix job", job_id=job.id, data=job.data)
    result = await process_mix_job(job.data, job.id)
    return result


async def draft_transition_job_processor(job, token):
    """BullMQ job processor for draft transition queue"""
    logger.info("Received draft transition job", job_id=job.id, data=job.data)
    result = await process_draft_transition_job(job.data, job.id)
    return result


def start_worker(worker_id: int):
    """
    Start BullMQ worker processes.

    Args:
        worker_id: Unique identifier for this worker
    """
    # Setup logging in subprocess (not inherited from parent)
    from src.utils.logging import setup_logging
    from src.config import settings
    setup_logging(settings.log_level)

    logger.info("Starting BullMQ worker", worker_id=worker_id)

    async def run_workers():
        redis_opts = {
            "host": settings.redis_host,
            "port": settings.redis_port,
        }
        if settings.redis_password:
            redis_opts["password"] = settings.redis_password

        # Create workers for each queue
        analyze_worker = Worker(
            settings.queue_analyze,
            analyze_job_processor,
            {"connection": redis_opts}
        )

        transitions_worker = Worker(
            settings.queue_transitions,
            transition_job_processor,
            {"connection": redis_opts}
        )

        mix_worker = Worker(
            settings.queue_mix,
            mix_job_processor,
            {"connection": redis_opts}
        )

        draft_transition_worker = Worker(
            settings.queue_draft_transition,
            draft_transition_job_processor,
            {"connection": redis_opts}
        )

        logger.info(
            "Workers started",
            worker_id=worker_id,
            queues=[settings.queue_analyze, settings.queue_transitions, settings.queue_mix, settings.queue_draft_transition],
            redis_host=settings.redis_host,
        )

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Shutting down workers...")
            await analyze_worker.close()
            await transitions_worker.close()
            await mix_worker.close()
            await draft_transition_worker.close()

    asyncio.run(run_workers())
