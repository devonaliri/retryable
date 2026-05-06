"""Hooks that feed retry events into a :class:`~retryable.drain.RetryDrain`."""
from __future__ import annotations

from typing import Callable, List, Optional

from retryable.context import AttemptRecord, RetryContext
from retryable.drain import RetryDrain
from retryable.event_log import RetryEvent
from retryable.hooks import HookSet


def _make_event(kind: str, ctx: RetryContext, record: AttemptRecord) -> RetryEvent:
    exc = record.exception
    return RetryEvent(
        kind=kind,
        attempt=ctx.total_attempts,
        delay=record.delay,
        exception_type=type(exc).__name__ if exc else None,
        exception_message=str(exc) if exc else None,
        metadata=dict(ctx.metadata),
    )


def make_drain_hookset(
    sink: Callable[[List[RetryEvent]], None],
    *,
    batch_size: int = 50,
    max_capacity: Optional[int] = None,
    flush_on_success: bool = True,
) -> tuple[HookSet, RetryDrain]:
    """Create a :class:`~retryable.hooks.HookSet` wired to a new
    :class:`~retryable.drain.RetryDrain`.

    Parameters
    ----------
    sink:
        Callable that receives flushed event batches.
    batch_size:
        Forwarded to :class:`RetryDrain`.
    max_capacity:
        Forwarded to :class:`RetryDrain`.
    flush_on_success:
        When ``True`` the after-attempt hook triggers an immediate flush
        whenever the attempt succeeded (no exception).

    Returns
    -------
    tuple[HookSet, RetryDrain]
        The configured hook-set and the underlying drain instance.
    """
    drain = RetryDrain(sink, batch_size=batch_size, max_capacity=max_capacity)
    hooks = HookSet()

    def after(ctx: RetryContext, record: AttemptRecord) -> None:
        kind = "success" if record.exception is None else "failure"
        event = _make_event(kind, ctx, record)
        drain.put(event)
        if flush_on_success and record.exception is None:
            drain.flush()

    hooks.add_after(after)
    return hooks, drain
