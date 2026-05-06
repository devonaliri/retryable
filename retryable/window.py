"""Sliding-window failure tracker for retryable.

Tracks attempt outcomes within a rolling time window so callers can
decide whether a function is behaving poorly *recently* rather than
across its entire lifetime.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Optional


@dataclass
class _Entry:
    timestamp: float
    failed: bool


class SlidingWindow:
    """Count successes and failures within a rolling time window.

    Parameters
    ----------
    window_seconds:
        Width of the rolling window in seconds.  Must be positive.
    clock:
        Zero-argument callable that returns the current time as a float
        (defaults to :func:`time.monotonic`).
    """

    def __init__(
        self,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = window_seconds
        self._clock = clock
        self._entries: Deque[_Entry] = deque()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def window_seconds(self) -> float:
        return self._window

    def record_success(self) -> None:
        """Record a successful attempt at the current time."""
        self._entries.append(_Entry(self._clock(), failed=False))

    def record_failure(self) -> None:
        """Record a failed attempt at the current time."""
        self._entries.append(_Entry(self._clock(), failed=True))

    def total(self) -> int:
        """Total attempts within the current window."""
        self._evict()
        return len(self._entries)

    def failures(self) -> int:
        """Failed attempts within the current window."""
        self._evict()
        return sum(1 for e in self._entries if e.failed)

    def successes(self) -> int:
        """Successful attempts within the current window."""
        self._evict()
        return sum(1 for e in self._entries if not e.failed)

    def failure_rate(self) -> Optional[float]:
        """Fraction of attempts that failed, or *None* if the window is empty."""
        t = self.total()
        return None if t == 0 else self.failures() / t

    def reset(self) -> None:
        """Discard all recorded entries."""
        self._entries.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict(self) -> None:
        """Remove entries that have fallen outside the window."""
        cutoff = self._clock() - self._window
        while self._entries and self._entries[0].timestamp <= cutoff:
            self._entries.popleft()
