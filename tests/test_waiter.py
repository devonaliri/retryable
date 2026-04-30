"""Tests for retryable.waiter.Waiter."""

from __future__ import annotations

import pytest

from retryable.waiter import Waiter, default_waiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dry() -> Waiter:
    """Return a dry-run Waiter that never calls real sleep."""
    return Waiter(dry_run=True)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestWaiterInit:
    def test_default_is_not_dry_run(self):
        w = Waiter()
        assert w.dry_run is False

    def test_dry_run_flag_stored(self):
        w = Waiter(dry_run=True)
        assert w.dry_run is True

    def test_non_callable_sleep_fn_raises(self):
        with pytest.raises(TypeError, match="callable"):
            Waiter(sleep_fn="not-a-function")  # type: ignore[arg-type]

    def test_custom_sleep_fn_accepted(self):
        called = []
        w = Waiter(sleep_fn=lambda s: called.append(s))
        w.wait(0.1)
        assert called == [0.1]


# ---------------------------------------------------------------------------
# wait() behaviour
# ---------------------------------------------------------------------------

class TestWaiterWait:
    def test_records_delay_in_dry_run(self):
        w = _dry()
        w.wait(1.5)
        assert w.recorded_delays == [1.5]

    def test_multiple_delays_accumulated(self):
        w = _dry()
        w.wait(1.0)
        w.wait(2.0)
        w.wait(0.5)
        assert w.recorded_delays == [1.0, 2.0, 0.5]

    def test_zero_delay_ignored(self):
        w = _dry()
        w.wait(0)
        assert w.recorded_delays == []

    def test_negative_delay_ignored(self):
        w = _dry()
        w.wait(-3.0)
        assert w.recorded_delays == []

    def test_total_waited_sums_delays(self):
        w = _dry()
        w.wait(1.0)
        w.wait(2.0)
        assert w.total_waited == pytest.approx(3.0)

    def test_total_waited_zero_initially(self):
        w = _dry()
        assert w.total_waited == 0.0

    def test_dry_run_does_not_call_sleep_fn(self):
        calls = []
        w = Waiter(sleep_fn=lambda s: calls.append(s), dry_run=True)
        w.wait(5.0)
        assert calls == []


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestWaiterReset:
    def test_reset_clears_recorded_delays(self):
        w = _dry()
        w.wait(1.0)
        w.wait(2.0)
        w.reset()
        assert w.recorded_delays == []

    def test_reset_clears_total_waited(self):
        w = _dry()
        w.wait(3.0)
        w.reset()
        assert w.total_waited == 0.0


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestWaiterRepr:
    def test_repr_contains_dry_run(self):
        w = _dry()
        assert "dry_run=True" in repr(w)

    def test_repr_contains_total_waited(self):
        w = _dry()
        w.wait(1.25)
        assert "1.250" in repr(w)


# ---------------------------------------------------------------------------
# Module-level default_waiter
# ---------------------------------------------------------------------------

class TestDefaultWaiter:
    def test_is_waiter_instance(self):
        assert isinstance(default_waiter, Waiter)

    def test_not_dry_run(self):
        assert default_waiter.dry_run is False
