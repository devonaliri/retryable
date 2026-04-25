"""Metrics collection for retry attempts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from retryable.context import RetryContext


@dataclass
class RetryMetrics:
    """Aggregated metrics collected over the lifetime of a retryable call."""

    total_calls: int = 0
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    exception_counts: Dict[str, int] = field(default_factory=dict)
    attempt_counts: List[int] = field(default_factory=list)

    def record(self, ctx: RetryContext) -> None:
        """Record the outcome of a single retryable call from its context."""
        self.total_calls += 1
        n = ctx.total_attempts()
        self.total_attempts += n
        self.attempt_counts.append(n)

        last = ctx.last_attempt()
        if last is not None and last.succeeded():
            self.total_successes += 1
        else:
            self.total_failures += 1

        for record in ctx.history:
            if record.exception is not None:
                name = type(record.exception).__name__
                self.exception_counts[name] = self.exception_counts.get(name, 0) + 1

    @property
    def success_rate(self) -> Optional[float]:
        """Fraction of calls that ultimately succeeded (0.0–1.0), or None if no calls."""
        if self.total_calls == 0:
            return None
        return self.total_successes / self.total_calls

    @property
    def average_attempts(self) -> Optional[float]:
        """Mean number of attempts per call, or None if no calls."""
        if not self.attempt_counts:
            return None
        return self.total_attempts / len(self.attempt_counts)

    def reset(self) -> None:
        """Clear all collected metrics."""
        self.total_calls = 0
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.exception_counts.clear()
        self.attempt_counts.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetryMetrics(calls={self.total_calls}, "
            f"successes={self.total_successes}, "
            f"failures={self.total_failures}, "
            f"avg_attempts={self.average_attempts})"
        )
