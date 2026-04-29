"""Tests for retryable.snapshot."""

import time
from unittest.mock import MagicMock

import pytest

from retryable.snapshot import RetrySnapshot, take_snapshot
from retryable.context import RetryContext, AttemptRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(records=None):
    ctx = MagicMock(spec=RetryContext)
    records = records or []
    ctx.history.return_value = records
    ctx.total_attempts = len(records)
    ctx.elapsed.return_value = 0.5
    return ctx


def _record(succeeded=True, delay=0.0, exc=None):
    r = MagicMock(spec=AttemptRecord)
    r.succeeded = succeeded
    r.delay = delay
    r.exception = exc
    return r


# ---------------------------------------------------------------------------
# RetrySnapshot unit tests
# ---------------------------------------------------------------------------

class TestRetrySnapshot:
    def test_is_healthy_when_no_failures(self):
        snap = RetrySnapshot(
            total_attempts=3, successful_attempts=3, failed_attempts=0,
            last_delay=0.0, last_exception=None, elapsed=0.1,
        )
        assert snap.is_healthy is True

    def test_not_healthy_when_failures_present(self):
        snap = RetrySnapshot(
            total_attempts=3, successful_attempts=2, failed_attempts=1,
            last_delay=1.0, last_exception=ValueError("boom"), elapsed=0.5,
        )
        assert snap.is_healthy is False

    def test_failure_rate_none_when_no_attempts(self):
        snap = RetrySnapshot(
            total_attempts=0, successful_attempts=0, failed_attempts=0,
            last_delay=0.0, last_exception=None, elapsed=0.0,
        )
        assert snap.failure_rate is None

    def test_failure_rate_calculated_correctly(self):
        snap = RetrySnapshot(
            total_attempts=4, successful_attempts=3, failed_attempts=1,
            last_delay=0.2, last_exception=None, elapsed=0.8,
        )
        assert snap.failure_rate == pytest.approx(0.25)

    def test_str_contains_key_info(self):
        snap = RetrySnapshot(
            total_attempts=2, successful_attempts=1, failed_attempts=1,
            last_delay=0.5, last_exception=None, elapsed=1.2,
        )
        s = str(snap)
        assert "attempts=2" in s
        assert "failed=1" in s
        assert "healthy=False" in s

    def test_frozen_immutable(self):
        snap = RetrySnapshot(
            total_attempts=1, successful_attempts=1, failed_attempts=0,
            last_delay=0.0, last_exception=None, elapsed=0.1,
        )
        with pytest.raises(Exception):
            snap.total_attempts = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# take_snapshot integration
# ---------------------------------------------------------------------------

class TestTakeSnapshot:
    def test_empty_context(self):
        ctx = _make_ctx([])
        snap = take_snapshot(ctx)
        assert snap.total_attempts == 0
        assert snap.successful_attempts == 0
        assert snap.failed_attempts == 0
        assert snap.last_delay == 0.0
        assert snap.last_exception is None
        assert snap.is_healthy is True

    def test_counts_failures_and_successes(self):
        exc = RuntimeError("oops")
        records = [
            _record(succeeded=False, delay=1.0, exc=exc),
            _record(succeeded=False, delay=2.0, exc=exc),
            _record(succeeded=True, delay=0.0),
        ]
        ctx = _make_ctx(records)
        snap = take_snapshot(ctx)
        assert snap.failed_attempts == 2
        assert snap.successful_attempts == 1
        assert snap.total_attempts == 3

    def test_last_delay_from_most_recent_record(self):
        records = [
            _record(succeeded=False, delay=1.0),
            _record(succeeded=True, delay=3.5),
        ]
        ctx = _make_ctx(records)
        snap = take_snapshot(ctx)
        assert snap.last_delay == pytest.approx(3.5)

    def test_last_exception_from_most_recent_record(self):
        exc = ValueError("last")
        records = [
            _record(succeeded=False, exc=RuntimeError("first")),
            _record(succeeded=False, exc=exc),
        ]
        ctx = _make_ctx(records)
        snap = take_snapshot(ctx)
        assert snap.last_exception is exc

    def test_captured_at_is_recent(self):
        before = time.monotonic()
        snap = take_snapshot(_make_ctx([]))
        after = time.monotonic()
        assert before <= snap.captured_at <= after
