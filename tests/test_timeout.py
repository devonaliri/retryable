"""Tests for retryable.timeout."""

import time
import pytest

from retryable.timeout import RetryTimeout


class TestRetryTimeoutInit:
    def test_valid_construction(self):
        t = RetryTimeout(5.0)
        assert t.total_seconds == 5.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryTimeout(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryTimeout(-1.0)


class TestRetryTimeoutLifecycle:
    def test_elapsed_before_start_raises(self):
        t = RetryTimeout(5.0)
        with pytest.raises(RuntimeError, match="start\(\) has not been called"):
            _ = t.elapsed

    def test_remaining_before_start_raises(self):
        t = RetryTimeout(5.0)
        with pytest.raises(RuntimeError):
            _ = t.remaining

    def test_elapsed_increases_after_start(self):
        t = RetryTimeout(5.0)
        t.start()
        time.sleep(0.05)
        assert t.elapsed >= 0.04

    def test_remaining_decreases_over_time(self):
        t = RetryTimeout(5.0)
        t.start()
        time.sleep(0.05)
        assert t.remaining < 5.0

    def test_remaining_never_negative(self):
        t = RetryTimeout(0.01)
        t.start()
        time.sleep(0.05)
        assert t.remaining == 0.0


class TestRetryTimeoutExpiry:
    def test_not_expired_immediately(self):
        t = RetryTimeout(10.0)
        t.start()
        assert not t.is_expired

    def test_expired_after_budget_consumed(self):
        t = RetryTimeout(0.02)
        t.start()
        time.sleep(0.05)
        assert t.is_expired


class TestClampDelay:
    def test_clamp_returns_delay_when_plenty_of_time(self):
        t = RetryTimeout(10.0)
        t.start()
        assert t.clamp_delay(1.0) == pytest.approx(1.0, abs=0.01)

    def test_clamp_caps_at_remaining(self):
        t = RetryTimeout(0.1)
        t.start()
        time.sleep(0.08)
        clamped = t.clamp_delay(5.0)
        assert clamped <= 0.1

    def test_clamp_returns_zero_when_expired(self):
        t = RetryTimeout(0.01)
        t.start()
        time.sleep(0.05)
        assert t.clamp_delay(2.0) == 0.0
