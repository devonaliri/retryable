"""Debounce guard — suppress retries that arrive faster than a minimum interval."""

from __future__ import annotations

import time
from typing import Callable, Optional


class DebounceViolation(Exception):
    """Raised when a retry attempt is made before the debounce interval has elapsed."""

    def __init__(self, wait_remaining: float) -> None:
        self.wait_remaining = wait_remaining
        super().__init__(
            f"Retry attempted too soon; {wait_remaining:.3f}s remaining in debounce window."
        )


class RetryDebounce:
    """Ensures retry attempts are spaced at least *min_interval* seconds apart.

    Parameters
    ----------
    min_interval:
        Minimum number of seconds that must elapse between consecutive retry
        attempts.  Must be a positive number.
    clock:
        Optional callable returning the current time as a float (defaults to
        :func:`time.monotonic`).  Useful for deterministic testing.
    """

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min_interval <= 0:
            raise ValueError("min_interval must be a positive number.")
        self._min_interval = min_interval
        self._clock = clock
        self._last_attempt: Optional[float] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def min_interval(self) -> float:
        """The configured minimum interval in seconds."""
        return self._min_interval

    @property
    def last_attempt(self) -> Optional[float]:
        """Timestamp of the most recent allowed attempt, or *None* if never called."""
        return self._last_attempt

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Return *True* if enough time has passed since the last attempt.

        Calling this method does **not** record the attempt; call
        :meth:`record` explicitly (or use :meth:`check` which does both).
        """
        if self._last_attempt is None:
            return True
        return (self._clock() - self._last_attempt) >= self._min_interval

    def record(self) -> None:
        """Mark the current moment as the latest attempt timestamp."""
        self._last_attempt = self._clock()

    def check(self) -> None:
        """Assert that the debounce interval has elapsed, then record the attempt.

        Raises :class:`DebounceViolation` if the interval has *not* elapsed.
        """
        if self._last_attempt is not None:
            elapsed = self._clock() - self._last_attempt
            if elapsed < self._min_interval:
                raise DebounceViolation(self._min_interval - elapsed)
        self.record()

    def reset(self) -> None:
        """Clear the last-attempt timestamp, as if no attempt has ever been made."""
        self._last_attempt = None
