"""Tests for retryable.cooldown."""
from __future__ import annotations

import pytest

from retryable.cooldown import RetryCooldown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SteppingClock:
    """A fake monotonic clock whose value advances on demand."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestRetryCooldownInit:
    def test_valid_construction(self):
        cd = RetryCooldown(5.0)
        assert cd.cooldown_seconds == 5.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryCooldown(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryCooldown(-1.0)

    def test_not_active_initially(self):
        cd = RetryCooldown(10.0)
        assert cd.active is False

    def test_allow_true_initially(self):
        cd = RetryCooldown(10.0)
        assert cd.allow() is True

    def test_remaining_zero_initially(self):
        cd = RetryCooldown(10.0)
        assert cd.remaining == 0.0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestRetryCooldownLifecycle:
    def test_active_immediately_after_burst_end(self):
        clock = _SteppingClock(100.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        assert cd.active is True

    def test_allow_false_during_cooldown(self):
        clock = _SteppingClock(100.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        clock.advance(3.0)
        assert cd.allow() is False

    def test_allow_true_after_cooldown_expires(self):
        clock = _SteppingClock(100.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        clock.advance(5.1)
        assert cd.allow() is True

    def test_active_false_after_cooldown_expires(self):
        clock = _SteppingClock(0.0)
        cd = RetryCooldown(2.0, clock=clock)
        cd.record_burst_end()
        clock.advance(2.0)
        assert cd.active is False

    def test_remaining_decreases_over_time(self):
        clock = _SteppingClock(0.0)
        cd = RetryCooldown(10.0, clock=clock)
        cd.record_burst_end()
        clock.advance(3.0)
        assert abs(cd.remaining - 7.0) < 1e-9

    def test_remaining_zero_after_expiry(self):
        clock = _SteppingClock(0.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        clock.advance(10.0)
        assert cd.remaining == 0.0

    def test_reset_clears_state(self):
        clock = _SteppingClock(0.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        assert cd.active is True
        cd.reset()
        assert cd.active is False
        assert cd.allow() is True

    def test_second_burst_end_restarts_window(self):
        clock = _SteppingClock(0.0)
        cd = RetryCooldown(5.0, clock=clock)
        cd.record_burst_end()
        clock.advance(6.0)          # first window expired
        assert cd.allow() is True
        cd.record_burst_end()       # start a new burst
        assert cd.active is True
        assert cd.allow() is False
