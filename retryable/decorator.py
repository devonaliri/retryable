"""Core retry decorator."""

import time
from functools import wraps
from typing import Callable, Optional, Type, Tuple

from .backoff import constant
from .context import RetryContext
from .exceptions import RetryLimitExceeded, NonRetryableError
from .hooks import HookSet
from .predicates import on_all_exceptions
from .budget import RetryBudget


def retry(
    max_attempts: int = 3,
    backoff=None,
    predicate=None,
    on_retry=None,
    exceptions: Optional[Tuple[Type[BaseException], ...]] = None,
    budget: Optional[RetryBudget] = None,
):
    """Decorator factory that wraps a callable with configurable retry logic.

    Args:
        max_attempts: Maximum number of times the function may be called in
                      total (first attempt + retries).  Must be >= 1.
        backoff:      A callable ``(attempt: int) -> float`` returning the
                      number of seconds to wait before the next attempt.
                      Defaults to :func:`retryable.backoff.constant` (0 s).
        predicate:    A callable ``(exc: Exception) -> bool`` that decides
                      whether the exception should trigger a retry.  Defaults
                      to :func:`retryable.predicates.on_all_exceptions`.
        on_retry:     A :class:`retryable.hooks.HookSet` or a single hook
                      callable fired before each retry attempt.
        exceptions:   Shorthand for ``predicate=on_exception(*exceptions)``.
                      Ignored when *predicate* is also supplied.
        budget:       Optional :class:`retryable.budget.RetryBudget`.  Each
                      failed attempt consumes one token; when the budget is
                      exhausted retrying stops regardless of *max_attempts*.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    if backoff is None:
        backoff = constant(0)

    if predicate is None:
        if exceptions:
            from .predicates import on_exception
            predicate = on_exception(*exceptions)
        else:
            predicate = on_all_exceptions()

    hooks: HookSet
    if isinstance(on_retry, HookSet):
        hooks = on_retry
    elif callable(on_retry):
        hooks = HookSet(before=[on_retry])
    else:
        hooks = HookSet()

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = RetryContext(func=fn)
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                delay = backoff(attempt)
                hooks.fire_before_attempt(ctx, attempt)

                try:
                    result = fn(*args, **kwargs)
                    ctx.record_attempt(attempt=attempt, delay=delay, exception=None)
                    if budget is not None:
                        budget.record_success()
                    return result
                except Exception as exc:
                    last_exc = exc
                    ctx.record_attempt(attempt=attempt, delay=delay, exception=exc)
                    hooks.fire_after_attempt(ctx, ctx.last_record)

                    if not predicate(exc):
                        raise NonRetryableError(exc, ctx) from exc

                    if attempt == max_attempts:
                        break

                    if budget is not None and not budget.consume():
                        break

                    if delay > 0:
                        time.sleep(delay)

            raise RetryLimitExceeded(last_exc, ctx)

        return wrapper

    return decorator
