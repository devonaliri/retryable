"""Hooks that wire RetryTrace into a HookSet so every policy call is traced."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from retryable.hooks import HookSet
from retryable.trace import RetryTrace

# Key used to stash the active trace in context metadata
_TRACE_KEY = "_retry_trace"


def _get_or_create_trace(ctx) -> RetryTrace:
    """Return the trace stored in *ctx.metadata*, creating one if absent."""
    if _TRACE_KEY not in ctx.metadata:
        ctx.metadata[_TRACE_KEY] = RetryTrace()
    return ctx.metadata[_TRACE_KEY]  # type: ignore[return-value]


def make_trace_hookset(
    on_trace_complete: Optional[Callable[[RetryTrace], None]] = None,
) -> HookSet:
    """Return a HookSet that records a RetrySpan for every attempt.

    Parameters
    ----------
    on_trace_complete:
        Optional callback invoked with the finished :class:`RetryTrace` after
        the *last* attempt (succeeded or not).  Useful for exporting traces.
    """
    hooks = HookSet()

    def before(ctx) -> None:  # noqa: ANN001
        # Ensure the trace object exists before the attempt fires.
        _get_or_create_trace(ctx)

    def after(ctx, record) -> None:  # noqa: ANN001
        trace = _get_or_create_trace(ctx)
        exc_type = (
            type(record.exception).__name__ if record.exception else None
        )
        trace.add_span(
            attempt_number=ctx.total_attempts,
            succeeded=record.succeeded,
            exception_type=exc_type,
        )
        # Fire the completion callback once the call is truly finished.
        if on_trace_complete is not None and (
            record.succeeded or not ctx.will_retry
        ):
            on_trace_complete(trace)

    hooks.fire_before_attempt  # warm attribute access
    hooks._before.append(before)  # type: ignore[attr-defined]
    hooks._after.append(after)    # type: ignore[attr-defined]
    return hooks
