"""Tests for retryable.token_bucket."""
from __future__ import annotations

import pytest

from retryable.token_bucket import TokenBucket, BucketDepleted


class _ManualClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _bucket(rate: float = 1.0, capacity: float = 5.0, start: float = 0.0) -> tuple[TokenBucket, _ManualClock]:
    clock = _ManualClock(start)
    return TokenBucket(rate, capacity, clock), clock


class TestTokenBucketInit:
    def test_valid_construction(self) -> None:
        tb, _ = _bucket()
        assert tb.rate == 1.0
        assert tb.capacity == 5.0

    def test_zero_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            TokenBucket(0.0, 5.0)

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            TokenBucket(-1.0, 5.0)

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(1.0, 0.0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(1.0, -3.0)

    def test_starts_full(self) -> None:
        tb, _ = _bucket(capacity=10.0)
        assert tb.available == pytest.approx(10.0)


class TestTokenBucketConsume:
    def test_consume_reduces_tokens(self) -> None:
        tb, _ = _bucket(capacity=5.0)
        assert tb.consume(2.0) is True
        assert tb.available == pytest.approx(3.0)

    def test_consume_returns_false_when_insufficient(self) -> None:
        tb, _ = _bucket(capacity=1.0)
        tb.consume(1.0)
        assert tb.consume(1.0) is False

    def test_consume_or_raise_raises_bucket_depleted(self) -> None:
        tb, _ = _bucket(capacity=1.0)
        tb.consume(1.0)
        with pytest.raises(BucketDepleted):
            tb.consume_or_raise(1.0)

    def test_bucket_depleted_carries_amounts(self) -> None:
        tb, _ = _bucket(capacity=0.5)
        tb.consume(0.5)
        try:
            tb.consume_or_raise(1.0)
        except BucketDepleted as exc:
            assert exc.requested == pytest.approx(1.0)
            assert exc.available == pytest.approx(0.0, abs=1e-9)


class TestTokenBucketRefill:
    def test_tokens_refill_over_time(self) -> None:
        tb, clock = _bucket(rate=2.0, capacity=10.0)
        tb.consume(10.0)
        clock.advance(3.0)
        assert tb.available == pytest.approx(6.0)

    def test_tokens_capped_at_capacity(self) -> None:
        tb, clock = _bucket(rate=10.0, capacity=5.0)
        clock.advance(100.0)
        assert tb.available == pytest.approx(5.0)

    def test_partial_refill_allows_partial_consume(self) -> None:
        tb, clock = _bucket(rate=1.0, capacity=5.0)
        tb.consume(5.0)
        clock.advance(2.0)
        assert tb.consume(2.0) is True
        assert tb.consume(1.0) is False
