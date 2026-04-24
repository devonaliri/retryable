"""Tests for RetryContext and AttemptRecord."""

import time
import pytest
from retryable.context import RetryContext, AttemptRecord


class TestAttemptRecord:
    def test_succeeded_when_no_exception(self):
        record = AttemptRecord(attempt_number=1)
        assert record.succeeded is True

    def test_failed_when_exception_present(self):
        record = AttemptRecord(attempt_number=1, exception=ValueError("oops"))
        assert record.succeeded is False

    def test_stores_delay(self):
        record = AttemptRecord(attempt_number=2, delay_before=1.5)
        assert record.delay_before == 1.5

    def test_timestamp_is_recent(self):
        before = time.time()
        record = AttemptRecord(attempt_number=1)
        after = time.time()
        assert before <= record.timestamp <= after


class TestRetryContext:
    def _make_context(self, max_attempts=3):
        return RetryContext(max_attempts=max_attempts, exceptions=(Exception,))

    def test_initial_state(self):
        ctx = self._make_context()
        assert ctx.total_attempts == 0
        assert ctx.last_exception is None
        assert ctx.exhausted is False

    def test_record_successful_attempt(self):
        ctx = self._make_context()
        ctx.record_attempt(1)
        assert ctx.total_attempts == 1
        assert len(ctx.failed_attempts) == 0

    def test_record_failed_attempt(self):
        ctx = self._make_context()
        err = RuntimeError("fail")
        ctx.record_attempt(1, exception=err)
        assert ctx.total_attempts == 1
        assert len(ctx.failed_attempts) == 1
        assert ctx.last_exception is err

    def test_last_exception_returns_most_recent(self):
        ctx = self._make_context(max_attempts=5)
        ctx.record_attempt(1, exception=ValueError("first"))
        ctx.record_attempt(2, exception=TypeError("second"))
        assert isinstance(ctx.last_exception, TypeError)

    def test_exhausted_after_max_attempts(self):
        ctx = self._make_context(max_attempts=2)
        assert ctx.exhausted is False
        ctx.record_attempt(1)
        assert ctx.exhausted is False
        ctx.record_attempt(2)
        assert ctx.exhausted is True

    def test_elapsed_increases_over_time(self):
        ctx = self._make_context()
        t1 = ctx.elapsed
        time.sleep(0.05)
        t2 = ctx.elapsed
        assert t2 > t1

    def test_repr_contains_useful_info(self):
        ctx = self._make_context(max_attempts=5)
        ctx.record_attempt(1)
        r = repr(ctx)
        assert "1/5" in r
        assert "elapsed" in r

    def test_failed_attempts_excludes_successes(self):
        ctx = self._make_context(max_attempts=5)
        ctx.record_attempt(1, exception=ValueError("bad"))
        ctx.record_attempt(2)  # success
        ctx.record_attempt(3, exception=RuntimeError("also bad"))
        assert len(ctx.failed_attempts) == 2
        assert ctx.total_attempts == 3
