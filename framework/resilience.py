"""
Resilience Patterns

Provides circuit breaker, retry, and other fault tolerance patterns
for building resilient workflows.
"""

import asyncio
import time
import random
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Type, Any, TypeVar
from functools import wraps
from enum import Enum

from framework.errors import FrameworkError, is_recoverable, get_retry_delay

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Retry Configuration
# ============================================================================

@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff (2.0 = double each time)
        jitter: Add random jitter to delays to prevent thundering herd
        jitter_factor: Maximum jitter as fraction of delay (0.1 = ±10%)
        retry_on: Tuple of exception types to retry on
    """
    
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retry_on: tuple[Type[Exception], ...] = (FrameworkError,)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        # Exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Add jitter
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        config: Retry configuration (uses defaults if None)
    
    Example:
        @with_retry(RetryConfig(max_attempts=5))
        async def fetch_data():
            # Automatically retries on recoverable errors
            response = await api_call()
            return response
    
    Returns:
        Decorated function with retry logic
    """
    config_ = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                last_error: Optional[Exception] = None
                
                for attempt in range(config_.max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    
                    except config_.retry_on as e:
                        last_error = e
                        
                        # Check if error is recoverable
                        if isinstance(e, FrameworkError) and not e.recoverable:
                            logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                            raise
                        
                        # Last attempt, don't retry
                        if attempt == config_.max_attempts - 1:
                            logger.error(
                                f"Max retry attempts ({config_.max_attempts}) "
                                f"reached for {func.__name__}"
                            )
                            raise
                        
                        # Calculate delay
                        if isinstance(e, FrameworkError) and e.retry_after:
                            delay = e.retry_after
                        else:
                            delay = config_.calculate_delay(attempt)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{config_.max_attempts} failed "
                            f"for {func.__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        
                        await asyncio.sleep(delay)
                
                # Should never reach here, but satisfy type checker
                raise last_error or RuntimeError("Retry loop completed unexpectedly")
            
            return async_wrapper
        
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                last_error: Optional[Exception] = None
                
                for attempt in range(config_.max_attempts):
                    try:
                        return func(*args, **kwargs)
                    
                    except config_.retry_on as e:
                        last_error = e
                        
                        # Check if error is recoverable
                        if isinstance(e, FrameworkError) and not e.recoverable:
                            logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                            raise
                        
                        # Last attempt, don't retry
                        if attempt == config_.max_attempts - 1:
                            logger.error(
                                f"Max retry attempts ({config_.max_attempts}) "
                                f"reached for {func.__name__}"
                            )
                            raise
                        
                        # Calculate delay
                        if isinstance(e, FrameworkError) and e.retry_after:
                            delay = e.retry_after
                        else:
                            delay = config_.calculate_delay(attempt)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{config_.max_attempts} failed "
                            f"for {func.__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        
                        time.sleep(delay)
                
                # Should never reach here, but satisfy type checker
                raise last_error or RuntimeError("Retry loop completed unexpectedly")
            
            return sync_wrapper
    
    return decorator


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker.
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying half-open
        success_threshold: Successes in half-open before closing
        expected_exception: Exception type that triggers circuit breaker
    """
    
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2
    expected_exception: Type[Exception] = Exception


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by failing fast when a service is unavailable.
    
    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, reject requests immediately
        - HALF_OPEN: Testing recovery, allow limited requests
    
    Example:
        breaker = CircuitBreaker(
            config=CircuitBreakerConfig(failure_threshold=3)
        )
        
        @breaker.protected
        async def call_external_api():
            return await api.fetch()
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
        self.config = config or CircuitBreakerConfig()
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            Function result
        
        Raises:
            FrameworkError: If circuit is open
            Exception: If function call fails
        """
        # Check if we should transition to half-open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                from framework.errors import WorkflowExecutionError
                raise WorkflowExecutionError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    recoverable=True,
                    retry_after=int(self.config.recovery_timeout)
                )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' closing (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' reopening (recovery failed)")
            self.state = CircuitState.OPEN
            self.success_count = 0
        
        elif self.failure_count >= self.config.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' opening "
                f"(threshold: {self.config.failure_threshold} failures)"
            )
            self.state = CircuitState.OPEN
    
    def protected(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to protect a function with circuit breaker.
        
        Example:
            breaker = CircuitBreaker()
            
            @breaker.protected
            def risky_operation():
                return external_api.call()
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return self.call(lambda: func(*args, **kwargs))
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(lambda: func(*args, **kwargs))
            return sync_wrapper
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name}, state={self.state.value}, "
            f"failures={self.failure_count})"
        )


# ============================================================================
# Circuit Breaker Manager
# ============================================================================

class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    _breakers: dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_breaker(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(config, name)
        return cls._breakers[name]
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()
    
    @classmethod
    def get_status(cls) -> dict[str, dict]:
        """Get status of all circuit breakers."""
        return {
            name: {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'success_count': breaker.success_count,
                'last_failure': breaker.last_failure_time
            }
            for name, breaker in cls._breakers.items()
        }


# ============================================================================
# Combined Decorator
# ============================================================================

def resilient(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
):
    """
    Combined decorator for retry + circuit breaker.
    
    Args:
        retry_config: Retry configuration
        circuit_breaker_name: Name of circuit breaker (if None, no circuit breaker)
        circuit_breaker_config: Circuit breaker configuration
    
    Example:
        @resilient(
            retry_config=RetryConfig(max_attempts=3),
            circuit_breaker_name="external_api"
        )
        async def call_api():
            return await api.fetch()
    """
    retry_cfg = retry_config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Apply circuit breaker if requested
        if circuit_breaker_name:
            breaker = CircuitBreakerManager.get_breaker(
                circuit_breaker_name,
                circuit_breaker_config
            )
            func = breaker.protected(func)
        
        # Apply retry
        func = with_retry(retry_cfg)(func)
        
        return func
    
    return decorator

