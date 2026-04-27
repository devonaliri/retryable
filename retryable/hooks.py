"""Hook infrastructure for before/after retry attempt callbacks."""
from __future__ import annotations

from typing import Callable, List

from retryable.context import AttemptRecord, RetryContext

BeforeHook = Callable[[RetryContext], None]
AfterHook = Callable[[RetryContext, AttemptRecord], None]


def on_retry(fn: BeforeHook) -> BeforeHook:
    """Mark a callable as a before-attempt hook (identity decorator)."""
    return fn


class HookSet:
    """Container for before and after attempt hooks.

    Attributes
    ----------
    before:
        Hooks called before each attempt with the current :class:`RetryContext`.
    after:
        Hooks called after each attempt with context and :class:`AttemptRecord`.
    """

    def __init__(
        self,
        before: List[BeforeHook] | None = None,
        after: List[AfterHook] | None = None,
    ) -> None:
        self.before: List[BeforeHook] = list(before or [])
        self.after: List[AfterHook] = list(after or [])

    def fire_before_attempt(self, ctx: RetryContext) -> None:
        """Invoke all registered before-attempt hooks."""
        for hook in self.before:
            hook(ctx)

    def fire_after_attempt(self, ctx: RetryContext, record: AttemptRecord) -> None:
        """Invoke all registered after-attempt hooks."""
        for hook in self.after:
            hook(ctx, record)
