"""Hooks that wire RetryCheckpoint into a HookSet for transparent persistence."""
from __future__ import annotations

from typing import Optional

from retryable.checkpoint import CheckpointData, RetryCheckpoint
from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import HookSet


def _exc_type(record: AttemptRecord) -> Optional[str]:
    return type(record.exception).__name__ if record.exception else None


def _exc_msg(record: AttemptRecord) -> Optional[str]:
    return str(record.exception) if record.exception else None


def make_checkpoint_hookset(
    checkpoint: RetryCheckpoint,
    key: str,
) -> HookSet:
    """Return a HookSet that saves state after every failed attempt and clears
    the checkpoint once the call eventually succeeds.
    """
    hooks = HookSet()

    def after_attempt(ctx: RetryContext, record: AttemptRecord) -> None:
        if record.exception is not None:
            data = CheckpointData(
                key=key,
                attempts=ctx.total_attempts,
                last_exception_type=_exc_type(record),
                last_exception_message=_exc_msg(record),
            )
            checkpoint.save(data)
        else:
            checkpoint.clear(key)

    hooks.fire_after_attempt = after_attempt  # type: ignore[method-assign]
    return hooks


def resume_attempts(checkpoint: RetryCheckpoint, key: str) -> int:
    """Return the number of attempts already recorded for *key*, or 0."""
    data = checkpoint.load(key)
    return data.attempts if data is not None else 0
