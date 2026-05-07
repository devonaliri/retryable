"""Hooks that wire a RetrySignal into a HookSet."""
from __future__ import annotations

from typing import TYPE_CHECKING

from retryable.exceptions import RetryLimitExceeded
from retryable.hooks import HookSet
from retryable.signal import RetrySignal, SignalAction

if TYPE_CHECKING:
    from retryable.context import AttemptRecord, RetryContext


class SignalCancelledError(RetryLimitExceeded):
    """Raised when a RetrySignal requests cancellation."""


def _make_before_hook(signal: RetrySignal):
    def hook(ctx: "RetryContext") -> None:
        if signal.action is SignalAction.CANCEL:
            raise SignalCancelledError(
                last_exception=RuntimeError("Retry cancelled via RetrySignal"),
                attempts=ctx.total_attempts,
            )
    return hook


def _make_after_hook(signal: RetrySignal):
    def hook(ctx: "RetryContext", record: "AttemptRecord") -> None:  # noqa: ARG001
        if signal.action is SignalAction.SUCCEED:
            # Stash the forced value in metadata; the integration wrapper reads it.
            ctx.metadata["__signal_forced_value__"] = signal.forced_value
    return hook


def make_signal_hookset(signal: RetrySignal) -> HookSet:
    """Return a HookSet that checks *signal* before/after every attempt."""
    hs = HookSet()
    hs.before_attempt.append(_make_before_hook(signal))
    hs.after_attempt.append(_make_after_hook(signal))
    return hs
