"""Core retry decorator implementation."""
import time
import logging
import functools
from typing import Callable, Optional, Tuple, Type, Union

from retryable.backoff import constant

logger = logging.getLogger(__name__)

ExceptionTypes = Union[Type[Exception], Tuple[Type[Exception], ...]]


def retry(
    max_attempts: int = 3,
    exceptions: ExceptionTypes = Exception,
    backoff: Optional[Callable[[int], float]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable:
    """Decorator that retries a function on failure.

    Args:
        max_attempts: Maximum number of total attempts (must be >= 1).
        exceptions: Exception type(s) that should trigger a retry.
        backoff: Callable that accepts the attempt number (1-based) and
                 returns the number of seconds to sleep before the next
                 attempt.  Defaults to ``constant(delay=1.0)``.
        on_retry: Optional callback invoked before each retry with
                  ``(attempt, exception)``.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    _backoff = backoff if backoff is not None else constant(delay=1.0)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.debug(
                            "%s failed after %d attempt(s): %s",
                            func.__qualname__,
                            attempt,
                            exc,
                        )
                        break
                    delay = _backoff(attempt)
                    logger.debug(
                        "%s attempt %d/%d failed (%s). Retrying in %.2fs.",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    if on_retry is not None:
                        on_retry(attempt, exc)
                    time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
