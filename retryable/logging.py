"""Structured logging hooks for retry attempts."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from retryable.context import AttemptRecord, RetryContext

_DEFAULT_LOGGER = logging.getLogger("retryable")


def _format_attempt(ctx: RetryContext, record: AttemptRecord) -> dict[str, Any]:
    """Build a structured log payload from context and record."""
    payload: dict[str, Any] = {
        "attempt": ctx.total_attempts,
        "elapsed": round(time.monotonic() - ctx._start_time, 4) if hasattr(ctx, "_start_time") else None,
        "delay": record.delay,
        "succeeded": record.succeeded,
    }
    if not record.succeeded and record.exception is not None:
        payload["exception_type"] = type(record.exception).__name__
        payload["exception"] = str(record.exception)
    return payload


def make_before_hook(
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
) -> Callable[[RetryContext], None]:
    """Return a before-attempt hook that logs attempt start."""
    _log = logger or _DEFAULT_LOGGER

    def hook(ctx: RetryContext) -> None:
        _log.log(
            level,
            "[retryable] starting attempt %d",
            ctx.total_attempts + 1,
        )

    return hook


def make_after_hook(
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
    failure_level: int = logging.WARNING,
) -> Callable[[RetryContext, AttemptRecord], None]:
    """Return an after-attempt hook that logs attempt outcome."""
    _log = logger or _DEFAULT_LOGGER

    def hook(ctx: RetryContext, record: AttemptRecord) -> None:
        payload = _format_attempt(ctx, record)
        if record.succeeded:
            _log.log(level, "[retryable] attempt %d succeeded %s", ctx.total_attempts, payload)
        else:
            _log.log(
                failure_level,
                "[retryable] attempt %d failed %s",
                ctx.total_attempts,
                payload,
            )

    return hook
