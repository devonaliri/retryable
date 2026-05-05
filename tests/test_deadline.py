"""Tests for retryable.deadline."""

from __future__ import annotations

import pytest

from retryable.deadline import Deadline, DeadlineExceeded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixed_clock(value: float):
    """Return a clock function that always returns *value*."""
    return lambda: value


class _SteppingClock:
    """A clock whose return value advances by *step* each call."""

    def __init__(self, start: float = 0.0, step: float = 1.0) -> None:
        self._value = start
        self._step = step

    def __call__(self) -> float:
        v = self._value
        self._value += self._step
        return v


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestDeadlineInit:
    def test_valid_construction(self):
        d = Deadline(10.0)
        assert d.total_seconds == 10.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Deadline(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Deadline(-5)


# ---------------------------------------------------------------------------
# Lifecycle / elapsed / remaining
# ---------------------------------------------------------------------------

class TestDeadlineLifecycle:
    def test_elapsed_zero_before_start(self):
        d = Deadline(5.0, clock=_fixed_clock(100.0))
        assert d.elapsed == 0.0

    def test_remaining_equals_total_before_start(self):
        d = Deadline(5.0, clock=_fixed_clock(100.0))
        assert d.remaining == 5.0

    def test_start_records_time(self):
        clock = _SteppingClock(start=0.0, step=2.0)
        d = Deadline(10.0, clock=clock)
        d.start()          # clock → 0
        # elapsed uses next call → 2
        assert d.elapsed == pytest.approx(2.0)

    def test_start_is_idempotent(self):
        clock = _SteppingClock(start=0.0, step=1.0)
        d = Deadline(10.0, clock=clock)
        d.start()  # records 0
        d.start()  # should NOT advance start time
        # elapsed: clock returns 2 on next call
        assert d.elapsed == pytest.approx(2.0)

    def test_remaining_never_negative(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()  # start=0
        # next call → 20, elapsed=20 > total=5
        assert d.remaining == 0.0


# ---------------------------------------------------------------------------
# Expiry / check
# ---------------------------------------------------------------------------

class TestDeadlineExpiry:
    def test_not_expired_within_budget(self):
        clock = _SteppingClock(start=0.0, step=1.0)
        d = Deadline(10.0, clock=clock)
        d.start()  # start=0
        # elapsed → 1
        assert not d.is_expired

    def test_expired_when_over_budget(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()  # start=0
        # elapsed → 20
        assert d.is_expired

    def test_check_raises_when_expired(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()
        with pytest.raises(DeadlineExceeded):
            d.check()

    def test_check_passes_within_budget(self):
        clock = _SteppingClock(start=0.0, step=1.0)
        d = Deadline(10.0, clock=clock)
        d.start()
        d.check()  # should not raise

    def test_deadline_exceeded_message(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()
        exc = DeadlineExceeded(d)
        assert "5.0" in str(exc)
        assert "elapsed" in str(exc)


# ---------------------------------------------------------------------------
# clamp_delay
# ---------------------------------------------------------------------------

class TestClampDelay:
    def test_clamps_delay_to_remaining(self):
        clock = _SteppingClock(start=0.0, step=3.0)
        d = Deadline(5.0, clock=clock)
        d.start()  # start=0; next call → 3, remaining=2
        assert d.clamp_delay(10.0) == pytest.approx(2.0)

    def test_does_not_clamp_when_delay_fits(self):
        clock = _SteppingClock(start=0.0, step=1.0)
        d = Deadline(10.0, clock=clock)
        d.start()  # start=0; next call → 1, remaining=9
        assert d.clamp_delay(3.0) == pytest.approx(3.0)

    def test_clamp_returns_zero_when_expired(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()
        assert d.clamp_delay(5.0) == 0.0
