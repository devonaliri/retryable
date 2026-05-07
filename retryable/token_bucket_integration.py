"""Integration helpers: attach a TokenBucket to a HookSet."""
from __future__ import annotations

from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import HookSet
from retryable.token_bucket import TokenBucket, BucketDepleted


class BucketThrottledError(Exception):
    """Raised by the before-hook when the token bucket is depleted."""

    def __init__(self, inner: BucketDepleted) -> None:
        self.inner = inner
        super().__init__(str(inner))


def make_token_bucket_hookset(
    bucket: TokenBucket,
    *,
    tokens_per_attempt: float = 1.0,
) -> HookSet:
    """Return a :class:`~retryable.hooks.HookSet` that gates each attempt
    through *bucket*.

    The before-hook tries to consume *tokens_per_attempt* tokens before every
    attempt.  If the bucket is depleted a :exc:`BucketThrottledError` is raised,
    which will propagate out of the retry loop.
    """
    hookset = HookSet()

    def before(ctx: RetryContext) -> None:
        try:
            bucket.consume_or_raise(tokens_per_attempt)
        except BucketDepleted as exc:
            raise BucketThrottledError(exc) from exc

    def after(ctx: RetryContext, record: AttemptRecord) -> None:  # noqa: ARG001
        # Reserved for future telemetry (e.g. recording bucket level).
        pass

    hookset.before_attempt_hooks.append(before)
    hookset.after_attempt_hooks.append(after)
    return hookset
