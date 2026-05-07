"""Leaky bucket rate limiter for controlling retry attempt flow."""
from __future__ import annotations

import time
from threading import Lock
from typing import Callable, Optional


class BucketOverflow(Exception:
    """Raised when the leaky bucket is full and cannot accept more tokens."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        super().__init__(f"Leaky bucket overflow: capacity {capacity} exceeded")


class LeakyBucket:
    """Token-based leaky bucket that drains at a fixed rate.

    Attempts are accepted only when there is room in the bucket.  The
    bucket drains continuously at *leak_rate* tokens per second, making
    room for new attempts over time.

    Args:
        leak_rate:  Tokens drained per second (must be > 0).
        capacity:   Maximum number of tokens the bucket can hold (must be > 0).
        clock:      Optional callable returning the current time in seconds.
    """

    def __init__(
        self,
        leak_rate: float,
        capacity: int = 10,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if leak_rate <= 0:
            raise ValueError("leak_rate must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._leak_rate = leak_rate
        self._capacity = capacity
        self._clock = clock or time.monotonic
        self._level: float = 0.0
        self._last_leak: float = self._clock()
        self._lock = Lock()

    @property
    def leak_rate(self) -> float:
        return self._leak_rate

    @property
    def capacity(self) -> int:
        return self._capacity

    def _drain(self) -> None:
        """Drain tokens that have leaked since the last call."""
        now = self._clock()
        elapsed = now - self._last_leak
        self._level = max(0.0, self._level - elapsed * self._leak_rate)
        self._last_leak = now

    @property
    def current_level(self) -> float:
        """Return the current fill level after draining."""
        with self._lock:
            self._drain()
            return self._level

    def allow(self) -> bool:
        """Try to add one token.  Returns True if accepted, False if full."""
        with self._lock:
            self._drain()
            if self._level + 1 > self._capacity:
                return False
            self._level += 1
            return True

    def consume(self) -> None:
        """Add one token or raise BucketOverflow if the bucket is full."""
        if not self.allow():
            raise BucketOverflow(self._capacity)
