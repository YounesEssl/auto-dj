"""
Main entry point for AutoDJ Python workers
"""

import signal
import sys
from multiprocessing import Process
from typing import List

import structlog

from src.config import settings
from src.job_queue.consumer import start_worker
from src.utils.logging import setup_logging

logger = structlog.get_logger()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received", signal=signum)
    sys.exit(0)


def main():
    """Start the worker processes"""
    setup_logging(settings.log_level)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(
        "Starting AutoDJ workers",
        worker_count=settings.worker_count,
        redis_host=settings.redis_host,
        queues=[
            settings.queue_analyze,
            settings.queue_mix,
            settings.queue_transitions,
            settings.queue_draft_transition
        ],
    )

    # Start worker processes
    processes: List[Process] = []

    try:
        for i in range(settings.worker_count):
            process = Process(
                target=start_worker,
                args=(i,),
                name=f"worker-{i}",
            )
            process.start()
            processes.append(process)
            logger.info("Started worker process", worker_id=i, pid=process.pid)

        # Wait for all processes
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        logger.info("Shutting down workers...")
        for process in processes:
            process.terminate()
            process.join(timeout=5)


if __name__ == "__main__":
    main()
