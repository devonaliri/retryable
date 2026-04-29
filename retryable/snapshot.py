"""Snapshot captures a point-in-time summary of retry state for diagnostics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from retryable.context import RetryContext


@dataclass(frozen=True)
class RetrySnapshot:
    """Immutable point-in-time view of a RetryContext."""

    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    last_delay: float
    last_exception: Optional[BaseException]
    elapsed: float
    captured_at: float = field(default_factory=time.monotonic)

    @property
    def is_healthy(self) -> bool:
        """True when no failures have been recorded yet."""
        return self.failed_attempts == 0

    @property
    def failure_rate(self) -> Optional[float]:
        """Fraction of attempts that failed, or None if no attempts made."""
        if self.total_attempts == 0:
            return None
        return self.failed_attempts / self.total_attempts

    def __str__(self) -> str:
        return (
            f"RetrySnapshot(attempts={self.total_attempts}, "
            f"failed={self.failed_attempts}, "
            f"elapsed={self.elapsed:.3f}s, "
            f"healthy={self.is_healthy})"
        )


def take_snapshot(ctx: RetryContext) -> RetrySnapshot:
    """Capture the current state of *ctx* as an immutable snapshot."""
    records = ctx.history()
    successful = sum(1 for r in records if r.succeeded)
    failed = len(records) - successful
    last_delay = records[-1].delay if records else 0.0
    last_exc = records[-1].exception if records else None
    elapsed = ctx.elapsed()
    return RetrySnapshot(
        total_attempts=ctx.total_attempts,
        successful_attempts=successful,
        failed_attempts=failed,
        last_delay=last_delay,
        last_exception=last_exc,
        elapsed=elapsed,
    )
