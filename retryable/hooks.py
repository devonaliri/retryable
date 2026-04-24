"""Hooks for observing retry lifecycle events."""
from typing import Callable, Optional
from retryable.context import AttemptRecord, RetryContext


HookFn = Callable[[RetryContext, AttemptRecord], None]


def on_retry(fn: HookFn) -> HookFn:
    """Mark a callable as a retry hook (identity, for documentation/typing)."""
    return fn


class HookSet:
    """Container for lifecycle hooks attached to a retry decorator."""

    def __init__(
        self,
        before_attempt: Optional[HookFn] = None,
        after_attempt: Optional[HookFn] = None,
        on_failure: Optional[HookFn] = None,
        on_success: Optional[HookFn] = None,
    ) -> None:
        self.before_attempt = before_attempt
        self.after_attempt = after_attempt
        self.on_failure = on_failure
        self.on_success = on_success

    def fire_before_attempt(self, ctx: RetryContext, record: AttemptRecord) -> None:
        if self.before_attempt is not None:
            self.before_attempt(ctx, record)

    def fire_after_attempt(self, ctx: RetryContext, record: AttemptRecord) -> None:
        if self.after_attempt is not None:
            self.after_attempt(ctx, record)

    def fire_on_failure(self, ctx: RetryContext, record: AttemptRecord) -> None:
        if self.on_failure is not None:
            self.on_failure(ctx, record)

    def fire_on_success(self, ctx: RetryContext, record: AttemptRecord) -> None:
        if self.on_success is not None:
            self.on_success(ctx, record)


EMPTY_HOOKS = HookSet()
