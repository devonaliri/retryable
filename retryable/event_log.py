"""Structured event log for retry attempts.

Provides an append-only, in-memory log of retry events that can be queried,
filtered, and exported.  Useful for post-mortem analysis and testing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Optional

from retryable.context import AttemptRecord, RetryContext


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryEvent:
    """A single entry in the event log."""

    #: Monotonic timestamp (seconds) when the event was recorded.
    timestamp: float
    #: Logical event kind: ``"before"``, ``"success"``, or ``"failure"``.
    kind: str
    #: Name of the callable being retried.
    fn_name: str
    #: 1-based attempt number at the time of the event.
    attempt: int
    #: Delay (seconds) that was applied *before* this attempt (0 for ``"before"`` events).
    delay: float
    #: Fully-qualified exception type name, or ``None`` on success.
    exception_type: Optional[str]
    #: Arbitrary metadata copied from the context at the time of recording.
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def as_dict(self) -> dict:
        """Return a plain-dict representation suitable for serialisation."""
        return {
            "timestamp": self.timestamp,
            "kind": self.kind,
            "fn_name": self.fn_name,
            "attempt": self.attempt,
            "delay": self.delay,
            "exception_type": self.exception_type,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Log container
# ---------------------------------------------------------------------------

class RetryEventLog:
    """Append-only in-memory log of :class:`RetryEvent` objects.

    Example usage with hooks::

        log = RetryEventLog()
        hookset = make_event_log_hookset(log)
        policy = RetryPolicy(..., hooks=hookset)
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._events: List[RetryEvent] = []

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(self, event: RetryEvent) -> None:
        """Append *event* to the log."""
        self._events.append(event)

    def _make_event(
        self,
        kind: str,
        ctx: RetryContext,
        record: Optional[AttemptRecord] = None,
    ) -> RetryEvent:
        attempt = ctx.total_attempts
        delay = record.delay if record is not None else 0.0
        exc_type: Optional[str] = None
        if record is not None and record.exception is not None:
            t = type(record.exception)
            exc_type = f"{t.__module__}.{t.__qualname__}"
        return RetryEvent(
            timestamp=self._clock(),
            kind=kind,
            fn_name=getattr(ctx, "fn_name", "unknown"),
            attempt=attempt,
            delay=delay,
            exception_type=exc_type,
            metadata=dict(getattr(ctx, "metadata", {})),
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @property
    def events(self) -> List[RetryEvent]:
        """All recorded events in insertion order (read-only copy)."""
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def filter(self, *, kind: Optional[str] = None, fn_name: Optional[str] = None) -> List[RetryEvent]:
        """Return events matching the supplied criteria.

        Parameters
        ----------
        kind:
            If given, only events whose ``kind`` equals this value are returned.
        fn_name:
            If given, only events for this function name are returned.
        """
        results: Iterable[RetryEvent] = self._events
        if kind is not None:
            results = (e for e in results if e.kind == kind)
        if fn_name is not None:
            results = (e for e in results if e.fn_name == fn_name)
        return list(results)

    def failures(self) -> List[RetryEvent]:
        """Convenience: return all failure events."""
        return self.filter(kind="failure")

    def successes(self) -> List[RetryEvent]:
        """Convenience: return all success events."""
        return self.filter(kind="success")

    def clear(self) -> None:
        """Remove all recorded events."""
        self._events.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return f"RetryEventLog(events={len(self._events)})"


# ---------------------------------------------------------------------------
# Hook factory
# ---------------------------------------------------------------------------

def make_event_log_hookset(log: RetryEventLog) -> Any:
    """Return a :class:`~retryable.hooks.HookSet` that writes to *log*.

    The returned hook-set records:

    * a ``"before"`` event before every attempt,
    * a ``"success"`` event when an attempt succeeds,
    * a ``"failure"`` event when an attempt raises.
    """
    from retryable.hooks import HookSet

    hs = HookSet()

    def before(ctx: RetryContext) -> None:  # noqa: D401
        log.record(log._make_event("before", ctx))

    def after(ctx: RetryContext, record: AttemptRecord) -> None:
        kind = "success" if record.succeeded else "failure"
        log.record(log._make_event(kind, ctx, record))

    hs.fire_before_attempt = before  # type: ignore[method-assign]
    hs.fire_after_attempt = after    # type: ignore[method-assign]
    return hs
