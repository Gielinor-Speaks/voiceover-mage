# ABOUTME: Tests for LLM retry logic and error handling
# ABOUTME: Validates exponential backoff, rate limiting, and circuit breaker patterns

import asyncio

import pytest

from voiceover_mage.utils.retry import (
    CircuitBreaker,
    CircuitBreakerOpen,
    LLMAPIError,
    LLMConnectionError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    RateLimiter,
    configure_llm_retry,
    get_llm_retry_status,
    llm_retry,
)


class TestLLMAPIErrors:
    """Test LLM-specific exception types."""

    def test_llm_api_error_hierarchy(self):
        """Test that all LLM errors inherit from LLMAPIError."""
        assert issubclass(LLMRateLimitError, LLMAPIError)
        assert issubclass(LLMQuotaExceededError, LLMAPIError)
        assert issubclass(LLMTimeoutError, LLMAPIError)
        assert issubclass(LLMConnectionError, LLMAPIError)
        assert issubclass(CircuitBreakerOpen, LLMAPIError)

    def test_error_messages(self):
        """Test error creation with messages."""
        rate_limit_error = LLMRateLimitError("Rate limit exceeded")
        assert str(rate_limit_error) == "Rate limit exceeded"

        quota_error = LLMQuotaExceededError("Quota exhausted")
        assert str(quota_error) == "Quota exhausted"


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_no_delay(self):
        """Test rate limiter with unlimited rate."""
        rate_limiter = RateLimiter(calls_per_second=0)  # No limit

        start_time = asyncio.get_event_loop().time()
        await rate_limiter.acquire()
        await rate_limiter.acquire()
        end_time = asyncio.get_event_loop().time()

        # Should be nearly instantaneous
        assert end_time - start_time < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_with_delay(self):
        """Test rate limiter enforces delays."""
        rate_limiter = RateLimiter(calls_per_second=2.0)  # 2 calls per second

        start_time = asyncio.get_event_loop().time()
        await rate_limiter.acquire()  # First call immediate
        await rate_limiter.acquire()  # Second call should be delayed
        end_time = asyncio.get_event_loop().time()

        # Should take at least 0.5 seconds (1/2 calls per second)
        assert end_time - start_time >= 0.4  # Allow some margin for timing


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker(failure_threshold=3)

        def successful_function():
            return "success"

        wrapped = breaker(successful_function)
        result = wrapped()

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        def failing_function():
            raise ValueError("Test failure")

        wrapped = breaker(failing_function)

        # First failure
        with pytest.raises(ValueError):
            wrapped()
        assert breaker.state == "closed"
        assert breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            wrapped()
        assert breaker.state == "open"
        assert breaker.failure_count == 2

        # Third attempt - should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            wrapped()

    def test_circuit_breaker_ignores_unexpected_exceptions(self):
        """Test circuit breaker doesn't count unexpected exceptions."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        def function_with_type_error():
            raise TypeError("Different error type")

        wrapped = breaker(function_with_type_error)

        # TypeError should not be caught by circuit breaker
        with pytest.raises(TypeError):
            wrapped()
        assert breaker.state == "closed"
        assert breaker.failure_count == 0


class TestLLMRetryDecorator:
    """Test the main LLM retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_successful_function(self):
        """Test retry decorator with successful function."""

        @llm_retry(max_attempts=3, with_rate_limiting=False, with_circuit_breaker=False)
        async def successful_function():
            return "success"

        result = await successful_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_recoverable_failure(self):
        """Test retry with function that fails then succeeds."""
        call_count = 0

        @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.1, with_rate_limiting=False, with_circuit_breaker=False)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMTimeoutError("Temporary timeout")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_unrecoverable_failure(self):
        """Test retry with quota exceeded (should not retry)."""
        call_count = 0

        @llm_retry(max_attempts=3, with_rate_limiting=False, with_circuit_breaker=False)
        async def quota_exceeded_function():
            nonlocal call_count
            call_count += 1
            raise LLMQuotaExceededError("Quota exceeded")

        with pytest.raises(LLMQuotaExceededError):
            await quota_exceeded_function()

        # Should not retry quota exceeded errors
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_converts_generic_exceptions(self):
        """Test retry decorator converts generic exceptions to LLM errors."""

        @llm_retry(max_attempts=2, with_rate_limiting=False, with_circuit_breaker=True)
        async def function_with_generic_error():
            raise Exception("Generic error")

        with pytest.raises(LLMAPIError, match="LLM API call failed"):
            await function_with_generic_error()

    @pytest.mark.asyncio
    async def test_retry_converts_specific_error_types(self):
        """Test retry decorator converts specific errors to LLM types."""

        @llm_retry(max_attempts=2, with_rate_limiting=False, with_circuit_breaker=True)
        async def rate_limit_function():
            raise Exception("rate limit exceeded")

        with pytest.raises(LLMAPIError, match="Rate limit exceeded"):
            await rate_limit_function()


class TestRetryConfiguration:
    """Test retry configuration functions."""

    def test_configure_llm_retry(self):
        """Test configuring global retry settings."""
        configure_llm_retry(rate_limit=2.0, circuit_breaker_threshold=5, circuit_breaker_timeout=60.0)

        status = get_llm_retry_status()

        assert status["rate_limiter"]["calls_per_second"] == 2.0
        assert status["circuit_breaker"]["failure_threshold"] == 5
        assert status["circuit_breaker"]["timeout"] == 60.0

    def test_get_retry_status(self):
        """Test getting current retry status."""
        status = get_llm_retry_status()

        # Should have rate limiter status
        assert "rate_limiter" in status
        assert "calls_per_second" in status["rate_limiter"]
        assert "min_interval" in status["rate_limiter"]

        # Should have circuit breaker status
        assert "circuit_breaker" in status
        assert "state" in status["circuit_breaker"]
        assert "failure_count" in status["circuit_breaker"]
        assert "failure_threshold" in status["circuit_breaker"]


class TestIntegrationScenarios:
    """Test integration scenarios combining retry features."""

    @pytest.mark.asyncio
    async def test_full_retry_pipeline(self):
        """Test complete retry pipeline with rate limiting and circuit breaker."""
        call_count = 0

        @llm_retry(
            max_attempts=3,
            min_wait=0.01,
            max_wait=0.1,
            with_rate_limiting=False,  # Disable for test speed
            with_circuit_breaker=False,  # Disable for predictable testing
        )
        async def realistic_llm_function():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise LLMConnectionError("Connection failed")
            elif call_count == 2:
                raise LLMTimeoutError("Request timeout")
            else:
                return {"analysis": "Character appears to be a wise mentor"}

        result = await realistic_llm_function()

        assert result["analysis"] == "Character appears to be a wise mentor"
        assert call_count == 3  # Should retry twice then succeed
