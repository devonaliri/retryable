"""Tests for retryable.aggregator."""
from __future__ import annotations

import pytest

from retryable.aggregator import OperationStats, RetryAggregator
from retryable.context import AttemptRecord, RetryContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(attempts):
    """Build a RetryContext with pre-loaded AttemptRecord objects."""
    ctx = RetryContext()
    for exc in attempts:
        ctx.record_attempt(exc, delay=0.0)
    return ctx


def _ok():
    return _make_ctx([None])


def _failed_once():
    return _make_ctx([ValueError("boom"), None])


def _all_failed():
    return _make_ctx([RuntimeError("x"), RuntimeError("y")])


# ---------------------------------------------------------------------------
# OperationStats
# ---------------------------------------------------------------------------

class TestOperationStats:
    def test_success_rate_none_when_no_calls(self):
        s = OperationStats(name="op")
        assert s.success_rate is None

    def test_average_attempts_none_when_no_calls(self):
        s = OperationStats(name="op")
        assert s.average_attempts is None

    def test_success_rate_computed(self):
        s = OperationStats(name="op", total_calls=4, total_successes=3)
        assert s.success_rate == pytest.approx(0.75)

    def test_average_attempts_computed(self):
        s = OperationStats(name="op", total_calls=2, total_attempts=6)
        assert s.average_attempts == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# RetryAggregator
# ---------------------------------------------------------------------------

class TestRetryAggregatorInit:
    def test_no_operations_initially(self):
        agg = RetryAggregator()
        assert agg.operation_names == []

    def test_get_unknown_returns_none(self):
        agg = RetryAggregator()
        assert agg.get("missing") is None


class TestRetryAggregatorRecord:
    def test_records_successful_call(self):
        agg = RetryAggregator()
        agg.record("fetch", _ok())
        stats = agg.get("fetch")
        assert stats.total_calls == 1
        assert stats.total_successes == 1
        assert stats.total_failures == 0

    def test_records_failed_call(self):
        agg = RetryAggregator()
        agg.record("fetch", _all_failed())
        stats = agg.get("fetch")
        assert stats.total_failures == 1
        assert stats.total_successes == 0

    def test_accumulates_attempts(self):
        agg = RetryAggregator()
        agg.record("fetch", _ok())          # 1 attempt
        agg.record("fetch", _failed_once()) # 2 attempts
        assert agg.get("fetch").total_attempts == 3

    def test_exception_counts_tracked(self):
        agg = RetryAggregator()
        agg.record("fetch", _failed_once())
        assert agg.get("fetch").exception_counts.get("ValueError") == 1

    def test_multiple_operations_tracked_separately(self):
        agg = RetryAggregator()
        agg.record("a", _ok())
        agg.record("b", _all_failed())
        assert agg.get("a").total_successes == 1
        assert agg.get("b").total_failures == 1

    def test_operation_names_sorted(self):
        agg = RetryAggregator()
        agg.record("zebra", _ok())
        agg.record("alpha", _ok())
        assert agg.operation_names == ["alpha", "zebra"]


class TestRetryAggregatorReset:
    def test_reset_single_operation(self):
        agg = RetryAggregator()
        agg.record("fetch", _ok())
        agg.reset("fetch")
        assert agg.get("fetch") is None

    def test_reset_all_operations(self):
        agg = RetryAggregator()
        agg.record("a", _ok())
        agg.record("b", _ok())
        agg.reset()
        assert agg.operation_names == []

    def test_reset_unknown_name_is_noop(self):
        agg = RetryAggregator()
        agg.reset("nonexistent")  # should not raise
