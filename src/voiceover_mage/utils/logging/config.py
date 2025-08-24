# ABOUTME: Logging configuration management for utils layer
# ABOUTME: Dual-mode operation: interactive CLI (Rich) vs production (JSON)

import contextlib
import io
import logging
import os
import sys
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import structlog


class LoggingMode:
    """Logging mode constants."""

    INTERACTIVE = "interactive"
    PRODUCTION = "production"


def detect_logging_mode() -> str:
    """Detect whether we're running in interactive or production mode.

    Returns:
        LoggingMode constant indicating the detected mode
    """
    # Check environment variable override
    mode = os.getenv("VOICEOVER_MAGE_LOG_MODE")
    if mode and mode.lower() in [LoggingMode.INTERACTIVE, LoggingMode.PRODUCTION]:
        return mode.lower()

    # Check if stdout is a TTY (interactive terminal)
    if sys.stdout.isatty():
        return LoggingMode.INTERACTIVE

    # Default to production for non-TTY environments
    return LoggingMode.PRODUCTION


def create_log_directory() -> Path:
    """Create and return the logs directory path."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir


def setup_third_party_logging():
    """Configure third-party library logging to avoid CLI interference."""
    # Silence crawl4ai and all its internal components
    logging.getLogger("crawl4ai").setLevel(logging.CRITICAL)
    logging.getLogger("crawl4ai.web_crawler").setLevel(logging.CRITICAL)
    logging.getLogger("crawl4ai.chunking_strategy").setLevel(logging.CRITICAL)
    logging.getLogger("crawl4ai.extraction_strategy").setLevel(logging.CRITICAL)

    # Silence LiteLLM (used by crawl4ai)
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
    logging.getLogger("litellm").setLevel(logging.CRITICAL)

    # Silence browser automation libraries
    logging.getLogger("selenium").setLevel(logging.CRITICAL)
    logging.getLogger("playwright").setLevel(logging.CRITICAL)
    logging.getLogger("undetected_chromedriver").setLevel(logging.CRITICAL)

    # Control httpx and httpcore output
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Capture warnings
    logging.captureWarnings(True)
    logging.getLogger("py.warnings").setLevel(logging.ERROR)

    # Silence other potential noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Disable specific chatty loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def add_correlation_id(logger: Any, method_name: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Add correlation ID to log events if not present."""
    if "correlation_id" not in event_dict:
        # Use operation context if available
        context = getattr(logger, "_context", {})
        event_dict["correlation_id"] = context.get("correlation_id") if isinstance(context, dict) else None
    return event_dict


def add_module_context(logger: Any, method_name: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Add module information to log events."""
    if "module" not in event_dict:
        # Extract module from logger name
        logger_name = getattr(logger, "_logger", logger).name
        if logger_name.startswith("voiceover_mage."):
            event_dict["module"] = logger_name.replace("voiceover_mage.", "")
        else:
            event_dict["module"] = logger_name
    return event_dict


def configure_logging(mode: str | None = None, log_level: str = "INFO", log_file: str | None = None) -> None:
    """Configure logging for the application.

    Args:
        mode: Logging mode (interactive/production), auto-detected if None
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Custom log file path, uses default if None
    """
    if mode is None:
        mode = detect_logging_mode()

    # Set up third-party library logging
    setup_third_party_logging()

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    if mode == LoggingMode.INTERACTIVE:
        # Create log directory only for interactive mode
        log_dir = create_log_directory()
        # Interactive mode: beautiful file logs, no console interference
        log_file_path = log_file or str(log_dir / "voiceover-mage.log")
        json_log_path = str(log_dir / "voiceover-mage.json")
        error_log_path = str(log_dir / "errors.log")

        # Configure file handler for human-readable logs
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(numeric_level)

        # Configure JSON file handler for machine-readable logs using structlog
        json_handler = logging.FileHandler(json_log_path)
        json_handler.setLevel(numeric_level)

        # Create a custom formatter that outputs JSON using structlog
        class StructlogJSONFormatter(logging.Formatter):
            def __init__(self):
                super().__init__()
                # JSON processor chain for this handler
                self.processor = structlog.get_logger().bind()

            def format(self, record) -> str:
                # Extract message and context from the log record
                if hasattr(record, "msg") and isinstance(record.msg, dict):
                    # Structured log message
                    event_dict = record.msg.copy()
                    event_dict.update(
                        {
                            "timestamp": self.formatTime(record),
                            "logger": record.name,
                            "level": record.levelname,
                        }
                    )
                else:
                    # Plain text message
                    event_dict = {
                        "timestamp": self.formatTime(record),
                        "logger": record.name,
                        "level": record.levelname,
                        "message": record.getMessage(),
                    }

                # Use structlog's JSON renderer
                json_renderer = structlog.processors.JSONRenderer()
                result = json_renderer(None, "", event_dict)
                return str(result) if isinstance(result, bytes) else result

        json_handler.setFormatter(StructlogJSONFormatter())

        # Configure error-only handler
        error_handler = logging.FileHandler(error_log_path)
        error_handler.setLevel(logging.ERROR)

        # Configure structlog for beautiful file output
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                add_correlation_id,
                add_module_context,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.dev.ConsoleRenderer(colors=False),  # No colors in file logs
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Set up standard library logging
        logging.basicConfig(
            level=numeric_level,
            handlers=[file_handler, json_handler, error_handler],
            format="%(message)s",  # structlog handles formatting
        )

        # Explicitly set root logger level in case basicConfig didn't apply it
        logging.getLogger().setLevel(numeric_level)

    else:
        # Production mode: JSON logs to stdout, no file logging
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                add_correlation_id,
                add_module_context,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure stdout output (structlog JSONRenderer handles JSON formatting)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)

        logging.basicConfig(
            level=numeric_level,
            handlers=[handler],
            format="%(message)s",  # structlog handles all formatting
        )

        # Explicitly set root logger level in case basicConfig didn't apply it
        logging.getLogger().setLevel(numeric_level)


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
    """Context manager to completely suppress stdout/stderr from noisy libraries.

    Use this around crawl4ai operations to prevent any console output from
    bleeding through, including progress bars and status messages.
    """
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # Redirect to null device
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        yield
    finally:
        # Restore original stdout/stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
