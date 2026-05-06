"""Aggregates retry statistics across multiple named operations."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from retryable.context import RetryContext


@dataclass
class OperationStats:
    """Accumulated statistics for a single named operation."""
    name: str
    total_calls: int = 0
    total_attempts: int = 0
    total_failures: int = 0
    total_successes: int = 0
    exception_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> Optional[float]:
        """Fraction of calls that ultimately succeeded, or None if no calls."""
        if self.total_calls == 0:
            return None
        return self.total_successes / self.total_calls

    @property
    def average_attempts(self) -> Optional[float]:
        """Average attempts per call, or None if no calls."""
        if self.total_calls == 0:
            return None
        return self.total_attempts / self.total_calls

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"OperationStats(name={self.name!r}, calls={self.total_calls}, "
            f"success_rate={self.success_rate})"
        )


class RetryAggregator:
    """Collect and query retry statistics keyed by operation name."""

    def __init__(self) -> None:
        self._stats: Dict[str, OperationStats] = {}

    def record(self, name: str, ctx: RetryContext) -> None:
        """Update aggregated stats for *name* from a completed RetryContext."""
        if name not in self._stats:
            self._stats[name] = OperationStats(name=name)

        stats = self._stats[name]
        stats.total_calls += 1
        stats.total_attempts += ctx.total_attempts

        last = ctx.last_attempt
        if last is not None and last.succeeded:
            stats.total_successes += 1
        else:
            stats.total_failures += 1

        for attempt in ctx.attempts:
            if attempt.exception is not None:
                exc_name = type(attempt.exception).__name__
                stats.exception_counts[exc_name] = (
                    stats.exception_counts.get(exc_name, 0) + 1
                )

    def get(self, name: str) -> Optional[OperationStats]:
        """Return stats for *name*, or None if never recorded."""
        return self._stats.get(name)

    @property
    def operation_names(self) -> List[str]:
        """Sorted list of all tracked operation names."""
        return sorted(self._stats)

    def reset(self, name: Optional[str] = None) -> None:
        """Clear stats for *name*, or all operations when *name* is None."""
        if name is None:
            self._stats.clear()
        else:
            self._stats.pop(name, None)
