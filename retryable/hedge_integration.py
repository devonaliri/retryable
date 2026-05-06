"""Integration helpers that wire hedged calls into a RetryPolicy HookSet."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from retryable.hedge import hedged_call, HedgeTimeout
from retryable.hooks import HookSet
from retryable.context import RetryContext, AttemptRecord


def make_hedge_hookset(
    *,
    hedge_delay: float = 0.1,
    deadline_seconds: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> HookSet:
    """Return a HookSet that enables hedged execution.

    The *before* hook stores the hedge configuration in
    ``ctx.metadata['hedge']`` so that the decorator can pick it up.
    The *after* hook records whether the attempt was a hedge winner.

    In practice callers wrap the target function with :func:`hedged_wrap`
    rather than relying solely on hooks.
    """
    hs = HookSet()

    def before(ctx: RetryContext) -> None:
        ctx.metadata.setdefault("hedge", {
            "hedge_delay": hedge_delay,
            "deadline_seconds": deadline_seconds,
        })

    def after(ctx: RetryContext, record: AttemptRecord) -> None:
        if record.exception is not None and isinstance(record.exception, HedgeTimeout):
            ctx.metadata["hedge_timeout"] = True

    hs.before_attempt.append(before)
    hs.after_attempt.append(after)
    return hs


def hedged_wrap(
    fn: Callable[..., Any],
    *,
    hedge_delay: float = 0.1,
    deadline_seconds: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Callable[..., Any]:
    """Wrap *fn* so every call is executed as a hedged pair.

    Example
    -------
    >>> from retryable.hedge_integration import hedged_wrap
    >>> fast = hedged_wrap(my_slow_io_fn, hedge_delay=0.05)
    >>> result = fast(arg1, arg2)
    """
    deadline: Optional[float] = None

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        nonlocal deadline
        if deadline_seconds is not None:
            deadline = time.monotonic() + deadline_seconds
        return hedged_call(
            fn,
            args,
            kwargs,
            hedge_delay=hedge_delay,
            deadline=deadline,
            sleep_fn=sleep_fn,
        )

    wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
    wrapper.__name__ = getattr(fn, "__name__", "hedged")
    return wrapper
