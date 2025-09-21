# ABOUTME: Simplified retry logic using tenacity library
# ABOUTME: Leverages tenacity's built-in features for exponential backoff and circuit breaking

import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from voiceover_mage.utils.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class LLMAPIError(Exception):
    """Base exception for LLM API-related errors."""

    pass


class LLMRateLimitError(LLMAPIError):
    """Raised when API rate limit is exceeded."""

    pass


class LLMQuotaExceededError(LLMAPIError):
    """Raised when API quota is exceeded."""

    pass


class LLMTimeoutError(LLMAPIError):
    """Raised when API request times out."""

    pass


class LLMConnectionError(LLMAPIError):
    """Raised when connection to API fails."""

    pass


class CircuitBreakerOpen(LLMAPIError):
    """Raised when circuit breaker is open due to repeated failures."""

    pass


# Circuit breaker state (simplified using tenacity stop conditions)
_circuit_breaker_state = {
    "failure_count": 0,
    "last_failure_time": None,
    "threshold": 3,
    "timeout": 30.0,
    "is_open": False,
}


def _circuit_breaker_stop(retry_state):
    """Tenacity stop condition that implements circuit breaker logic."""
    global _circuit_breaker_state

    current_time = time.time()
    state = _circuit_breaker_state

    # Check if circuit breaker should reset
    if (
        state["is_open"]
        and state["last_failure_time"]
        and current_time - state["last_failure_time"] >= state["timeout"]
    ):
        state["is_open"] = False
        state["failure_count"] = 0
        logger.info("Circuit breaker reset")

    # If circuit is open, stop retrying
    if state["is_open"]:
        return True  # Stop retrying

    # Only count failures, let tenacity handle the retry logic
    # Don't interfere with tenacity's attempt counting
    if retry_state.outcome and retry_state.outcome.failed:
        state["failure_count"] += 1
        state["last_failure_time"] = current_time

        if state["failure_count"] >= state["threshold"]:
            state["is_open"] = True
            logger.warning("Circuit breaker opened", failures=state["failure_count"])
            return True  # Stop retrying

    return False  # Continue retrying


# Global rate limiter state
_rate_limiter_state = {
    "calls_per_second": 1.0,
    "last_call_time": 0.0,
}


async def _apply_rate_limiting():
    """Apply rate limiting using simple async sleep."""
    state = _rate_limiter_state

    if state["calls_per_second"] <= 0:
        return

    min_interval = 1.0 / state["calls_per_second"]
    current_time = time.time()
    time_since_last = current_time - state["last_call_time"]

    if time_since_last < min_interval:
        sleep_time = min_interval - time_since_last
        logger.debug("Rate limiting", sleep_time=sleep_time)
        await asyncio.sleep(sleep_time)

    state["last_call_time"] = time.time()


def _convert_exception(e: Exception) -> Exception:
    """Convert generic exceptions to LLM-specific ones for better handling."""
    error_str = str(e).lower()

    if "rate limit" in error_str or "429" in error_str:
        return LLMRateLimitError(f"Rate limit exceeded: {e}")
    elif "quota" in error_str or "billing" in error_str:
        return LLMQuotaExceededError(f"API quota exceeded: {e}")
    elif "timeout" in error_str:
        return LLMTimeoutError(f"Request timeout: {e}")
    elif "connection" in error_str or "network" in error_str:
        return LLMConnectionError(f"Connection failed: {e}")
    else:
        return LLMAPIError(f"LLM API call failed: {e}")


def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    with_rate_limiting: bool = True,
    with_circuit_breaker: bool = True,
):
    """Simplified LLM retry decorator using tenacity."""

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Apply rate limiting before each attempt
            if with_rate_limiting:
                await _apply_rate_limiting()

            # Configure retry strategy
            retry_kwargs = {
                "stop": stop_after_attempt(max_attempts),
                "wait": wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
                "retry": retry_if_exception_type(
                    (
                        LLMRateLimitError,
                        LLMTimeoutError,
                        LLMConnectionError,
                    )
                ),
                "reraise": True,
            }

            # Add circuit breaker if enabled
            if with_circuit_breaker:
                retry_kwargs["stop"] = _circuit_breaker_stop

            async for attempt in AsyncRetrying(**retry_kwargs):
                with attempt:
                    try:
                        return await func(*args, **kwargs)
                    except (
                        LLMAPIError,
                        LLMRateLimitError,
                        LLMTimeoutError,
                        LLMConnectionError,
                        LLMQuotaExceededError,
                        CircuitBreakerOpen,
                    ) as e:
                        # Already an LLM-specific exception, re-raise as-is
                        raise e
                    except Exception as e:
                        # Convert generic exceptions to LLM-specific ones
                        raise _convert_exception(e) from e

        return wrapper

    return decorator


@asynccontextmanager
async def llm_batch_context(calls_per_second: float = 2.0):
    """Context manager for batch LLM operations with higher rate limits."""
    global _rate_limiter_state
    original_rate = _rate_limiter_state["calls_per_second"]

    try:
        _rate_limiter_state["calls_per_second"] = calls_per_second
        logger.info("Batch LLM context started", calls_per_second=calls_per_second)
        yield
    finally:
        _rate_limiter_state["calls_per_second"] = original_rate
        logger.info("Batch LLM context ended")


def configure_llm_retry(
    rate_limit: float = 1.0, circuit_breaker_threshold: int = 3, circuit_breaker_timeout: float = 30.0
):
    """Configure global LLM retry settings."""
    global _rate_limiter_state, _circuit_breaker_state

    _rate_limiter_state["calls_per_second"] = rate_limit
    _circuit_breaker_state.update(
        {
            "threshold": circuit_breaker_threshold,
            "timeout": circuit_breaker_timeout,
            "failure_count": 0,
            "is_open": False,
        }
    )

    logger.info("LLM retry configured", rate_limit=rate_limit, threshold=circuit_breaker_threshold)


def get_llm_retry_status() -> dict[str, Any]:
    """Get current status of LLM retry mechanisms."""
    return {
        "rate_limiter": {
            "calls_per_second": _rate_limiter_state["calls_per_second"],
            "last_call_time": _rate_limiter_state["last_call_time"],
        },
        "circuit_breaker": {
            "is_open": _circuit_breaker_state["is_open"],
            "failure_count": _circuit_breaker_state["failure_count"],
            "failure_threshold": _circuit_breaker_state["threshold"],
        },
    }


def reset_circuit_breaker():
    """Reset circuit breaker state (useful for testing)."""
    global _circuit_breaker_state
    _circuit_breaker_state.update(
        {
            "failure_count": 0,
            "last_failure_time": None,
            "is_open": False,
        }
    )
