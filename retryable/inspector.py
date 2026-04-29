"""Inspector provides a high-level diagnostic interface over RetryContext.

It wraps a context and exposes snapshot-based helpers useful for logging,
monitoring hooks, and circuit-breaker integrations.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from retryable.context import RetryContext
from retryable.snapshot import RetrySnapshot, take_snapshot


SnapshotCallback = Callable[[RetrySnapshot], None]


class Inspector:
    """Wraps a RetryContext and provides diagnostic utilities."""

    def __init__(self, ctx: RetryContext) -> None:
        self._ctx = ctx
        self._snapshots: List[RetrySnapshot] = []
        self._callbacks: List[SnapshotCallback] = []

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def capture(self) -> RetrySnapshot:
        """Take a snapshot of the current context state and store it."""
        snap = take_snapshot(self._ctx)
        self._snapshots.append(snap)
        for cb in self._callbacks:
            cb(snap)
        return snap

    @property
    def snapshots(self) -> List[RetrySnapshot]:
        """All snapshots captured so far (oldest first)."""
        return list(self._snapshots)

    def latest(self) -> Optional[RetrySnapshot]:
        """Return the most recently captured snapshot, or None."""
        return self._snapshots[-1] if self._snapshots else None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_snapshot(self, callback: SnapshotCallback) -> None:
        """Register *callback* to be invoked each time a snapshot is captured."""
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Convenience diagnostics
    # ------------------------------------------------------------------

    def is_degraded(self, threshold: float = 0.5) -> bool:
        """True when the latest snapshot's failure rate exceeds *threshold*."""
        snap = self.latest()
        if snap is None or snap.failure_rate is None:
            return False
        return snap.failure_rate > threshold

    def summary(self) -> str:
        """Human-readable one-line summary based on the latest snapshot."""
        snap = self.latest()
        if snap is None:
            return "Inspector(no snapshots)"
        return (
            f"Inspector(total={snap.total_attempts}, "
            f"failed={snap.failed_attempts}, "
            f"rate={snap.failure_rate:.0%} failure, "
            f"elapsed={snap.elapsed:.3f}s)"
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Inspector(snapshots={len(self._snapshots)})"
