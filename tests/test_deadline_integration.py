"""Tests for retryable.deadline_integration."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from retryable.deadline import Deadline, DeadlineExceeded
from retryable.deadline_integration import (
    attach_deadline,
    deadline_policy,
    _make_before_hook,
    _make_after_hook,
)
from retryable.policy import RetryPolicy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SteppingClock:
    def __init__(self, start: float = 0.0, step: float = 1.0) -> None:
        self._value = start
        self._step = step

    def __call__(self) -> float:
        v = self._value
        self._value += self._step
        return v


# ---------------------------------------------------------------------------
# Hook unit tests
# ---------------------------------------------------------------------------

class TestBeforeHook:
    def test_starts_deadline_on_first_call(self):
        clock = _SteppingClock()
        d = Deadline(10.0, clock=clock)
        hook = _make_before_hook(d)
        ctx = MagicMock()
        hook(ctx)
        assert d.elapsed > 0

    def test_raises_when_deadline_expired(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        hook = _make_before_hook(d)
        ctx = MagicMock()
        with pytest.raises(DeadlineExceeded):
            hook(ctx)  # start=0; elapsed check → 20 > 5

    def test_hook_name(self):
        d = Deadline(5.0)
        hook = _make_before_hook(d)
        assert hook.__name__ == "deadline_before_hook"


class TestAfterHook:
    def test_does_not_raise_within_budget(self):
        clock = _SteppingClock(start=0.0, step=1.0)
        d = Deadline(10.0, clock=clock)
        d.start()  # start=0
        hook = _make_after_hook(d)
        hook(MagicMock(), MagicMock())  # elapsed=1 < 10 → no raise

    def test_raises_when_expired(self):
        clock = _SteppingClock(start=0.0, step=20.0)
        d = Deadline(5.0, clock=clock)
        d.start()  # start=0; is_expired check → elapsed=20
        hook = _make_after_hook(d)
        with pytest.raises(DeadlineExceeded):
            hook(MagicMock(), MagicMock())

    def test_hook_name(self):
        d = Deadline(5.0)
        hook = _make_after_hook(d)
        assert hook.__name__ == "deadline_after_hook"


# ---------------------------------------------------------------------------
# attach_deadline
# ---------------------------------------------------------------------------

class TestAttachDeadline:
    def test_returns_same_policy(self):
        policy = RetryPolicy(max_attempts=3)
        d = Deadline(10.0)
        result = attach_deadline(policy, d)
        assert result is policy

    def test_hooks_registered(self):
        policy = RetryPolicy(max_attempts=3)
        d = Deadline(10.0)
        before_count = len(policy.hooks._before)
        after_count = len(policy.hooks._after)
        attach_deadline(policy, d)
        assert len(policy.hooks._before) == before_count + 1
        assert len(policy.hooks._after) == after_count + 1


# ---------------------------------------------------------------------------
# deadline_policy factory
# ---------------------------------------------------------------------------

class TestDeadlinePolicy:
    def test_returns_retry_policy(self):
        p = deadline_policy(10.0, max_attempts=3)
        assert isinstance(p, RetryPolicy)

    def test_hooks_attached(self):
        p = deadline_policy(10.0, max_attempts=3)
        names_before = [h.__name__ for h in p.hooks._before]
        names_after = [h.__name__ for h in p.hooks._after]
        assert "deadline_before_hook" in names_before
        assert "deadline_after_hook" in names_after

    def test_successful_call_passes_through(self):
        p = deadline_policy(30.0, max_attempts=3)

        @p
        def ok():
            return 42

        assert ok() == 42

    def test_deadline_exceeded_stops_retries(self):
        """A very short deadline should stop retries before max_attempts."""
        call_count = 0

        # Use a real short deadline; the function always fails.
        p = deadline_policy(0.05, max_attempts=100)

        @p
        def always_fails():
            nonlocal call_count
            call_count += 1
            time.sleep(0.02)
            raise RuntimeError("boom")

        with pytest.raises((DeadlineExceeded, Exception)):
            always_fails()

        assert call_count < 100
