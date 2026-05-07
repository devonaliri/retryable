"""Integration tests for TokenBucket + HookSet."""
from __future__ import annotations

import time
import pytest

from retryable.token_bucket import TokenBucket, BucketDepleted
from retryable.token_bucket_integration import (
    make_token_bucket_hookset,
    BucketThrottledError,
)
from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import HookSet


class _ManualClock:
    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_ctx() -> RetryContext:
    return RetryContext(fn_name="test_fn")


def _make_record(exc: Exception | None = None) -> AttemptRecord:
    return AttemptRecord(attempt_number=1, delay=0.0, exception=exc)


class TestMakeTokenBucketHookSet:
    def test_returns_hookset(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 5.0, clock)
        hs = make_token_bucket_hookset(bucket)
        assert isinstance(hs, HookSet)

    def test_has_before_and_after_hooks(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 5.0, clock)
        hs = make_token_bucket_hookset(bucket)
        assert len(hs.before_attempt_hooks) == 1
        assert len(hs.after_attempt_hooks) == 1

    def test_before_hook_consumes_token(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 3.0, clock)
        hs = make_token_bucket_hookset(bucket)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)
        assert bucket.available == pytest.approx(2.0)

    def test_before_hook_raises_when_depleted(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 1.0, clock)
        hs = make_token_bucket_hookset(bucket)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)  # consumes the only token
        with pytest.raises(BucketThrottledError):
            hs.fire_before_attempt(ctx)

    def test_throttled_error_wraps_bucket_depleted(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 1.0, clock)
        hs = make_token_bucket_hookset(bucket)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)
        try:
            hs.fire_before_attempt(ctx)
        except BucketThrottledError as exc:
            assert isinstance(exc.inner, BucketDepleted)

    def test_after_hook_does_not_raise(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 5.0, clock)
        hs = make_token_bucket_hookset(bucket)
        ctx = _make_ctx()
        record = _make_record()
        hs.fire_after_attempt(ctx, record)  # should not raise

    def test_custom_tokens_per_attempt(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 10.0, clock)
        hs = make_token_bucket_hookset(bucket, tokens_per_attempt=3.0)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)
        assert bucket.available == pytest.approx(7.0)
