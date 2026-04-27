"""Rate limiting support for retry operations."""

import time
from threading import Lock
from typing import Optional


class RateLimiter:
    """Token-bucket rate limiter for controlling retry attempt frequency.

    Limits the number of attempts allowed per second using a token-bucket
    algorithm. Useful when retrying against APIs with strict rate limits.
    """

    def __init__(self, rate: float, capacity: Optional[float] = None) -> None:
        """Initialise the rate limiter.

        Args:
            rate: Maximum number of tokens (attempts) replenished per second.
            capacity: Maximum bucket capacity. Defaults to ``rate``.

        Raises:
            ValueError: If *rate* or *capacity* are not positive.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        capacity = capacity if capacity is not None else rate
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")

        self._rate: float = rate
        self._capacity: float = capacity
        self._tokens: float = capacity
        self._last_refill: float = time.monotonic()
        self._lock: Lock = Lock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rate(self) -> float:
        """Tokens replenished per second."""
        return self._rate

    @property
    def capacity(self) -> float:
        """Maximum bucket capacity."""
        return self._capacity

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Consume one token and return whether the attempt is permitted."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def tokens(self) -> float:
        """Return the current (approximate) token count."""
        with self._lock:
            self._refill()
            return self._tokens

    def reset(self) -> None:
        """Refill the bucket to capacity."""
        with self._lock:
            self._tokens = self._capacity
            self._last_refill = time.monotonic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now
