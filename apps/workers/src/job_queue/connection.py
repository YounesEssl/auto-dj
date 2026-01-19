"""
Redis connection management
"""

from functools import lru_cache

import redis
import structlog

from src.config import settings

logger = structlog.get_logger()


@lru_cache
def get_redis_connection() -> redis.Redis:
    """
    Get a cached Redis connection instance.

    Returns:
        redis.Redis: Redis client instance
    """
    connection = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )

    # Test connection
    try:
        connection.ping()
        logger.info(
            "Connected to Redis",
            host=settings.redis_host,
            port=settings.redis_port,
        )
    except redis.ConnectionError as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise

    return connection


def get_redis_url() -> str:
    """Get Redis URL for RQ"""
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}"
    return f"redis://{settings.redis_host}:{settings.redis_port}"
