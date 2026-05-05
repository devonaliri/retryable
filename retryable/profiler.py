"""Retry profiler: collects per-call timing and attempt statistics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CallProfile:
    """Timing and attempt data for a single decorated call."""

    total_attempts: int
    succeeded: bool
    total_elapsed: float  # seconds
    attempt_durations: List[float] = field(default_factory=list)

    @property
    def average_attempt_duration(self) -> Optional[float]:
        if not self.attempt_durations:
            return None
        return sum(self.attempt_durations) / len(self.attempt_durations)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CallProfile(attempts={self.total_attempts}, "
            f"succeeded={self.succeeded}, "
            f"elapsed={self.total_elapsed:.4f}s)"
        )


class RetryProfiler:
    """Accumulates CallProfile entries produced by profiling hooks."""

    def __init__(self) -> None:
        self._profiles: List[CallProfile] = []

    def record(self, profile: CallProfile) -> None:
        self._profiles.append(profile)

    @property
    def profiles(self) -> List[CallProfile]:
        return list(self._profiles)

    @property
    def total_calls(self) -> int:
        return len(self._profiles)

    @property
    def success_rate(self) -> Optional[float]:
        if not self._profiles:
            return None
        return sum(1 for p in self._profiles if p.succeeded) / len(self._profiles)

    def average_elapsed(self) -> Optional[float]:
        if not self._profiles:
            return None
        return sum(p.total_elapsed for p in self._profiles) / len(self._profiles)

    def reset(self) -> None:
        self._profiles.clear()
