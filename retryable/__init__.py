"""retryable — Lightweight retry decorator library with configurable backoff strategies."""

from retryable.decorator import retry
from retryable.exceptions import NonRetryableError, RetryError, RetryLimitExceeded
from retryable.backoff import constant, linear, exponential
from retryable.jitter import none as no_jitter, full as full_jitter, equal as equal_jitter
from retryable.predicates import on_exception, on_all_exceptions, exclude_exceptions
from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import on_retry, HookSet
from retryable.budget import RetryBudget
from retryable.timeout import RetryTimeout
from retryable.throttle import RetryThrottle
from retryable.metrics import RetryMetrics

__all__ = [
    # Core
    "retry",
    # Exceptions
    "RetryError",
    "RetryLimitExceeded",
    "NonRetryableError",
    # Backoff strategies
    "constant",
    "linear",
    "exponential",
    # Jitter strategies
    "no_jitter",
    "full_jitter",
    "equal_jitter",
    # Predicates
    "on_exception",
    "on_all_exceptions",
    "exclude_exceptions",
    # Context
    "RetryContext",
    "AttemptRecord",
    # Hooks
    "on_retry",
    "HookSet",
    # Budget / Timeout / Throttle
    "RetryBudget",
    "RetryTimeout",
    "RetryThrottle",
    # Metrics
    "RetryMetrics",
]
