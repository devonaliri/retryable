"""Tests for retryable.metrics."""
import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.metrics import RetryMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(exceptions=()) -> RetryContext:
    """Build a RetryContext whose history reflects the given exception sequence."""
    ctx = RetryContext()
    for exc in exceptions:
        ctx.record_attempt(delay=0.0, exception=exc)
    # Final successful attempt (no exception)
    ctx.record_attempt(delay=0.0, exception=None)
    return ctx


def _make_failed_ctx(exceptions=(ValueError(),)) -> RetryContext:
    """Build a RetryContext that ends in failure."""
    ctx = RetryContext()
    for exc in exceptions:
        ctx.record_attempt(delay=0.0, exception=exc)
    return ctx


# ---------------------------------------------------------------------------
# RetryMetrics
# ---------------------------------------------------------------------------

class TestRetryMetricsInitial:
    def test_zero_state(self):
        m = RetryMetrics()
        assert m.total_calls == 0
        assert m.total_attempts == 0
        assert m.total_successes == 0
        assert m.total_failures == 0
        assert m.exception_counts == {}
        assert m.attempt_counts == []

    def test_success_rate_none_when_no_calls(self):
        assert RetryMetrics().success_rate is None

    def test_average_attempts_none_when_no_calls(self):
        assert RetryMetrics().average_attempts is None


class TestRetryMetricsRecord:
    def test_single_success_on_first_try(self):
        m = RetryMetrics()
        ctx = _make_ctx(exceptions=[])
        m.record(ctx)
        assert m.total_calls == 1
        assert m.total_successes == 1
        assert m.total_failures == 0
        assert m.total_attempts == 1

    def test_success_after_retries(self):
        m = RetryMetrics()
        ctx = _make_ctx(exceptions=[ValueError(), ValueError()])
        m.record(ctx)
        assert m.total_attempts == 3
        assert m.total_successes == 1

    def test_failure_recorded(self):
        m = RetryMetrics()
        ctx = _make_failed_ctx(exceptions=[RuntimeError(), RuntimeError()])
        m.record(ctx)
        assert m.total_failures == 1
        assert m.total_successes == 0

    def test_exception_counts_aggregated(self):
        m = RetryMetrics()
        m.record(_make_ctx(exceptions=[ValueError(), TypeError()]))
        assert m.exception_counts["ValueError"] == 1
        assert m.exception_counts["TypeError"] == 1

    def test_exception_counts_accumulate_across_calls(self):
        m = RetryMetrics()
        m.record(_make_ctx(exceptions=[ValueError()]))
        m.record(_make_ctx(exceptions=[ValueError()]))
        assert m.exception_counts["ValueError"] == 2

    def test_success_rate_calculation(self):
        m = RetryMetrics()
        m.record(_make_ctx())          # success
        m.record(_make_failed_ctx())   # failure
        assert m.success_rate == pytest.approx(0.5)

    def test_average_attempts_calculation(self):
        m = RetryMetrics()
        m.record(_make_ctx(exceptions=[]))            # 1 attempt
        m.record(_make_ctx(exceptions=[ValueError()])) # 2 attempts
        assert m.average_attempts == pytest.approx(1.5)


class TestRetryMetricsReset:
    def test_reset_clears_all_state(self):
        m = RetryMetrics()
        m.record(_make_ctx(exceptions=[ValueError()]))
        m.reset()
        assert m.total_calls == 0
        assert m.total_attempts == 0
        assert m.exception_counts == {}
        assert m.attempt_counts == []
        assert m.success_rate is None
