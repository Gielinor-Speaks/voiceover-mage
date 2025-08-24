# ABOUTME: Retry logic and error handling for LLM API calls
# ABOUTME: Implements exponential backoff, rate limiting, and circuit breaker patterns

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from voiceover_mage.utils.logging import get_logger

# Type variable for generic functions
T = TypeVar("T")

# Logger for retry operations
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


class CircuitBreaker:
    """Simple circuit breaker for API calls."""

    def __init__(
        self, failure_threshold: int = 5, timeout: float = 60.0, expected_exception: type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""

        def wrapper(*args, **kwargs):
            return self._call(func, *args, **kwargs)

        return wrapper

    def _call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker logic."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("Circuit breaker half-open, attempting request")
            else:
                logger.warning("Circuit breaker open, rejecting request")
                raise CircuitBreakerOpen(
                    f"Circuit breaker open. Last failure: {self.last_failure_time}. "
                    f"Will retry after {self.timeout} seconds."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
        if self.state == "half_open":
            logger.info("Circuit breaker reset after successful request")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count,
                failure_threshold=self.failure_threshold,
                timeout=self.timeout,
            )


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second if calls_per_second > 0 else 0
        self.last_call_time = 0.0

    async def acquire(self):
        """Acquire rate limit permission."""
        if self.min_interval <= 0:
            return

        current_time = time.time()
        time_since_last = current_time - self.last_call_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.debug("Rate limiting: sleeping for %.2f seconds", sleep_time)
            await asyncio.sleep(sleep_time)

        self.last_call_time = time.time()


# Global rate limiter for LLM API calls (1 call per second by default)
_llm_rate_limiter = RateLimiter(calls_per_second=1.0)

# Global circuit breaker for LLM API calls
_llm_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30.0, expected_exception=LLMAPIError)


def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    with_rate_limiting: bool = True,
    with_circuit_breaker: bool = True,
):
    """
    Decorator for retrying LLM API calls with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        multiplier: Exponential backoff multiplier
        with_rate_limiting: Whether to apply rate limiting
        with_circuit_breaker: Whether to use circuit breaker pattern
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(
                (
                    LLMRateLimitError,
                    LLMTimeoutError,
                    LLMConnectionError,
                    # Don't retry quota exceeded or circuit breaker open
                )
            ),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
            after=after_log(logging.getLogger(__name__), logging.INFO),
            reraise=True,
        )
        async def wrapper(*args, **kwargs) -> T:
            # Apply rate limiting
            if with_rate_limiting:
                await _llm_rate_limiter.acquire()

            # Apply circuit breaker
            if with_circuit_breaker:
                try:
                    return await _llm_circuit_breaker._call(func, *args, **kwargs)
                except Exception as e:
                    # Convert generic exceptions to LLM-specific ones for better handling
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        raise LLMRateLimitError(f"Rate limit exceeded: {e}") from e
                    elif "quota" in str(e).lower() or "billing" in str(e).lower():
                        raise LLMQuotaExceededError(f"API quota exceeded: {e}") from e
                    elif "timeout" in str(e).lower():
                        raise LLMTimeoutError(f"Request timeout: {e}") from e
                    elif "connection" in str(e).lower() or "network" in str(e).lower():
                        raise LLMConnectionError(f"Connection failed: {e}") from e
                    else:
                        # Wrap other exceptions as generic LLM API errors
                        raise LLMAPIError(f"LLM API call failed: {e}") from e
            else:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@asynccontextmanager
async def llm_batch_context(calls_per_second: float = 2.0):
    """
    Context manager for batch LLM operations with higher rate limits.

    Args:
        calls_per_second: Higher rate limit for batch operations
    """
    global _llm_rate_limiter
    original_rate_limiter = _llm_rate_limiter

    try:
        # Temporarily increase rate limit for batch operations
        _llm_rate_limiter = RateLimiter(calls_per_second=calls_per_second)
        logger.info("Batch LLM context started", calls_per_second=calls_per_second)
        yield
    finally:
        # Restore original rate limiter
        _llm_rate_limiter = original_rate_limiter
        logger.info("Batch LLM context ended")


def configure_llm_retry(
    rate_limit: float = 1.0, circuit_breaker_threshold: int = 3, circuit_breaker_timeout: float = 30.0
):
    """
    Configure global LLM retry settings.

    Args:
        rate_limit: Global rate limit (calls per second)
        circuit_breaker_threshold: Number of failures before circuit breaker opens
        circuit_breaker_timeout: Time to wait before attempting to close circuit breaker
    """
    global _llm_rate_limiter, _llm_circuit_breaker

    _llm_rate_limiter = RateLimiter(calls_per_second=rate_limit)
    _llm_circuit_breaker = CircuitBreaker(
        failure_threshold=circuit_breaker_threshold, timeout=circuit_breaker_timeout, expected_exception=LLMAPIError
    )

    logger.info(
        "LLM retry configuration updated",
        rate_limit=rate_limit,
        circuit_breaker_threshold=circuit_breaker_threshold,
        circuit_breaker_timeout=circuit_breaker_timeout,
    )


def get_llm_retry_status() -> dict[str, Any]:
    """Get current status of LLM retry mechanisms."""
    return {
        "rate_limiter": {
            "calls_per_second": _llm_rate_limiter.calls_per_second,
            "last_call_time": _llm_rate_limiter.last_call_time,
            "min_interval": _llm_rate_limiter.min_interval,
        },
        "circuit_breaker": {
            "state": _llm_circuit_breaker.state,
            "failure_count": _llm_circuit_breaker.failure_count,
            "failure_threshold": _llm_circuit_breaker.failure_threshold,
            "last_failure_time": _llm_circuit_breaker.last_failure_time,
            "timeout": _llm_circuit_breaker.timeout,
        },
    }
