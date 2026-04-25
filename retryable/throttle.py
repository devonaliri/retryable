"""Rate-limiting / throttle support for retry attempts."""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Optional


class RetryThrottle:
    """Sliding-window rate limiter that caps the number of retry attempts
    allowed within a rolling time window.

    Parameters
    ----------
    max_attempts:
        Maximum number of attempts permitted inside *window_seconds*.
    window_seconds:
        Length of the rolling window in seconds.
    """

    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self._max_attempts = max_attempts
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def max_attempts(self) -> int:
        """Maximum attempts allowed per window."""
        return self._max_attempts

    @property
    def window_seconds(self) -> float:
        """Width of the rolling window in seconds."""
        return self._window

    def allow(self) -> bool:
        """Return *True* and record the attempt if the rate limit allows it;
        return *False* without recording if the limit has been reached."""
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            if len(self._timestamps) >= self._max_attempts:
                return False
            self._timestamps.append(now)
            return True

    def remaining(self) -> int:
        """Number of attempts still available in the current window."""
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            return max(0, self._max_attempts - len(self._timestamps))

    def reset(self) -> None:
        """Clear all recorded timestamps (useful for testing)."""
        with self._lock:
            self._timestamps.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Remove timestamps that have fallen outside the window."""
        cutoff = now - self._window
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
