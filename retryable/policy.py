"""RetryPolicy — a composable configuration object that bundles all retry
behaviour into a single, reusable unit.

Typical usage::

    from retryable.policy import RetryPolicy
    from retryable import backoff, jitter

    policy = RetryPolicy(
        max_attempts=5,
        backoff=backoff.exponential(base=0.5, multiplier=2),
        jitter=jitter.full,
        predicate=on_exception(ValueError, IOError),
    )

    @policy.retry
    def flaky():
        ...
"""

from __future__ import annotations

from typing import Callable, Optional

from retryable import backoff as _backoff
from retryable import jitter as _jitter
from retryable.decorator import retry
from retryable.predicates import on_all_exceptions


class RetryPolicy:
    """Encapsulates a complete retry configuration.

    Parameters
    ----------
    max_attempts:
        Maximum number of times the decorated callable will be invoked
        (including the first attempt).  Must be >= 1.
    backoff:
        A backoff *strategy* callable ``(attempt: int) -> float`` that
        returns the base delay in seconds before the next attempt.
        Defaults to :func:`retryable.backoff.constant` with a 1-second
        delay.
    jitter:
        A jitter *strategy* callable ``(delay: float) -> float`` applied
        on top of the backoff delay.  Defaults to
        :func:`retryable.jitter.none` (no jitter).
    predicate:
        A callable ``(exc: BaseException) -> bool`` that decides whether
        a raised exception should trigger a retry.  Defaults to
        :func:`retryable.predicates.on_all_exceptions`.
    timeout:
        Optional :class:`retryable.timeout.RetryTimeout` instance.  When
        supplied the total wall-clock time across all attempts is bounded.
    budget:
        Optional :class:`retryable.budget.RetryBudget` instance that
        gates retries via a shared token pool.
    on_retry:
        Optional sequence of hook callables fired between attempts (see
        :mod:`retryable.hooks`).
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff: Optional[Callable[[int], float]] = None,
        jitter: Optional[Callable[[float], float]] = None,
        predicate: Optional[Callable[[BaseException], bool]] = None,
        timeout=None,
        budget=None,
        on_retry=None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.max_attempts = max_attempts
        self.backoff = backoff if backoff is not None else _backoff.constant(1)
        self.jitter = jitter if jitter is not None else _jitter.none
        self.predicate = predicate if predicate is not None else on_all_exceptions
        self.timeout = timeout
        self.budget = budget
        self.on_retry: list = list(on_retry) if on_retry is not None else []

    # ------------------------------------------------------------------
    # Decorator interface
    # ------------------------------------------------------------------

    def apply(self, func: Callable) -> Callable:
        """Wrap *func* with this policy's retry logic and return the wrapper."""
        return retry(
            max_attempts=self.max_attempts,
            backoff=self.backoff,
            jitter=self.jitter,
            predicate=self.predicate,
            timeout=self.timeout,
            budget=self.budget,
            on_retry=self.on_retry if self.on_retry else None,
        )(func)

    # Alias so a policy instance can be used directly as a decorator.
    def __call__(self, func: Callable) -> Callable:  # noqa: D401
        """Allow the policy to be used as a bare decorator."""
        return self.apply(func)

    # Convenience property so users can write ``@policy.retry``.
    @property
    def retry(self) -> Callable:
        """Return :meth:`apply`, enabling ``@policy.retry`` decorator syntax."""
        return self.apply

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetryPolicy("
            f"max_attempts={self.max_attempts!r}, "
            f"backoff={self.backoff!r}, "
            f"jitter={self.jitter!r}, "
            f"predicate={self.predicate!r})"
        )
