"""HookSet integration that gates retry attempts through a LeakyBucket."""
from __future__ import annotations

from typing import Optional

from retryable.context import RetryContext
from retryable.context import AttemptRecord
from retryable.hooks import HookSet
from retryable.leaky_bucket import LeakyBucket, BucketOverflow


class BucketThrottledError(RuntimeError):
    """Raised before an attempt when the leaky bucket is full."""

    def __init__(self) -> None:
        super().__init__("Retry attempt blocked: leaky bucket is full")


def make_leaky_bucket_hookset(
    bucket: LeakyBucket,
    raise_on_overflow: bool = True,
) -> HookSet:
    """Return a HookSet that checks the bucket before every attempt.

    Args:
        bucket:            The LeakyBucket instance to consult.
        raise_on_overflow: If True (default) raise BucketThrottledError when
                           the bucket is full.  If False the hook silently
                           skips consuming a token and lets the attempt
                           proceed (useful for soft throttling / metrics only).
    """
    hookset = HookSet()

    def before(ctx: RetryContext) -> None:  # noqa: D401
        try:
            bucket.consume()
        except BucketOverflow:
            if raise_on_overflow:
                raise BucketThrottledError() from None

    def after(ctx: RetryContext, record: AttemptRecord) -> None:  # noqa: D401
        # Expose current bucket level in attempt metadata for observability.
        record.metadata["leaky_bucket_level"] = bucket.current_level

    hookset.fire_before_attempt  # ensure attribute exists
    hookset._before_hooks.append(before)  # type: ignore[attr-defined]
    hookset._after_hooks.append(after)   # type: ignore[attr-defined]
    return hookset
