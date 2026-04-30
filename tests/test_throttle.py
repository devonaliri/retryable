"""Tests for retryable.throttle.RetryThrottle."""
from __future__ import annotations

import time

import pytest

from retryable.throttle import RetryThrottle


class TestRetryThrottleInit:
    def test_valid_construction(self):
        t = RetryThrottle(max_attempts=5, window_seconds=10.0)
        assert t.max_attempts == 5
        assert t.window_seconds == 10.0

    def test_zero_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryThrottle(max_attempts=0, window_seconds=5.0)

    def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryThrottle(max_attempts=-1, window_seconds=5.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RetryThrottle(max_attempts=3, window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RetryThrottle(max_attempts=3, window_seconds=-1.0)


class TestRetryThrottleAllow:
    def test_allows_up_to_max(self):
        t = RetryThrottle(max_attempts=3, window_seconds=60.0)
        assert t.allow() is True
        assert t.allow() is True
        assert t.allow() is True

    def test_blocks_when_limit_reached(self):
        t = RetryThrottle(max_attempts=2, window_seconds=60.0)
        t.allow()
        t.allow()
        assert t.allow() is False

    def test_remaining_decreases_on_allow(self):
        t = RetryThrottle(max_attempts=4, window_seconds=60.0)
        assert t.remaining() == 4
        t.allow()
        assert t.remaining() == 3
        t.allow()
        assert t.remaining() == 2

    def test_remaining_zero_when_exhausted(self):
        t = RetryThrottle(max_attempts=2, window_seconds=60.0)
        t.allow()
        t.allow()
        assert t.remaining() == 0

    def test_reset_clears_history(self):
        t = RetryThrottle(max_attempts=2, window_seconds=60.0)
        t.allow()
        t.allow()
        assert t.allow() is False
        t.reset()
        assert t.allow() is True

    def test_blocked_attempt_does_not_consume_slot(self):
        """A call to allow() that returns False must not record a timestamp,
        so the remaining count stays at zero rather than going negative."""
        t = RetryThrottle(max_attempts=2, window_seconds=60.0)
        t.allow()
        t.allow()
        assert t.remaining() == 0
        t.allow()  # blocked
        t.allow()  # blocked
        assert t.remaining() == 0


class TestRetryThrottleWindow:
    def test_old_timestamps_evicted_after_window(self):
        """Attempts older than the window should not count."""
        t = RetryThrottle(max_attempts=2, window_seconds=0.1)
        t.allow()
        t.allow()
        # Both slots used — must wait for the window to expire.
        assert t.allow() is False
        time.sleep(0.15)
        # Window has rolled; slots are free again.
        assert t.allow() is True

    def test_remaining_recovers_after_window(self):
        t = RetryThrottle(max_attempts=3, window_seconds=0.1)
        t.allow()
        t.allow()
        t.allow()
        assert t.remaining() == 0
        time.sleep(0.15)
        assert t.remaining() == 3
