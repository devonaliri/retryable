"""Timeout support for retry attempts."""

import time
from typing import Optional


class RetryTimeout:
    """Tracks wall-clock time budget across all retry attempts."""

    def __init__(self, total_seconds: float) -> None:
        if total_seconds <= 0:
            raise ValueError("total_seconds must be positive")
        self._total_seconds = total_seconds
        self._start: Optional[float] = None

    def start(self) -> None:
        """Record the start time. Must be called before checking elapsed/remaining."""
        self._start = time.monotonic()

    @property
    def total_seconds(self) -> float:
        return self._total_seconds

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since start() was called."""
        if self._start is None:
            raise RuntimeError("RetryTimeout.start() has not been called")
        return time.monotonic() - self._start

    @property
    def remaining(self) -> float:
        """Seconds remaining before the budget is exhausted."""
        return max(0.0, self._total_seconds - self.elapsed)

    @property
    def is_expired(self) -> bool:
        """True when the time budget has been fully consumed."""
        return self.elapsed >= self._total_seconds

    def clamp_delay(self, delay: float) -> float:
        """Return *delay* clamped so it does not exceed the remaining budget."""
        return min(delay, self.remaining)

    def __repr__(self) -> str:  # pragma: no cover
        started = self._start is not None
        return (
            f"RetryTimeout(total_seconds={self._total_seconds}, "
            f"started={started})"
        )
