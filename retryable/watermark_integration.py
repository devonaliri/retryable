"""Hooks that feed RetryContext data into a Watermark instance."""
from __future__ import annotations

from typing import Callable

from retryable.context import AttemptRecord, RetryContext
from retryable.hooks import HookSet
from retryable.watermark import Watermark


def _total_delay(ctx: RetryContext) -> float:
    """Sum of all delays recorded in *ctx*."""
    return sum(r.delay for r in ctx.history)


def _peak_single_delay(ctx: RetryContext) -> float:
    """Largest single delay recorded in *ctx*."""
    delays = [r.delay for r in ctx.history]
    return max(delays) if delays else 0.0


def make_watermark_hookset(watermark: Watermark) -> HookSet:
    """Return a :class:`HookSet` that updates *watermark* after every call.

    Only the *after_attempt* hook is used; we update on every attempt so that
    the watermark reflects the running peak even for long-running operations.
    """
    hs = HookSet()

    def after(ctx: RetryContext, record: AttemptRecord) -> None:  # noqa: D401
        watermark.record(
            attempts=ctx.total_attempts,
            delay=record.delay,
            total_delay=_total_delay(ctx),
        )

    hs.after_attempt.append(after)
    return hs
