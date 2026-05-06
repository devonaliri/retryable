"""Hooks that integrate CorrelationTracker with the retry decorator.

Usage::

    from retryable.correlation import CorrelationTracker
    from retryable.correlation_integration import make_correlation_hookset
    from retryable.hooks import HookSet
    from retryable import retry

    tracker = CorrelationTracker()
    hooks = make_correlation_hookset(tracker)

    @retry(max_attempts=3, hooks=hooks)
    def my_fn(): ...
"""
from __future__ import annotations

from typing import Optional

from retryable.context import AttemptRecord, RetryContext
from retryable.correlation import CorrelationEntry, CorrelationTracker
from retryable.hooks import HookSet

_ENTRY_ATTR = "_correlation_entry"


def make_correlation_hookset(tracker: CorrelationTracker) -> HookSet:
    """Return a HookSet that stamps correlation/attempt IDs onto contexts."""

    def before(ctx: RetryContext) -> None:
        # On the very first attempt create a new correlation entry.
        if ctx.total_attempts == 0:
            entry: CorrelationEntry = tracker.new_call()
            setattr(ctx, _ENTRY_ATTR, entry)
        else:
            entry = getattr(ctx, _ENTRY_ATTR, None)
            if entry is None:
                entry = tracker.new_call()
                setattr(ctx, _ENTRY_ATTR, entry)
        attempt_id = entry.add_attempt()
        # Expose IDs via context metadata for downstream hooks / logging.
        ctx.metadata["correlation_id"] = entry.correlation_id
        ctx.metadata["attempt_id"] = attempt_id

    def after(ctx: RetryContext, record: AttemptRecord) -> None:  # noqa: ARG001
        pass  # Nothing extra needed after each attempt.

    hs = HookSet()
    hs.before_attempt.append(before)
    hs.after_attempt.append(after)
    return hs
