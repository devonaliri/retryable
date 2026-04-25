"""retryable — Lightweight retry decorator library with configurable backoff strategies."""

from retryable.decorator import retry
from retryable.backoff import constant, linear, exponential
from retryable.jitter import none as no_jitter, full as full_jitter, equal as equal_jitter, bounded as bounded_jitter
from retryable.predicates import on_exception, on_all_exceptions, exclude_exceptions
from retryable.exceptions import RetryError, RetryLimitExceeded, NonRetryableError
from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import on_retry, HookSet
from retryable.budget import RetryBudget

__all__ = [
    "retry",
    # backoff
    "constant",
    "linear",
    "exponential",
    # jitter
    "no_jitter",
    "full_jitter",
    "equal_jitter",
    "bounded_jitter",
    # predicates
    "on_exception",
    "on_all_exceptions",
    "exclude_exceptions",
    # exceptions
    "RetryError",
    "RetryLimitExceeded",
    "NonRetryableError",
    # context
    "RetryContext",
    "AttemptRecord",
    # hooks
    "on_retry",
    "HookSet",
    # budget
    "RetryBudget",
]

__version__ = "0.1.0"
