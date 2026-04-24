"""Core retry decorator implementation."""
import time
from functools import wraps
from typing import Callable, Optional, Type, Tuple

from retryable.backoff import constant
from retryable.context import RetryContext, AttemptRecord
from retryable.exceptions import RetryLimitExceeded, NonRetryableError
from retryable.hooks import HookSet, EMPTY_HOOKS
from retryable.predicates import on_all_exceptions


def retry(
    max_attempts: int = 3,
    backoff: Callable[[int], float] = constant(1.0),
    predicate: Callable[[Exception], bool] = on_all_exceptions,
    reraise: bool = False,
    hooks: HookSet = EMPTY_HOOKS,
) -> Callable:
    """Decorator factory that wraps a function with configurable retry logic.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        backoff: Callable(attempt_number) -> seconds to wait.
        predicate: Callable(exception) -> bool; True means retry.
        reraise: If True, reraise the last exception instead of RetryLimitExceeded.
        hooks: HookSet with optional lifecycle callbacks.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = RetryContext(func=fn, max_attempts=max_attempts)
            last_exc: Optional[Exception] = None

            for attempt_number in range(1, max_attempts + 1):
                delay = backoff(attempt_number)
                record = AttemptRecord(attempt_number=attempt_number, delay=delay)
                hooks.fire_before_attempt(ctx, record)

                try:
                    result = fn(*args, **kwargs)
                    record.mark_success()
                    ctx.record_attempt(record)
                    hooks.fire_after_attempt(ctx, record)
                    hooks.fire_on_success(ctx, record)
                    return result
                except Exception as exc:
                    record.mark_failure(exc)
                    ctx.record_attempt(record)
                    hooks.fire_after_attempt(ctx, record)
                    last_exc = exc

                    if not predicate(exc):
                        hooks.fire_on_failure(ctx, record)
                        raise NonRetryableError(
                            f"Non-retryable exception: {exc!r}",
                            last_exception=exc,
                            attempts=attempt_number,
                        ) from exc

                    hooks.fire_on_failure(ctx, record)

                    if attempt_number < max_attempts:
                        time.sleep(delay)

            if reraise and last_exc is not None:
                raise last_exc

            raise RetryLimitExceeded(
                last_exception=last_exc,
                attempts=max_attempts,
            )

        return wrapper

    return decorator
