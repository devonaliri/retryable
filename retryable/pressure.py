"""Retry pressure tracker — monitors cumulative retry load across calls."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PressureSnapshot:
    """Point-in-time view of retry pressure."""
    total_retries: int
    active_calls: int
    pressure_ratio: float  # retries / (calls * max_retries)
    sampled_at: float = field(default_factory=time.monotonic)

    def is_elevated(self, threshold: float = 0.5) -> bool:
        """Return True when pressure_ratio exceeds *threshold*."""
        return self.pressure_ratio > threshold

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"PressureSnapshot(ratio={self.pressure_ratio:.2f}, "
            f"retries={self.total_retries}, active={self.active_calls})"
        )


class RetryPressure:
    """Thread-safe accumulator of retry pressure across concurrent calls."""

    def __init__(self, max_retries: int = 3) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self._max_retries = max_retries
        self._lock = threading.Lock()
        self._total_retries: int = 0
        self._active_calls: int = 0
        self._total_calls: int = 0

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def enter_call(self) -> None:
        """Signal that a new retryable call has started."""
        with self._lock:
            self._active_calls += 1
            self._total_calls += 1

    def exit_call(self) -> None:
        """Signal that a retryable call has finished."""
        with self._lock:
            self._active_calls = max(0, self._active_calls - 1)

    def record_retry(self) -> None:
        """Increment the retry counter by one."""
        with self._lock:
            self._total_retries += 1

    def snapshot(self) -> PressureSnapshot:
        """Return a consistent snapshot of current pressure."""
        with self._lock:
            calls = max(1, self._total_calls)
            ratio = self._total_retries / (calls * self._max_retries)
            return PressureSnapshot(
                total_retries=self._total_retries,
                active_calls=self._active_calls,
                pressure_ratio=min(1.0, ratio),
            )

    def reset(self) -> None:
        """Clear all counters."""
        with self._lock:
            self._total_retries = 0
            self._active_calls = 0
            self._total_calls = 0
