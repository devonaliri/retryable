"""Deadline enforcement for retry operations.

Provides a Deadline class that tracks an absolute wall-clock cutoff,
allowing callers to check whether time remains before attempting another
retry or sleeping through a backoff delay.
"""

from __future__ import annotations

import time
from typing import Optional


class DeadlineExceeded(Exception):
    """Raised when an operation is attempted after the deadline has passed."""

    def __init__(self, deadline: "Deadline") -> None:
        self.deadline = deadline
        super().__init__(
            f"Deadline exceeded: {deadline.total_seconds}s budget exhausted "
            f"({deadline.elapsed:.3f}s elapsed)"
        )


class Deadline:
    """Tracks an absolute time budget for a sequence of retry attempts.

    Args:
        total_seconds: Maximum number of seconds allowed across all attempts.
        clock: Callable returning the current time (defaults to ``time.monotonic``).

    Raises:
        ValueError: If *total_seconds* is not a positive number.
    """

    def __init__(
        self,
        total_seconds: float,
        *,
        clock=time.monotonic,
    ) -> None:
        if total_seconds <= 0:
            raise ValueError("total_seconds must be a positive number")
        self._total = total_seconds
        self._clock = clock
        self._started_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> "Deadline":
        """Record the start time.  Idempotent after the first call."""
        if self._started_at is None:
            self._started_at = self._clock()
        return self

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total_seconds(self) -> float:
        return self._total

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since :meth:`start` was called (0 if not started)."""
        if self._started_at is None:
            return 0.0
        return self._clock() - self._started_at

    @property
    def remaining(self) -> float:
        """Seconds remaining in the deadline budget (never negative)."""
        return max(0.0, self._total - self.elapsed)

    @property
    def is_expired(self) -> bool:
        """``True`` when the deadline budget has been exhausted."""
        return self.elapsed >= self._total

    # ------------------------------------------------------------------
    # Guard helper
    # ------------------------------------------------------------------

    def check(self) -> None:
        """Raise :class:`DeadlineExceeded` if the deadline has passed."""
        if self.is_expired:
            raise DeadlineExceeded(self)

    def clamp_delay(self, delay: float) -> float:
        """Return *delay* clamped so it does not exceed the remaining budget."""
        return min(delay, self.remaining)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Deadline(total_seconds={self._total}, "
            f"elapsed={self.elapsed:.3f}, remaining={self.remaining:.3f})"
        )
