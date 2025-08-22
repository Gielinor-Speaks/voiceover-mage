# ABOUTME: Logger utilities with context binding and operation tracking decorators
# ABOUTME: Provides get_logger function and decorators for consistent structured logging

import functools
import time
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with automatic module detection.

    Args:
        name: Logger name, auto-detected from caller if None

    Returns:
        Configured structlog logger instance
    """
    if name is None:
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            # Get the module name of the caller
            caller_module = frame.f_back.f_globals.get("__name__", "unknown")
            name = caller_module

    return structlog.get_logger(name or "voiceover_mage")


def generate_operation_id() -> str:
    """Generate a unique operation ID for tracking requests."""
    return str(uuid.uuid4())[:8]


def with_operation_context(operation: str, **context) -> Callable[[F], F]:
    """Decorator to add operation context to function logging.

    Args:
        operation: Operation name for logging
        **context: Additional context to bind to logger

    Returns:
        Decorated function with operation logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            operation_id = generate_operation_id()

            # Bind operation context
            bound_logger = logger.bind(
                operation=operation, operation_id=operation_id, function=func.__name__, **context
            )

            bound_logger.info(f"Starting {operation}")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                bound_logger.info(f"Completed {operation}", duration_seconds=round(duration, 3), success=True)
                return result

            except Exception as e:
                duration = time.time() - start_time
                bound_logger.error(
                    f"Failed {operation}",
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    error_type=type(e).__name__,
                    success=False,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def with_async_operation_context(operation: str, **context) -> Callable[[F], F]:
    """Decorator to add operation context to async function logging.

    Args:
        operation: Operation name for logging
        **context: Additional context to bind to logger

    Returns:
        Decorated async function with operation logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            operation_id = generate_operation_id()

            # Bind operation context
            bound_logger = logger.bind(
                operation=operation, operation_id=operation_id, function=func.__name__, **context
            )

            bound_logger.info(f"Starting {operation}")
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                bound_logger.info(f"Completed {operation}", duration_seconds=round(duration, 3), success=True)
                return result

            except Exception as e:
                duration = time.time() - start_time
                bound_logger.error(
                    f"Failed {operation}",
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    error_type=type(e).__name__,
                    success=False,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def log_api_call(api_name: str, **context) -> Callable[[F], F]:
    """Decorator to log API calls with request/response details.

    Args:
        api_name: Name of the API being called
        **context: Additional context for the API call

    Returns:
        Decorated function with API call logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            call_id = generate_operation_id()

            # Extract URL from function arguments if possible
            url = None
            if args:
                for arg in args:
                    if isinstance(arg, str) and (arg.startswith("http://") or arg.startswith("https://")):
                        url = arg
                        break

            bound_logger = logger.bind(api_name=api_name, call_id=call_id, url=url, **context)

            bound_logger.debug(f"API call to {api_name}")
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log successful API call
                bound_logger.info(
                    f"API call to {api_name} succeeded", duration_seconds=round(duration, 3), success=True
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                bound_logger.error(
                    f"API call to {api_name} failed",
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    error_type=type(e).__name__,
                    success=False,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def log_extraction_step(step_name: str, npc_id: int | None = None) -> Callable[[F], F]:
    """Decorator to log NPC extraction pipeline steps.

    Args:
        step_name: Name of the extraction step
        npc_id: NPC ID being processed (if known)

    Returns:
        Decorated function with extraction step logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            # Try to extract npc_id from arguments if not provided
            actual_npc_id = npc_id
            if actual_npc_id is None:
                for arg in args:
                    if isinstance(arg, int):
                        actual_npc_id = arg
                        break

                # Check kwargs
                if actual_npc_id is None:
                    actual_npc_id = kwargs.get("npc_id") or kwargs.get("id")

            bound_logger = logger.bind(step=step_name, npc_id=actual_npc_id, pipeline="npc_extraction")

            bound_logger.info(f"Starting extraction step: {step_name}")
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log results info if available
                result_info = {}
                if hasattr(result, "__len__"):
                    result_info["result_count"] = len(result)
                if hasattr(result, "name"):
                    result_info["npc_name"] = result.name
                elif isinstance(result, list) and result and hasattr(result[0], "name"):
                    result_info["npc_name"] = result[0].name

                bound_logger.info(
                    f"Completed extraction step: {step_name}",
                    duration_seconds=round(duration, 3),
                    success=True,
                    **result_info,
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                bound_logger.error(
                    f"Failed extraction step: {step_name}",
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    error_type=type(e).__name__,
                    success=False,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


class LogContext:
    """Context manager for binding logger context."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, **context):
        self.logger = logger
        self.context = context
        self.bound_logger = None

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.bound_logger is not None:
            self.bound_logger.error("Context operation failed", error=str(exc_val), error_type=exc_type.__name__)


def with_npc_context(npc_id: int) -> LogContext:
    """Create a logging context for NPC operations.

    Args:
        npc_id: NPC ID for context binding

    Returns:
        LogContext manager with NPC context
    """
    logger = get_logger()
    return LogContext(logger, npc_id=npc_id, entity_type="npc")


def with_pipeline_context(pipeline_name: str, **context) -> LogContext:
    """Create a logging context for pipeline operations.

    Args:
        pipeline_name: Name of the pipeline
        **context: Additional context to bind

    Returns:
        LogContext manager with pipeline context
    """
    logger = get_logger()
    operation_id = generate_operation_id()
    return LogContext(logger, pipeline=pipeline_name, operation_id=operation_id, **context)
