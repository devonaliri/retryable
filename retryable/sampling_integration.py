"""Hooks that gate retry observation behind a RetrySampler."""
from __future__ import annotations

from typing import Callable

from retryable.context import AttemptRecord, RetryContext
from retryable.hooks import HookSet
from retryable.sampling import RetrySampler

# A key we store on the context's metadata dict to propagate the sampling
# decision from the before-hook to the after-hook within a single attempt.
_SAMPLED_KEY = "_sampler_sampled"


def make_sampled_hookset(
    sampler: RetrySampler,
    before: Callable[[RetryContext], None],
    after: Callable[[RetryContext, AttemptRecord], None],
) -> HookSet:
    """Wrap *before* and *after* hooks so they only fire when sampled.

    The sampling decision is made once per attempt in the before-hook and
    stored on ``ctx.metadata`` so the after-hook uses the same decision.

    Args:
        sampler: A :class:`RetrySampler` instance.
        before:  Hook called before each attempt (when sampled).
        after:   Hook called after each attempt (when sampled).

    Returns:
        A :class:`~retryable.hooks.HookSet` with the wrapped hooks.
    """
    hs = HookSet()

    def _before(ctx: RetryContext) -> None:
        sampled = sampler.should_sample()
        ctx.metadata[_SAMPLED_KEY] = sampled
        if sampled:
            before(ctx)

    def _after(ctx: RetryContext, record: AttemptRecord) -> None:
        if ctx.metadata.get(_SAMPLED_KEY):
            after(ctx, record)

    hs.before_attempt.append(_before)
    hs.after_attempt.append(_after)
    return hs


def always_sample_hookset(
    before: Callable[[RetryContext], None],
    after: Callable[[RetryContext, AttemptRecord], None],
) -> HookSet:
    """Convenience wrapper: create a hook-set sampled at 100 %.

    Equivalent to ``make_sampled_hookset(RetrySampler(1.0), before, after)``.
    """
    return make_sampled_hookset(RetrySampler(1.0), before, after)
