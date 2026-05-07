"""Unit tests for RetrySignal."""
import pytest

from retryable.signal import RetrySignal, SignalAction


class TestRetrySignalInit:
    def test_default_action_is_none(self):
        s = RetrySignal()
        assert s.action is SignalAction.NONE

    def test_is_not_set_by_default(self):
        assert not RetrySignal().is_set()


class TestRetrySignalCancel:
    def test_cancel_sets_action(self):
        s = RetrySignal()
        s.cancel()
        assert s.action is SignalAction.CANCEL

    def test_is_set_after_cancel(self):
        s = RetrySignal()
        s.cancel()
        assert s.is_set()

    def test_reset_clears_cancel(self):
        s = RetrySignal()
        s.cancel()
        s.reset()
        assert s.action is SignalAction.NONE
        assert not s.is_set()


class TestRetrySignalForceSuccess:
    def test_force_success_sets_action(self):
        s = RetrySignal()
        s.force_success(42)
        assert s.action is SignalAction.SUCCEED

    def test_forced_value_stored(self):
        s = RetrySignal()
        s.force_success("hello")
        assert s.forced_value == "hello"

    def test_forced_value_defaults_to_none(self):
        s = RetrySignal()
        s.force_success()
        assert s.forced_value is None

    def test_reset_clears_forced_value(self):
        s = RetrySignal()
        s.force_success(99)
        s.reset()
        assert s.forced_value is None
        assert s.action is SignalAction.NONE


class TestRetrySignalIdempotentReset:
    def test_double_reset_is_safe(self):
        s = RetrySignal()
        s.reset()
        s.reset()
        assert s.action is SignalAction.NONE

    def test_cancel_overwrites_succeed(self):
        s = RetrySignal()
        s.force_success(1)
        s.cancel()
        assert s.action is SignalAction.CANCEL
