"""Probabilistic sampling for retry telemetry and tracing."""
from __future__ import annotations

import random
from typing import Callable, Optional


class RetrySampler:
    """Decides whether a given retry call should be fully observed/traced.

    Useful when retry volume is high and you only want to record a fraction
    of calls for metrics or logging purposes.

    Args:
        rate: Probability in the range (0.0, 1.0] that a call is sampled.
        rng:  Optional callable returning a float in [0, 1).  Defaults to
              ``random.random``.  Inject a deterministic function in tests.
    """

    def __init__(
        self,
        rate: float = 1.0,
        rng: Optional[Callable[[], float]] = None,
    ) -> None:
        if not (0.0 < rate <= 1.0):
            raise ValueError(f"rate must be in (0, 1], got {rate!r}")
        self._rate = rate
        self._rng = rng or random.random
        self._total = 0
        self._sampled = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rate(self) -> float:
        """Configured sampling rate."""
        return self._rate

    @property
    def total_calls(self) -> int:
        """Total number of calls evaluated."""
        return self._total

    @property
    def sampled_calls(self) -> int:
        """Number of calls that were sampled."""
        return self._sampled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_sample(self) -> bool:
        """Return True if the current call should be sampled."""
        self._total += 1
        result = self._rng() < self._rate
        if result:
            self._sampled += 1
        return result

    def effective_rate(self) -> Optional[float]:
        """Observed sampling rate so far, or None if no calls yet."""
        if self._total == 0:
            return None
        return self._sampled / self._total

    def reset(self) -> None:
        """Reset counters without changing the configured rate."""
        self._total = 0
        self._sampled = 0

    def update_rate(self, rate: float) -> None:
        """Update the sampling rate without resetting counters.

        Args:
            rate: New probability in the range (0.0, 1.0].

        Raises:
            ValueError: If *rate* is outside the allowed range.
        """
        if not (0.0 < rate <= 1.0):
            raise ValueError(f"rate must be in (0, 1], got {rate!r}")
        self._rate = rate

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetrySampler(rate={self._rate!r}, "
            f"total={self._total}, sampled={self._sampled})"
        )
