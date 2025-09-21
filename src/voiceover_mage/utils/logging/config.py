# ABOUTME: Simplified logging configuration using loguru
# ABOUTME: Dual-mode operation: interactive CLI vs production JSON logging

import contextlib
import io
import logging
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger


class LoggingMode:
    """Logging mode constants."""

    INTERACTIVE = "interactive"
    PRODUCTION = "production"


def detect_logging_mode() -> str:
    """Detect whether we're running in interactive or production mode."""
    mode = os.getenv("VOICEOVER_MAGE_LOG_MODE")
    if mode and mode.lower() in [LoggingMode.INTERACTIVE, LoggingMode.PRODUCTION]:
        return mode.lower()

    return LoggingMode.INTERACTIVE if sys.stdout.isatty() else LoggingMode.PRODUCTION


def setup_third_party_logging() -> None:
    """Configure third-party library logging to avoid CLI interference."""
    # Critical loggers (complete silence)
    critical_loggers = [
        "crawl4ai",
        "crawl4ai.web_crawler",
        "crawl4ai.chunking_strategy",
        "crawl4ai.extraction_strategy",
        "LiteLLM",
        "litellm",
        "selenium",
        "playwright",
        "undetected_chromedriver",
    ]

    # Warning level loggers
    warning_loggers = ["httpx", "httpcore", "urllib3", "requests", "asyncio", "websockets", "aiohttp"]

    for logger_name in critical_loggers:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)

    for logger_name in warning_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.captureWarnings(True)
    logging.getLogger("py.warnings").setLevel(logging.ERROR)


def configure_logging(mode: str | None = None, log_level: str = "INFO", log_file: str | None = None) -> None:
    """Configure logging using loguru.

    Args:
        mode: Logging mode (interactive/production), auto-detected if None
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Custom log file path, uses default if None
    """
    if mode is None:
        mode = detect_logging_mode()

    setup_third_party_logging()

    # Set standard library logging level for compatibility with tests
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_level)

    # Remove default loguru handler
    logger.remove()

    if mode == LoggingMode.INTERACTIVE:
        # Interactive mode: logs to files, no console interference
        log_dir = Path("logs")

        # Robust directory creation with retry logic for race conditions
        max_retries = 3
        for attempt in range(max_retries):
            try:
                log_dir.mkdir(exist_ok=True)
                break
            except (FileNotFoundError, PermissionError, OSError):
                if attempt == max_retries - 1:
                    # Final fallback: switch to production mode (no file logging)
                    mode = LoggingMode.PRODUCTION
                    break
                # Brief pause to avoid tight retry loops
                import time

                time.sleep(0.01 * (attempt + 1))  # 10ms, 20ms, 30ms

        # If we couldn't create the directory, fall back to production mode
        if mode == LoggingMode.PRODUCTION:
            logger.add(sys.stdout, level=log_level, format="{time} | {level} | {name} | {message}", serialize=True)
            return

        log_file_path = log_file or str(log_dir / "voiceover-mage.log")

        # Human-readable logs
        logger.add(
            log_file_path,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
        )

        # JSON logs for machine processing
        logger.add(
            log_dir / "voiceover-mage.json",
            level=log_level,
            format="{time} | {level} | {name} | {message}",
            serialize=True,
            rotation="10 MB",
            retention="7 days",
        )

        # Errors only
        logger.add(
            log_dir / "errors.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production mode: JSON to stdout
        logger.add(sys.stdout, level=log_level, format="{time} | {level} | {name} | {message}", serialize=True)


def get_logging_status() -> dict[str, Any]:
    """Get current logging configuration status."""
    mode = detect_logging_mode()
    log_dir = Path("logs")

    return {
        "mode": mode,
        "log_directory": str(log_dir.absolute()) if log_dir.exists() else None,
        "log_files": {
            "main": str(log_dir / "voiceover-mage.log") if mode == LoggingMode.INTERACTIVE else None,
            "json": str(log_dir / "voiceover-mage.json") if mode == LoggingMode.INTERACTIVE else None,
            "errors": str(log_dir / "errors.log") if mode == LoggingMode.INTERACTIVE else None,
        },
        "third_party_suppressed": [
            "crawl4ai",
            "httpx",
            "urllib3",
            "requests",
            "py.warnings",
            "LiteLLM",
            "selenium",
            "playwright",
        ],
    }


@contextlib.contextmanager
def suppress_library_output():
    """Context manager to completely suppress stdout/stderr from noisy libraries."""
    original_stdout, original_stderr = sys.stdout, sys.stderr

    try:
        sys.stdout = sys.stderr = io.StringIO()
        yield
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
