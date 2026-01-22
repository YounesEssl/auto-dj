"""
Logging configuration for Python workers
"""

import logging
import sys
from typing import Any

import numpy as np
import structlog


def _convert_numpy_types(value: Any) -> Any:
    """Convert numpy types to native Python types for cleaner logs."""
    if isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, dict):
        return {k: _convert_numpy_types(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return type(value)(_convert_numpy_types(v) for v in value)
    return value


def numpy_to_python_processor(logger, method_name, event_dict):
    """Structlog processor that converts numpy types to native Python."""
    return {k: _convert_numpy_types(v) for k, v in event_dict.items()}


def setup_logging(log_level: str = "INFO"):
    """
    Configure structured logging using structlog.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Set up standard logging
    # Force flushing and use stderr for immediate output
    handlers = [
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("workers.log")
    ]
    
    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=getattr(logging, log_level.upper()),
        force=True, # Critical: override any existing config
    )

    # Silence noisy third-party loggers
    noisy_loggers = [
        "numba",
        "numba.core",
        "numba.core.ssa",
        "numba.core.byteflow",
        "numba.core.interpreter",
        "httpx",
        "httpcore",
        "httpcore.connection",
        "httpcore.http11",
        "urllib3",
        "anthropic",
        "anthropic._base_client",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            numpy_to_python_processor,  # Convert numpy types before rendering
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
