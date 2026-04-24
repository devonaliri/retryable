"""Tests for retryable.budget.RetryBudget."""

import threading
import pytest

from retryable.budget import RetryBudget


class TestRetryBudgetBasic:
    def test_initial_tokens_equal_capacity(self):
        b = RetryBudget(5)
        assert b.available == 5

    def test_capacity_property(self):
        b = RetryBudget(10)
        assert b.capacity == 10

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            RetryBudget(0)

    def test_consume_returns_true_when_tokens_available(self):
        b = RetryBudget(3)
        assert b.consume() is True

    def test_consume_decrements_available(self):
        b = RetryBudget(3)
        b.consume()
        assert b.available == 2

    def test_consume_returns_false_when_exhausted(self):
        b = RetryBudget(1)
        b.consume()
        assert b.consume() is False

    def test_available_never_goes_below_zero(self):
        b = RetryBudget(1)
        b.consume()
        b.consume()
        assert b.available == 0

    def test_reset_restores_full_capacity(self):
        b = RetryBudget(4)
        b.consume()
        b.consume()
        b.reset()
        assert b.available == 4


class TestRetryBudgetRefill:
    def test_no_refill_when_refill_every_is_none(self):
        b = RetryBudget(3)
        b.consume()
        b.consume()
        b.record_success()
        assert b.available == 1  # unchanged

    def test_refill_after_n_successes(self):
        b = RetryBudget(5, refill_every=2)
        b.consume()
        b.consume()
        b.consume()
        b.record_success()
        b.record_success()  # triggers refill
        assert b.available == 5

    def test_success_counter_resets_after_refill(self):
        b = RetryBudget(4, refill_every=2)
        b.consume()
        b.record_success()
        b.record_success()  # refill #1
        b.consume()
        b.consume()
        b.consume()
        b.record_success()
        b.record_success()  # refill #2
        assert b.available == 4

    def test_partial_successes_do_not_refill(self):
        b = RetryBudget(5, refill_every=3)
        b.consume()
        b.consume()
        b.record_success()
        b.record_success()
        assert b.available == 3  # not yet refilled


class TestRetryBudgetThreadSafety:
    def test_concurrent_consume_never_over_drafts(self):
        capacity = 50
        b = RetryBudget(capacity)
        results = []

        def worker():
            results.append(b.consume())

        threads = [threading.Thread(target=worker) for _ in range(capacity * 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(True) == capacity
        assert results.count(False) == capacity
        assert b.available == 0
