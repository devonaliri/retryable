"""Tests for retryable.quota."""
from __future__ import annotations

import pytest

from retryable.quota import QuotaExceeded, RetryQuota


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestRetryQuotaInit:
    def test_valid_construction(self):
        q = RetryQuota(limit=5)
        assert q.limit == 5

    def test_zero_limit_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            RetryQuota(limit=0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            RetryQuota(limit=-3)


# ---------------------------------------------------------------------------
# remaining()
# ---------------------------------------------------------------------------

class TestRetryQuotaRemaining:
    def test_full_quota_before_any_consumption(self):
        q = RetryQuota(limit=3)
        assert q.remaining("svc") == 3

    def test_remaining_decreases_after_consume(self):
        q = RetryQuota(limit=3)
        q.consume("svc")
        assert q.remaining("svc") == 2

    def test_remaining_never_negative(self):
        q = RetryQuota(limit=1)
        q.consume("svc")
        q.consume("svc")  # already exhausted
        assert q.remaining("svc") == 0

    def test_independent_keys(self):
        q = RetryQuota(limit=2)
        q.consume("a")
        assert q.remaining("a") == 1
        assert q.remaining("b") == 2


# ---------------------------------------------------------------------------
# consume()
# ---------------------------------------------------------------------------

class TestRetryQuotaConsume:
    def test_returns_true_while_quota_available(self):
        q = RetryQuota(limit=2)
        assert q.consume("svc") is True
        assert q.consume("svc") is True

    def test_returns_false_when_exhausted(self):
        q = RetryQuota(limit=1)
        q.consume("svc")
        assert q.consume("svc") is False

    def test_does_not_increment_beyond_limit(self):
        q = RetryQuota(limit=1)
        q.consume("svc")
        q.consume("svc")  # denied
        assert q.remaining("svc") == 0


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestRetryQuotaReset:
    def test_reset_specific_key(self):
        q = RetryQuota(limit=2)
        q.consume("a")
        q.consume("b")
        q.reset("a")
        assert q.remaining("a") == 2
        assert q.remaining("b") == 1

    def test_reset_all_keys(self):
        q = RetryQuota(limit=2)
        q.consume("a")
        q.consume("b")
        q.reset()
        assert q.remaining("a") == 2
        assert q.remaining("b") == 2

    def test_reset_unknown_key_is_noop(self):
        q = RetryQuota(limit=2)
        q.reset("nonexistent")  # should not raise
        assert q.remaining("nonexistent") == 2


# ---------------------------------------------------------------------------
# is_exhausted()
# ---------------------------------------------------------------------------

class TestRetryQuotaIsExhausted:
    def test_not_exhausted_initially(self):
        q = RetryQuota(limit=3)
        assert q.is_exhausted("svc") is False

    def test_exhausted_after_limit_reached(self):
        q = RetryQuota(limit=2)
        q.consume("svc")
        q.consume("svc")
        assert q.is_exhausted("svc") is True

    def test_not_exhausted_after_reset(self):
        q = RetryQuota(limit=1)
        q.consume("svc")
        q.reset("svc")
        assert q.is_exhausted("svc") is False


# ---------------------------------------------------------------------------
# QuotaExceeded exception
# ---------------------------------------------------------------------------

class TestQuotaExceeded:
    def test_stores_key_and_limit(self):
        exc = QuotaExceeded(key="payments", limit=10)
        assert exc.key == "payments"
        assert exc.limit == 10

    def test_str_contains_key_and_limit(self):
        exc = QuotaExceeded(key="payments", limit=10)
        msg = str(exc)
        assert "payments" in msg
        assert "10" in msg

    def test_is_exception_subclass(self):
        assert issubclass(QuotaExceeded, Exception)
