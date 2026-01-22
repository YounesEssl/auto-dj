"""
Configuration management for AutoDJ workers
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


def get_default_storage_path() -> str:
    """Get default storage path based on environment."""
    # In Docker, storage is at /app/storage
    if os.path.exists("/app/storage"):
        return "/app/storage"
    # Local development: relative to project root
    workers_dir = Path(__file__).parent.parent
    project_root = workers_dir.parent.parent
    return str(project_root / "apps" / "api" / "storage")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # Worker
    worker_count: int = 2
    log_level: str = "INFO"

    # Storage - path where API stores files (auto-detected or from env)
    storage_base_path: str = get_default_storage_path()

    # Audio Processing
    max_track_duration_minutes: int = 15
    demucs_model: str = "htdemucs"  # Base model - good quality, lower memory usage

    # Output paths
    output_path: str = get_default_storage_path()

    # Queue Names (must match NestJS API)
    queue_analyze: str = "audio-analyze"
    queue_transitions: str = "audio-transitions"
    queue_mix: str = "audio-mix"
    queue_results: str = "results"
    queue_draft_transition: str = "draft-transition"
    queue_chat_reorder: str = "chat-reorder"

    # LLM Configuration
    mistral_api_key: str = ""

    def get_absolute_path(self, relative_path: str) -> str:
        """Convert a relative storage path to absolute path."""
        # Strip leading "storage/" since base path already points to storage
        if relative_path.startswith("storage/"):
            relative_path = relative_path[8:]  # Remove "storage/"
        return str(Path(self.storage_base_path) / relative_path)

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
