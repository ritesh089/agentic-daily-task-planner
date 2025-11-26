"""
Unit tests for framework resilience patterns
"""

import pytest
import time
import asyncio
from framework.resilience import (
    RetryConfig,
    with_retry,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    resilient
)
from framework.errors import FrameworkError


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_calculate_delay(self):
        """Test delay calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        assert config.calculate_delay(0) == 1.0  # 1 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1 * 2^2
    
    def test_max_delay(self):
        """Test maximum delay cap."""
        config = RetryConfig(
            initial_delay=10.0,
            exponential_base=2.0,
            max_delay=15.0,
            jitter=False
        )
        
        assert config.calculate_delay(10) == 15.0  # Capped at max_delay


class TestWithRetry:
    """Tests for @with_retry decorator."""
    
    def test_retry_sync_success(self):
        """Test retry with immediate success (sync)."""
        call_count = {'count': 0}
        
        @with_retry(RetryConfig(max_attempts=3))
        def flaky_function():
            call_count['count'] += 1
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count['count'] == 1
    
    def test_retry_sync_eventual_success(self):
        """Test retry with eventual success (sync)."""
        call_count = {'count': 0}
        
        @with_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
        def flaky_function():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise FrameworkError("Temporary failure", recoverable=True)
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count['count'] == 3
    
    def test_retry_sync_max_attempts(self):
        """Test retry exhausts max attempts (sync)."""
        call_count = {'count': 0}
        
        @with_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
        def always_fails():
            call_count['count'] += 1
            raise FrameworkError("Permanent failure", recoverable=True)
        
        with pytest.raises(FrameworkError):
            always_fails()
        
        assert call_count['count'] == 3
    
    def test_retry_non_recoverable(self):
        """Test retry doesn't retry non-recoverable errors."""
        call_count = {'count': 0}
        
        @with_retry(RetryConfig(max_attempts=3))
        def non_recoverable_error():
            call_count['count'] += 1
            raise FrameworkError("Fatal error", recoverable=False)
        
        with pytest.raises(FrameworkError):
            non_recoverable_error()
        
        assert call_count['count'] == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry with async function."""
        call_count = {'count': 0}
        
        @with_retry(RetryConfig(max_attempts=3, initial_delay=0.1))
        async def async_flaky():
            call_count['count'] += 1
            if call_count['count'] < 2:
                raise FrameworkError("Temporary", recoverable=True)
            return "success"
        
        result = await async_flaky()
        
        assert result == "success"
        assert call_count['count'] == 2


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_initial_state(self):
        """Test circuit breaker initial state."""
        breaker = CircuitBreaker(name="test")
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_successful_call(self):
        """Test successful call through circuit breaker."""
        breaker = CircuitBreaker()
        
        result = breaker.call(lambda: "success")
        
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config, name="test")
        
        # Fail 3 times
        for i in range(3):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
    
    def test_circuit_rejects_when_open(self):
        """Test circuit rejects calls when open."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        for i in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        
        # Next call should be rejected
        with pytest.raises(FrameworkError) as exc_info:
            breaker.call(lambda: "success")
        
        assert "Circuit breaker" in str(exc_info.value)
        assert "OPEN" in str(exc_info.value)
    
    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1  # Short timeout for testing
        )
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        for i in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Next call should transition to half-open
        breaker.call(lambda: "success")
        
        # State should have transitioned to HALF_OPEN and then CLOSED (on success)
        # Or could be in HALF_OPEN if success_threshold > 1
        assert breaker.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
    
    def test_circuit_closes_after_success_threshold(self):
        """Test circuit closes after success threshold in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2
        )
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        for i in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Succeed twice to close circuit
        breaker.call(lambda: "success")
        breaker.call(lambda: "success")
        
        assert breaker.state == CircuitState.CLOSED
    
    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)
        
        # Open the circuit
        for i in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Reset
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestResilient:
    """Tests for @resilient combined decorator."""
    
    def test_resilient_with_retry_only(self):
        """Test resilient decorator with retry only."""
        call_count = {'count': 0}
        
        @resilient(retry_config=RetryConfig(max_attempts=3, initial_delay=0.1))
        def flaky_function():
            call_count['count'] += 1
            if call_count['count'] < 2:
                raise FrameworkError("Temporary", recoverable=True)
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count['count'] == 2

