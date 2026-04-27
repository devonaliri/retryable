"""RetryPolicy — assembles all retry components into a single configurable object."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple, Type

from retryable.backoff import exponential
from retryable.context import RetryContext
from retryable.exceptions import NonRetryableError, RetryLimitExceeded
from retryable.fallback import Fallback
from retryable.hooks import HookSet
from retryable.jitter import none as no_jitter
from retryable.predicates import on_all_exceptions


def flaky(
    max_attempts: int = 3,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> "RetryPolicy":
    """Convenience factory: simple exponential-backoff policy."""
    from retryable.predicates import on_exception

    return RetryPolicy(
        max_attempts=max_attempts,
        predicate=on_exception(*exceptions),
    )


class RetryPolicy:
    """Orchestrates retry logic, delegating to pluggable components."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff=None,
        jitter=None,
        predicate=None,
        hooks: Optional[HookSet] = None,
        fallback: Optional[Fallback] = None,
        budget=None,
        timeout=None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.max_attempts = max_attempts
        self.backoff = backoff or exponential()
        self.jitter = jitter or no_jitter()
        self.predicate = predicate or on_all_exceptions()
        self.hooks = hooks or HookSet()
        self.fallback = fallback
        self.budget = budget
        self.timeout = timeout

    def apply(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* with retry logic applied."""
        ctx = RetryContext()
        if self.timeout is not None:
            self.timeout.start()

        for attempt in range(1, self.max_attempts + 1):
            self.hooks.fire_before_attempt(ctx, attempt)
            delay = self.jitter(self.backoff(attempt))
            exc: Optional[BaseException] = None
            try:
                result = fn(*args, **kwargs)
                ctx.record_attempt(attempt, delay=delay, exception=None)
                self.hooks.fire_after_attempt(ctx, ctx.last)
                return result
            except BaseException as e:
                exc = e
                ctx.record_attempt(attempt, delay=delay, exception=e)
                self.hooks.fire_after_attempt(ctx, ctx.last)
                if not self.predicate(e):
                    raise NonRetryableError(e, attempts=attempt) from e
                if attempt < self.max_attempts:
                    if self.timeout is not None and self.timeout.is_expired():
                        break
                    if self.budget is not None and not self.budget.consume():
                        break
                    time.sleep(delay)

        last_exc = ctx.last.exception if ctx.last else None
        if self.fallback is not None and last_exc is not None:
            return self.fallback(last_exc, *args, **kwargs)
        raise RetryLimitExceeded(last_exc, attempts=ctx.total_attempts)

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Allow RetryPolicy to be used as a decorator."""
        import functools

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.apply(fn, *args, **kwargs)

        return wrapper
