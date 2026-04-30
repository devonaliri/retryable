"""Waiter — sleep abstraction for retry delays with optional dry-run mode."""

from __future__ import annotations

import time
from typing import Callable, List


class Waiter:
    """Encapsulates the sleep mechanism used between retry attempts.

    Allows tests and callers to inject a custom sleep function or run in
    dry-run mode where no actual sleeping occurs but delays are recorded.
    """

    def __init__(
        self,
        sleep_fn: Callable[[float], None] = time.sleep,
        dry_run: bool = False,
    ) -> None:
        if not callable(sleep_fn):
            raise TypeError("sleep_fn must be callable")
        self._sleep_fn = sleep_fn
        self._dry_run = dry_run
        self._recorded: List[float] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def dry_run(self) -> bool:
        """Return True if this waiter will skip actual sleeping."""
        return self._dry_run

    @property
    def recorded_delays(self) -> List[float]:
        """Return a copy of all delays that were requested so far."""
        return list(self._recorded)

    @property
    def total_waited(self) -> float:
        """Return the sum of all recorded delays."""
        return sum(self._recorded)

    def wait(self, seconds: float) -> None:
        """Sleep for *seconds* (or record the delay in dry-run mode).

        Args:
            seconds: Duration to wait.  Values <= 0 are silently ignored.
        """
        if seconds <= 0:
            return
        self._recorded.append(seconds)
        if not self._dry_run:
            self._sleep_fn(seconds)

    def reset(self) -> None:
        """Clear the recorded delay history."""
        self._recorded.clear()

    def __repr__(self) -> str:
        return (
            f"Waiter(dry_run={self._dry_run!r}, "
            f"total_waited={self.total_waited:.3f}s, "
            f"calls={len(self._recorded)})"
        )


# ---------------------------------------------------------------------------
# Module-level convenience instance (real sleep, not dry-run)
# ---------------------------------------------------------------------------

default_waiter: Waiter = Waiter()
