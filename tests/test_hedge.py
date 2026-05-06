"""Unit tests for retryable.hedge."""
from __future__ import annotations

import time
import threading
from unittest.mock import MagicMock

import pytest

from retryable.hedge import HedgeResult, HedgeTimeout, hedged_call


# ---------------------------------------------------------------------------
# HedgeResult
# ---------------------------------------------------------------------------

class TestHedgeResult:
    def test_set_value_returns_true_first_time(self):
        hr = HedgeResult()
        assert hr.set_value(42) is True

    def test_set_value_returns_false_when_already_done(self):
        hr = HedgeResult()
        hr.set_value(1)
        assert hr.set_value(2) is False

    def test_value_accessible_after_set(self):
        hr = HedgeResult()
        hr.set_value("hello")
        assert hr.value == "hello"

    def test_set_exception_causes_value_to_raise(self):
        hr = HedgeResult()
        hr.set_exception(ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            _ = hr.value

    def test_set_exception_returns_false_when_already_done(self):
        hr = HedgeResult()
        hr.set_value(0)
        assert hr.set_exception(RuntimeError()) is False

    def test_wait_returns_true_when_done(self):
        hr = HedgeResult()
        hr.set_value(99)
        assert hr.wait(timeout=1.0) is True

    def test_wait_returns_false_on_timeout(self):
        hr = HedgeResult()
        assert hr.wait(timeout=0.01) is False


# ---------------------------------------------------------------------------
# hedged_call
# ---------------------------------------------------------------------------

class TestHedgedCall:
    def test_returns_value_from_fast_fn(self):
        result = hedged_call(lambda: 7, (), {}, hedge_delay=10)
        assert result == 7

    def test_negative_hedge_delay_raises(self):
        with pytest.raises(ValueError):
            hedged_call(lambda: 1, (), {}, hedge_delay=-0.1)

    def test_exception_propagates(self):
        def boom():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError, match="fail"):
            hedged_call(boom, (), {}, hedge_delay=10)

    def test_deadline_exceeded_raises_hedge_timeout(self):
        barrier = threading.Event()

        def slow():
            barrier.wait(timeout=5)
            return 1

        deadline = time.monotonic()  # already expired
        with pytest.raises(HedgeTimeout):
            hedged_call(slow, (), {}, hedge_delay=0.0, deadline=deadline)

        barrier.set()  # unblock thread

    def test_hedge_fires_when_primary_is_slow(self):
        call_count = [0]
        lock = threading.Lock()
        slow_event = threading.Event()

        def fn():
            with lock:
                call_count[0] += 1
                n = call_count[0]
            if n == 1:
                slow_event.wait(timeout=2)
            return "ok"

        result = hedged_call(fn, (), {}, hedge_delay=0.02)
        slow_event.set()
        assert result == "ok"
        assert call_count[0] >= 2

    def test_kwargs_forwarded(self):
        def add(a, b=0):
            return a + b

        assert hedged_call(add, (3,), {"b": 4}, hedge_delay=10) == 7
