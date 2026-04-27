"""High-level retry policy combining all retryable components."""

from __future__ import annotations

from typing import Callable, Optional, Tuple, Type

from retryable.backoff import exponential
from retryable.budget import RetryBudget
from retryable.circuit_breaker import CircuitBreaker
from retryable.decorator import retry
from retryable.jitter import full as full_jitter
from retryable.predicates import on_all_exceptions
from retryable.rate_limit import RateLimiter
from retryable.throttle import RetryThrottle
from retryable.timeout import RetryTimeout


def flaky(
    max_attempts: int = 3,
    *,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> Callable:
    """Convenience decorator for common flaky-function retry scenarios."""
    backoff = exponential(base=base_delay, max_delay=max_delay)
    jitter_fn = full_jitter if jitter else None
    predicate = on_all_exceptions if exceptions == (Exception,) else None

    kwargs = dict(
        max_attempts=max_attempts,
        backoff=backoff,
    )
    if jitter_fn:
        kwargs["jitter"] = jitter_fn
    if predicate:
        kwargs["predicate"] = predicate

    return retry(**kwargs)


class RetryPolicy:
    """Composable retry policy object.

    Combines backoff, jitter, predicate, budget, rate-limiter, throttle,
    circuit-breaker, and timeout into a single reusable policy that can be
    applied as a decorator or called directly.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff: Optional[Callable] = None,
        jitter: Optional[Callable] = None,
        predicate: Optional[Callable] = None,
        budget: Optional[RetryBudget] = None,
        rate_limiter: Optional[RateLimiter] = None,
        throttle: Optional[RetryThrottle] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        timeout: Optional[RetryTimeout] = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.backoff = backoff or exponential()
        self.jitter = jitter
        self.predicate = predicate or on_all_exceptions
        self.budget = budget
        self.rate_limiter = rate_limiter
        self.throttle = throttle
        self.circuit_breaker = circuit_breaker
        self.timeout = timeout

    def apply(self, fn: Callable) -> Callable:
        """Wrap *fn* with the configured retry logic."""
        kwargs: dict = dict(
            max_attempts=self.max_attempts,
            backoff=self.backoff,
            predicate=self.predicate,
        )
        if self.jitter:
            kwargs["jitter"] = self.jitter
        if self.budget:
            kwargs["budget"] = self.budget
        if self.throttle:
            kwargs["throttle"] = self.throttle
        if self.circuit_breaker:
            kwargs["circuit_breaker"] = self.circuit_breaker
        if self.timeout:
            kwargs["timeout"] = self.timeout
        return retry(**kwargs)(fn)

    def __call__(self, fn: Callable) -> Callable:
        """Allow the policy instance to be used directly as a decorator."""
        return self.apply(fn)
