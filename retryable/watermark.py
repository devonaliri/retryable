"""High-watermark tracking for retry attempt counts and delays."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Watermark:
    """Tracks the peak (maximum) values seen across retry calls."""

    _peak_attempts: int = field(default=0, init=False)
    _peak_delay: float = field(default=0.0, init=False)
    _peak_total_delay: float = field(default=0.0, init=False)
    _total_records: int = field(default=0, init=False)

    @property
    def peak_attempts(self) -> int:
        """Highest attempt count recorded in a single call."""
        return self._peak_attempts

    @property
    def peak_delay(self) -> float:
        """Highest single delay (seconds) recorded across all attempts."""
        return self._peak_delay

    @property
    def peak_total_delay(self) -> float:
        """Highest cumulative delay (seconds) recorded for a single call."""
        return self._peak_total_delay

    @property
    def total_records(self) -> int:
        """Total number of contexts recorded."""
        return self._total_records

    def record(self, attempts: int, delay: float, total_delay: float) -> None:
        """Update watermarks with values from a completed retry context."""
        if attempts < 0:
            raise ValueError("attempts must be non-negative")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        if total_delay < 0:
            raise ValueError("total_delay must be non-negative")
        self._peak_attempts = max(self._peak_attempts, attempts)
        self._peak_delay = max(self._peak_delay, delay)
        self._peak_total_delay = max(self._peak_total_delay, total_delay)
        self._total_records += 1

    def reset(self) -> None:
        """Reset all watermarks to zero."""
        self._peak_attempts = 0
        self._peak_delay = 0.0
        self._peak_total_delay = 0.0
        self._total_records = 0

    def as_dict(self) -> dict:
        return {
            "peak_attempts": self._peak_attempts,
            "peak_delay": self._peak_delay,
            "peak_total_delay": self._peak_total_delay,
            "total_records": self._total_records,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Watermark(peak_attempts={self._peak_attempts}, "
            f"peak_delay={self._peak_delay}, "
            f"peak_total_delay={self._peak_total_delay})"
        )
