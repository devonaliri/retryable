"""Tests for retryable.debounce."""

from __future__ import annotations

import pytest

from retryable.debounce import DebounceViolation, RetryDebounce


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SteppingClock:
    """Deterministic clock whose value advances only when explicitly stepped."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestRetryDebounceInit:
    def test_valid_construction(self):
        d = RetryDebounce(min_interval=1.0)
        assert d.min_interval == 1.0

    def test_zero_min_interval_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryDebounce(min_interval=0)

    def test_negative_min_interval_raises(self):
        with pytest.raises(ValueError, match="positive"):
            RetryDebounce(min_interval=-0.5)

    def test_last_attempt_none_initially(self):
        d = RetryDebounce(min_interval=1.0)
        assert d.last_attempt is None


# ---------------------------------------------------------------------------
# allow()
# ---------------------------------------------------------------------------

class TestRetryDebounceAllow:
    def test_allows_first_attempt(self):
        d = RetryDebounce(min_interval=1.0)
        assert d.allow() is True

    def test_disallows_before_interval_elapsed(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=2.0, clock=clock)
        d.record()
        clock.advance(1.0)
        assert d.allow() is False

    def test_allows_after_interval_elapsed(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=2.0, clock=clock)
        d.record()
        clock.advance(2.0)
        assert d.allow() is True

    def test_allows_exactly_at_interval_boundary(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=1.0, clock=clock)
        d.record()
        clock.advance(1.0)
        assert d.allow() is True


# ---------------------------------------------------------------------------
# record() and check()
# ---------------------------------------------------------------------------

class TestRetryDebounceCheck:
    def test_check_records_timestamp(self):
        clock = _SteppingClock(start=5.0)
        d = RetryDebounce(min_interval=1.0, clock=clock)
        d.check()
        assert d.last_attempt == 5.0

    def test_check_raises_debounce_violation_too_soon(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=3.0, clock=clock)
        d.check()          # first call — always allowed
        clock.advance(1.0)
        with pytest.raises(DebounceViolation) as exc_info:
            d.check()
        assert exc_info.value.wait_remaining == pytest.approx(2.0)

    def test_check_passes_after_sufficient_wait(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=1.0, clock=clock)
        d.check()
        clock.advance(1.5)
        d.check()  # should not raise

    def test_debounce_violation_message(self):
        v = DebounceViolation(wait_remaining=0.75)
        assert "0.750" in str(v)


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestRetryDebounceReset:
    def test_reset_clears_last_attempt(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=5.0, clock=clock)
        d.record()
        d.reset()
        assert d.last_attempt is None

    def test_allow_returns_true_after_reset(self):
        clock = _SteppingClock()
        d = RetryDebounce(min_interval=5.0, clock=clock)
        d.record()
        clock.advance(1.0)
        assert d.allow() is False
        d.reset()
        assert d.allow() is True
