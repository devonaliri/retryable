"""Circuit breaker pattern for retryable.

Prevents repeated calls to a failing resource by opening the circuit
after a threshold of consecutive failures.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Optional


class CircuitState(Enum):
    CLOSED = auto()   # Normal operation — calls are allowed.
    OPEN = auto()     # Failing — calls are blocked.
    HALF_OPEN = auto()  # Probing — one call allowed to test recovery.


class CircuitBreaker:
    """Tracks consecutive failures and opens the circuit when a threshold
    is exceeded.  After a cooldown period the circuit moves to HALF_OPEN,
    allowing a single probe call through.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._consecutive_failures: int = 0
        self._state: CircuitState = CircuitState.CLOSED
        self._opened_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return current state, transitioning to HALF_OPEN when ready."""
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and (time.monotonic() - self._opened_at) >= self._recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_threshold(self) -> int:
        return self._failure_threshold

    @property
    def recovery_timeout(self) -> float:
        return self._recovery_timeout

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def allow_request(self) -> bool:
        """Return True if a request should be allowed through."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Reset the breaker after a successful call."""
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        """Increment failure count and open the circuit if threshold hit."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None
