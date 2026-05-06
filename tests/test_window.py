"""Tests for retryable.window.SlidingWindow."""

from __future__ import annotations

import pytest

from retryable.window import SlidingWindow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ManualClock:
    """Controllable monotonic clock for deterministic tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _win(seconds: float = 10.0, clock: _ManualClock | None = None) -> tuple[SlidingWindow, _ManualClock]:
    clk = clock or _ManualClock()
    return SlidingWindow(window_seconds=seconds, clock=clk), clk


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestSlidingWindowInit:
    def test_valid_construction(self):
        sw, _ = _win(5.0)
        assert sw.window_seconds == 5.0

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SlidingWindow(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SlidingWindow(window_seconds=-1)


# ---------------------------------------------------------------------------
# Recording and counting
# ---------------------------------------------------------------------------

class TestSlidingWindowCounts:
    def test_empty_window_totals(self):
        sw, _ = _win()
        assert sw.total() == 0
        assert sw.failures() == 0
        assert sw.successes() == 0
        assert sw.failure_rate() is None

    def test_records_success(self):
        sw, _ = _win()
        sw.record_success()
        assert sw.total() == 1
        assert sw.successes() == 1
        assert sw.failures() == 0

    def test_records_failure(self):
        sw, _ = _win()
        sw.record_failure()
        assert sw.total() == 1
        assert sw.failures() == 1
        assert sw.successes() == 0

    def test_mixed_entries(self):
        sw, _ = _win()
        sw.record_success()
        sw.record_failure()
        sw.record_failure()
        assert sw.total() == 3
        assert sw.failures() == 2
        assert sw.successes() == 1

    def test_failure_rate_calculation(self):
        sw, _ = _win()
        sw.record_success()
        sw.record_failure()
        assert sw.failure_rate() == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------

class TestSlidingWindowEviction:
    def test_old_entries_evicted(self):
        sw, clk = _win(seconds=5.0)
        sw.record_failure()        # t=0
        clk.advance(6.0)           # move past window
        sw.record_success()        # t=6
        assert sw.total() == 1
        assert sw.failures() == 0

    def test_entry_exactly_at_boundary_evicted(self):
        sw, clk = _win(seconds=5.0)
        sw.record_failure()        # t=0
        clk.advance(5.0)           # exactly at boundary
        assert sw.total() == 0

    def test_entry_just_inside_window_retained(self):
        sw, clk = _win(seconds=5.0)
        sw.record_failure()        # t=0
        clk.advance(4.99)
        assert sw.total() == 1

    def test_partial_eviction(self):
        sw, clk = _win(seconds=5.0)
        sw.record_failure()        # t=0
        clk.advance(3.0)
        sw.record_success()        # t=3
        clk.advance(3.0)           # t=6 — first entry evicted
        assert sw.total() == 1
        assert sw.successes() == 1


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestSlidingWindowReset:
    def test_reset_clears_all_entries(self):
        sw, _ = _win()
        sw.record_success()
        sw.record_failure()
        sw.reset()
        assert sw.total() == 0
        assert sw.failure_rate() is None
