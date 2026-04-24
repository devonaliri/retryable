"""Retry budget: limits total retry attempts across multiple calls."""

import threading
from typing import Optional


class RetryBudget:
    """Thread-safe token bucket that caps total retries across invocations.

    Each failed attempt consumes one token.  When the budget is exhausted
    the decorator will stop retrying even if individual retry limits have
    not been reached yet.
    """

    def __init__(self, capacity: int, refill_every: Optional[int] = None) -> None:
        """
        Args:
            capacity:     Maximum number of retry tokens available.
            refill_every: If given, the budget is fully refilled after this
                          many *successful* calls (not retried calls).
        """
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._tokens = capacity
        self._refill_every = refill_every
        self._success_count = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def available(self) -> int:
        with self._lock:
            return self._tokens

    def consume(self) -> bool:
        """Try to consume one retry token.

        Returns:
            ``True`` if a token was available and consumed, ``False`` if
            the budget is exhausted.
        """
        with self._lock:
            if self._tokens <= 0:
                return False
            self._tokens -= 1
            return True

    def record_success(self) -> None:
        """Notify the budget that a call succeeded (possibly after retries)."""
        if self._refill_every is None:
            return
        with self._lock:
            self._success_count += 1
            if self._success_count >= self._refill_every:
                self._tokens = self._capacity
                self._success_count = 0

    def reset(self) -> None:
        """Restore the budget to full capacity (useful in tests)."""
        with self._lock:
            self._tokens = self._capacity
            self._success_count = 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetryBudget(capacity={self._capacity}, "
            f"available={self._tokens}, "
            f"refill_every={self._refill_every})"
        )
