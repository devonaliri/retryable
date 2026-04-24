"""Custom exceptions and exception filtering utilities for retryable."""

from typing import Sequence, Type, Union


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts

    def __str__(self) -> str:
        return (
            f"{super().__str__()} "
            f"(last error: {type(self.last_exception).__name__}: {self.last_exception}, "
            f"attempts: {self.attempts})"
        )


class RetryLimitExceeded(RetryError):
    """Raised specifically when the maximum number of retries is exceeded."""
    pass


class NonRetryableError(Exception):
    """Raised when an exception is encountered that should not be retried."""

    def __init__(self, message: str, original_exception: Exception):
        super().__init__(message)
        self.original_exception = original_exception


ExceptionTypes = Union[Type[Exception], Sequence[Type[Exception]]]


def is_retryable(exc: Exception, retryable_exceptions: ExceptionTypes) -> bool:
    """Determine whether a given exception should trigger a retry.

    Args:
        exc: The exception instance to check.
        retryable_exceptions: A single exception type or a sequence of
            exception types that are considered retryable.

    Returns:
        True if the exception matches one of the retryable types, False otherwise.
    """
    if isinstance(retryable_exceptions, (list, tuple)):
        return isinstance(exc, tuple(retryable_exceptions))
    return isinstance(exc, retryable_exceptions)


def is_non_retryable(exc: Exception, non_retryable_exceptions: ExceptionTypes) -> bool:
    """Determine whether a given exception should NOT be retried.

    Args:
        exc: The exception instance to check.
        non_retryable_exceptions: A single exception type or a sequence of
            exception types that are explicitly excluded from retrying.

    Returns:
        True if the exception matches one of the non-retryable types, False otherwise.
    """
    if isinstance(non_retryable_exceptions, (list, tuple)):
        return isinstance(exc, tuple(non_retryable_exceptions))
    return isinstance(exc, non_retryable_exceptions)
