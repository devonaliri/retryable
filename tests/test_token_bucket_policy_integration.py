"""End-to-end test: TokenBucket throttle wired into a RetryPolicy."""
from __future__ import annotations

import pytest

from retryable.policy import RetryPolicy
from retryable.token_bucket import TokenBucket
from retryable.token_bucket_integration import (
    make_token_bucket_hookset,
    BucketThrottledError,
)


class _ManualClock:
    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_policy(bucket: TokenBucket, max_attempts: int = 5) -> RetryPolicy:
    hookset = make_token_bucket_hookset(bucket)
    return RetryPolicy(
        max_attempts=max_attempts,
        delay=0.0,
        hooks=hookset,
    )


class TestTokenBucketWithPolicy:
    def test_success_on_first_attempt_consumes_one_token(self) -> None:
        clock = _ManualClock()
        bucket = TokenBucket(1.0, 10.0, clock)
        policy = _make_policy(bucket)

        @policy
        def ok() -> str:
            return "done"

        result = ok()
        assert result == "done"
        assert bucket.available == pytest.approx(9.0)

    def test_throttled_error_propagates_from_policy(self) -> None:
        clock = _ManualClock()
        # Only 1 token — first attempt consumes it, second attempt raises.
        bucket = TokenBucket(10.0, 1.0, clock)
        policy = _make_policy(bucket, max_attempts=5)

        call_count = 0

        @policy
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("boom")

        with pytest.raises(BucketThrottledError):
            flaky()

        # Only one real call was made before the bucket ran dry.
        assert call_count == 1

    def test_tokens_refill_allows_retry(self) -> None:
        clock = _ManualClock()
        # Rate=2/s, capacity=2 — start full, first two attempts drain it.
        bucket = TokenBucket(2.0, 2.0, clock)
        policy = _make_policy(bucket, max_attempts=3)

        call_count = 0

        @policy
        def eventually_ok() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("not yet")
            return "ok"

        # Advance clock so bucket refills between attempts.
        clock.advance(5.0)
        result = eventually_ok()
        assert result == "ok"
