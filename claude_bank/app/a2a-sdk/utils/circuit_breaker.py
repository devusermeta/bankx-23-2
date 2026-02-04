"""Circuit breaker pattern implementation for A2A calls."""
import logging
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again (half-open state)
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    def can_execute(self) -> bool:
        """Check if request can be executed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        current_time = time.time()

        if self._state == CircuitState.CLOSED:
            return True

        elif self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if (
                self._last_failure_time
                and current_time - self._last_failure_time >= self.timeout_seconds
            ):
                # Transition to half-open
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                return True
            return False

        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    def record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            # Success in half-open state - close the circuit
            logger.info("Circuit breaker transitioning to CLOSED state (recovered)")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

        elif self._state == CircuitState.CLOSED:
            self._success_count += 1
            # Gradually reduce failure count on success
            if self._failure_count > 0:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open state - reopen the circuit
            logger.warning("Circuit breaker transitioning back to OPEN state (still failing)")
            self._state = CircuitState.OPEN
            self._half_open_calls = 0

        elif self._state == CircuitState.CLOSED:
            # Check if threshold reached
            if self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker OPENING (failures: {self._failure_count})"
                )
                self._state = CircuitState.OPEN

    def reset(self):
        """Manually reset the circuit breaker."""
        logger.info("Circuit breaker manually reset to CLOSED state")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

    def __str__(self) -> str:
        """String representation."""
        return (
            f"CircuitBreaker(state={self._state}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )
