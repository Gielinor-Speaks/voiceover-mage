# ABOUTME: Tests for simplified LLM retry logic using tenacity
# ABOUTME: Validates error handling, rate limiting, and retry configuration

import pytest

from voiceover_mage.utils.retry import (
    CircuitBreakerOpen,
    LLMAPIError,
    LLMConnectionError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    configure_llm_retry,
    get_llm_retry_status,
    llm_retry,
    reset_circuit_breaker,
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


class TestRetryConfiguration:
    """Test retry configuration functions."""

    def test_configure_llm_retry(self):
        """Test configuring global retry settings."""
        configure_llm_retry(rate_limit=2.0, circuit_breaker_threshold=5, circuit_breaker_timeout=60.0)

        status = get_llm_retry_status()

        assert status["rate_limiter"]["calls_per_second"] == 2.0
        assert status["circuit_breaker"]["failure_threshold"] == 5

    def test_get_retry_status(self):
        """Test getting current retry status."""
        status = get_llm_retry_status()

        # Should have rate limiter status
        assert "rate_limiter" in status
        assert "calls_per_second" in status["rate_limiter"]
        assert "last_call_time" in status["rate_limiter"]

        # Should have circuit breaker status
        assert "circuit_breaker" in status
        assert "is_open" in status["circuit_breaker"]
        assert "failure_count" in status["circuit_breaker"]
        assert "failure_threshold" in status["circuit_breaker"]


class TestLLMRetryDecorator:
    """Test the LLM retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_retry_successful_function(self):
        """Test retry decorator with successful function."""
        call_count = 0

        @llm_retry(max_attempts=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_converts_generic_exceptions(self):
        """Test that generic exceptions get converted to LLM-specific ones."""
        reset_circuit_breaker()  # Reset state for clean test

        @llm_retry(max_attempts=1, with_circuit_breaker=False)  # Disable circuit breaker for this test
        async def failing_function():
            raise Exception("rate limit exceeded")

        with pytest.raises(LLMRateLimitError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_retry_converts_specific_error_types(self):
        """Test conversion of specific error types."""
        reset_circuit_breaker()  # Reset state for clean test

        @llm_retry(max_attempts=1, with_circuit_breaker=False)  # Disable circuit breaker for this test
        async def timeout_function():
            raise Exception("timeout occurred")

        with pytest.raises(LLMTimeoutError):
            await timeout_function()

    @pytest.mark.asyncio
    async def test_retry_with_recoverable_failure(self):
        """Test retry with recoverable failure types."""
        reset_circuit_breaker()  # Reset state for clean test
        call_count = 0

        @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, with_circuit_breaker=False)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMConnectionError("Connection failed")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_unrecoverable_failure(self):
        """Test retry doesn't retry unrecoverable failures."""
        call_count = 0

        @llm_retry(max_attempts=3)
        async def quota_function():
            nonlocal call_count
            call_count += 1
            raise LLMQuotaExceededError("Quota exceeded")

        with pytest.raises(LLMQuotaExceededError):
            await quota_function()

        # Should only call once since quota errors are not retried
        assert call_count == 1


class TestIntegrationScenarios:
    """Test integration scenarios combining retry features."""

    @pytest.mark.asyncio
    async def test_full_retry_pipeline(self):
        """Test complete retry pipeline with rate limiting."""
        # Configure retry system and reset circuit breaker
        reset_circuit_breaker()
        configure_llm_retry(rate_limit=10.0, circuit_breaker_threshold=5)

        call_count = 0

        @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, with_rate_limiting=True, with_circuit_breaker=False)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMConnectionError("First failure")
            return f"success on attempt {call_count}"

        result = await test_function()
        assert "success" in result
        assert call_count == 2
