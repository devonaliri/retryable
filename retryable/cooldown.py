"""Cooldown: enforces a minimum wait period between retry bursts."""
from __future__ import annotations

import time
from typing import Callable, Optional


class CooldownViolation(Exception):
    """Raised when a call is attempted before the cooldown period has elapsed."""


class RetryCooldown:
    """Tracks the end-of-burst timestamp and enforces a cooldown window.

    After a burst of retries completes (regardless of outcome), no new
    attempt is allowed until ``cooldown_seconds`` have elapsed.

    Args:
        cooldown_seconds: How long to wait after a burst before allowing
            another attempt.  Must be a positive number.
        clock: Optional callable returning the current time as a float
            (seconds since epoch).  Defaults to :func:`time.monotonic`.
    """

    def __init__(
        self,
        cooldown_seconds: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if cooldown_seconds <= 0:
            raise ValueError(
                f"cooldown_seconds must be positive, got {cooldown_seconds!r}"
            )
        self._cooldown = cooldown_seconds
        self._clock: Callable[[], float] = clock or time.monotonic
        self._burst_ended_at: Optional[float] = None

    @property
    def cooldown_seconds(self) -> float:
        """The configured cooldown window in seconds."""
        return self._cooldown

    @property
    def active(self) -> bool:
        """``True`` if the cooldown window is still in effect."""
        if self._burst_ended_at is None:
            return False
        return (self._clock() - self._burst_ended_at) < self._cooldown

    @property
    def remaining(self) -> float:
        """Seconds remaining in the current cooldown window (0.0 if inactive)."""
        if self._burst_ended_at is None:
            return 0.0
        elapsed = self._clock() - self._burst_ended_at
        remaining = self._cooldown - elapsed
        return max(0.0, remaining)

    def record_burst_end(self) -> None:
        """Mark the current moment as the end of a retry burst."""
        self._burst_ended_at = self._clock()

    def allow(self) -> bool:
        """Return ``True`` if a new attempt is permitted right now."""
        return not self.active

    def reset(self) -> None:
        """Clear the cooldown state entirely."""
        self._burst_ended_at = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetryCooldown(cooldown_seconds={self._cooldown!r}, "
            f"active={self.active!r})"
        )
