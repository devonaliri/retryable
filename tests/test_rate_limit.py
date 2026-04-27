"""Tests for retryable.rate_limit."""

import time
import pytest
from unittest.mock import patch

from retryable.rate_limit import RateLimiter


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestRateLimiterInit:
    def test_valid_construction(self):
        rl = RateLimiter(rate=5.0)
        assert rl.rate == 5.0
        assert rl.capacity == 5.0

    def test_custom_capacity(self):
        rl = RateLimiter(rate=2.0, capacity=10.0)
        assert rl.capacity == 10.0

    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="rate must be positive"):
            RateLimiter(rate=0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate must be positive"):
            RateLimiter(rate=-1.0)

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            RateLimiter(rate=5.0, capacity=0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            RateLimiter(rate=5.0, capacity=-3.0)


# ---------------------------------------------------------------------------
# Token consumption
# ---------------------------------------------------------------------------

class TestRateLimiterAllow:
    def test_allows_up_to_capacity(self):
        rl = RateLimiter(rate=3.0, capacity=3.0)
        assert rl.allow() is True
        assert rl.allow() is True
        assert rl.allow() is True

    def test_denies_when_bucket_empty(self):
        rl = RateLimiter(rate=1.0, capacity=1.0)
        rl.allow()  # consume the single token
        assert rl.allow() is False

    def test_tokens_decrease_on_allow(self):
        rl = RateLimiter(rate=5.0, capacity=5.0)
        before = rl.tokens()
        rl.allow()
        assert rl.tokens() < before

    def test_tokens_do_not_exceed_capacity(self):
        rl = RateLimiter(rate=2.0, capacity=2.0)
        # Simulate a large time gap via monotonic patch
        with patch("retryable.rate_limit.time.monotonic", return_value=time.monotonic() + 100):
            assert rl.tokens() <= rl.capacity


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestRateLimiterReset:
    def test_reset_restores_capacity(self):
        rl = RateLimiter(rate=3.0, capacity=3.0)
        rl.allow()
        rl.allow()
        rl.reset()
        assert rl.tokens() == pytest.approx(3.0, abs=0.01)

    def test_allows_again_after_reset(self):
        rl = RateLimiter(rate=1.0, capacity=1.0)
        rl.allow()
        assert rl.allow() is False
        rl.reset()
        assert rl.allow() is True
