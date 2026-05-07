"""Tests for retryable.leaky_bucket and retryable.leaky_bucket_integration."""
from __future__ import annotations

import pytest

from retryable.leaky_bucket import BucketOverflow, LeakyBucket
from retryable.leaky_bucket_integration import (
    BucketThrottledError,
    make_leaky_bucket_hookset,
)
from retryable.context import RetryContext, AttemptRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ManualClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _bucket(rate: float = 1.0, capacity: int = 3, clock: _ManualClock | None = None) -> LeakyBucket:
    return LeakyBucket(leak_rate=rate, capacity=capacity, clock=clock or _ManualClock())


# ---------------------------------------------------------------------------
# Init validation
# ---------------------------------------------------------------------------

class TestLeakyBucketInit:
    def test_valid_construction(self) -> None:
        b = LeakyBucket(leak_rate=2.0, capacity=5)
        assert b.leak_rate == 2.0
        assert b.capacity == 5

    def test_zero_leak_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="leak_rate"):
            LeakyBucket(leak_rate=0)

    def test_negative_leak_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="leak_rate"):
            LeakyBucket(leak_rate=-1)

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity"):
            LeakyBucket(leak_rate=1, capacity=0)


# ---------------------------------------------------------------------------
# allow / consume behaviour
# ---------------------------------------------------------------------------

class TestLeakyBucketAllow:
    def test_allows_up_to_capacity(self) -> None:
        b = _bucket(capacity=3)
        assert all(b.allow() for _ in range(3))

    def test_rejects_when_full(self) -> None:
        b = _bucket(capacity=2)
        b.allow(); b.allow()
        assert b.allow() is False

    def test_drains_over_time(self) -> None:
        clock = _ManualClock()
        b = _bucket(rate=1.0, capacity=2, clock=clock)
        b.allow(); b.allow()          # fill to capacity
        assert b.allow() is False
        clock.advance(1.5)            # drain 1.5 tokens => level ~0.5
        assert b.allow() is True      # room for one more

    def test_consume_raises_on_overflow(self) -> None:
        b = _bucket(capacity=1)
        b.consume()
        with pytest.raises(BucketOverflow) as exc_info:
            b.consume()
        assert exc_info.value.capacity == 1

    def test_current_level_reflects_drain(self) -> None:
        clock = _ManualClock()
        b = _bucket(rate=2.0, capacity=4, clock=clock)
        b.allow(); b.allow()          # level = 2
        clock.advance(1.0)            # drain 2 => level = 0
        assert b.current_level == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Integration: HookSet
# ---------------------------------------------------------------------------

def _make_ctx() -> RetryContext:
    ctx = RetryContext(fn=lambda: None, args=(), kwargs={})
    return ctx


def _make_record(exc: Exception | None = None) -> AttemptRecord:
    r = AttemptRecord(attempt_number=1, exception=exc, delay=0.0)
    return r


class TestLeakyBucketHookSet:
    def test_before_hook_consumes_token(self) -> None:
        b = _bucket(capacity=2)
        hs = make_leaky_bucket_hookset(b)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)
        assert b.current_level == pytest.approx(1.0)

    def test_raises_when_bucket_full(self) -> None:
        b = _bucket(capacity=1)
        hs = make_leaky_bucket_hookset(b, raise_on_overflow=True)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)   # consumes the only slot
        with pytest.raises(BucketThrottledError):
            hs.fire_before_attempt(ctx)

    def test_no_raise_when_soft_mode(self) -> None:
        b = _bucket(capacity=1)
        hs = make_leaky_bucket_hookset(b, raise_on_overflow=False)
        ctx = _make_ctx()
        hs.fire_before_attempt(ctx)
        hs.fire_before_attempt(ctx)   # should not raise

    def test_after_hook_records_level_in_metadata(self) -> None:
        b = _bucket(capacity=5)
        hs = make_leaky_bucket_hookset(b)
        ctx = _make_ctx()
        record = _make_record()
        hs.fire_before_attempt(ctx)
        hs.fire_after_attempt(ctx, record)
        assert "leaky_bucket_level" in record.metadata
