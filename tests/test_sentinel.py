"""Tests for retryable.sentinel."""
import time
import pytest

from retryable.sentinel import (
    RetrySentinel,
    SentinelKind,
    SentinelRaised,
)


class TestRetrySentinelConstructors:
    def test_skip_kind(self):
        s = RetrySentinel.skip()
        assert s.kind is SentinelKind.SKIP

    def test_skip_stores_reason(self):
        s = RetrySentinel.skip(reason="not ready")
        assert s.reason == "not ready"

    def test_abort_kind(self):
        s = RetrySentinel.abort()
        assert s.kind is SentinelKind.ABORT

    def test_abort_stores_reason(self):
        s = RetrySentinel.abort(reason="fatal")
        assert s.reason == "fatal"

    def test_succeed_kind(self):
        s = RetrySentinel.succeed(value=42)
        assert s.kind is SentinelKind.SUCCEED

    def test_succeed_stores_value(self):
        s = RetrySentinel.succeed(value="ok")
        assert s.value == "ok"

    def test_succeed_default_value_is_none(self):
        s = RetrySentinel.succeed()
        assert s.value is None

    def test_timestamp_is_recent(self):
        before = time.monotonic()
        s = RetrySentinel.skip()
        after = time.monotonic()
        assert before <= s.timestamp <= after


class TestRetrySentinelPredicates:
    def test_is_skip_true(self):
        assert RetrySentinel.skip().is_skip() is True

    def test_is_skip_false_for_abort(self):
        assert RetrySentinel.abort().is_skip() is False

    def test_is_abort_true(self):
        assert RetrySentinel.abort().is_abort() is True

    def test_is_abort_false_for_succeed(self):
        assert RetrySentinel.succeed().is_abort() is False

    def test_is_succeed_true(self):
        assert RetrySentinel.succeed(value=1).is_succeed() is True

    def test_is_succeed_false_for_skip(self):
        assert RetrySentinel.skip().is_succeed() is False


class TestSentinelRaised:
    def test_stores_sentinel(self):
        s = RetrySentinel.abort(reason="boom")
        exc = SentinelRaised(s)
        assert exc.sentinel is s

    def test_is_exception_subclass(self):
        assert issubclass(SentinelRaised, Exception)

    def test_can_be_raised_and_caught(self):
        s = RetrySentinel.succeed(value=99)
        with pytest.raises(SentinelRaised) as exc_info:
            raise SentinelRaised(s)
        assert exc_info.value.sentinel.value == 99

    def test_str_contains_sentinel_repr(self):
        s = RetrySentinel.skip(reason="waiting")
        exc = SentinelRaised(s)
        assert "SKIP" in str(exc)
