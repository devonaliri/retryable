"""Tests for the retry decorator core behaviour."""
import pytest
from unittest.mock import MagicMock

from retryable.decorator import retry
from retryable.backoff import constant, exponential
from retryable.predicates import on_exception, on_all_exceptions
from retryable.exceptions import RetryLimitExceeded, NonRetryableError


class TestRetryBasic:
    def test_returns_value_on_first_success(self):
        @retry(max_attempts=3)
        def fn():
            return 99

        assert fn() == 99

    def test_retries_until_success(self):
        attempts = []

        @retry(max_attempts=5, backoff=constant(0))
        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("not yet")
            return "done"

        assert fn() == "done"
        assert len(attempts) == 3

    def test_raises_retry_limit_exceeded_after_max_attempts(self):
        @retry(max_attempts=3, backoff=constant(0))
        def fn():
            raise RuntimeError("fail")

        with pytest.raises(RetryLimitExceeded) as exc_info:
            fn()
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, RuntimeError)

    def test_reraise_option_raises_original_exception(self):
        @retry(max_attempts=2, backoff=constant(0), reraise=True)
        def fn():
            raise KeyError("original")

        with pytest.raises(KeyError, match="original"):
            fn()


class TestRetryPredicate:
    def test_non_retryable_exception_raises_immediately(self):
        call_count = [0]

        @retry(
            max_attempts=5,
            backoff=constant(0),
            predicate=on_exception(ValueError),
        )
        def fn():
            call_count[0] += 1
            raise TypeError("not retryable")

        with pytest.raises(NonRetryableError):
            fn()
        assert call_count[0] == 1

    def test_retryable_exception_retries_fully(self):
        call_count = [0]

        @retry(
            max_attempts=3,
            backoff=constant(0),
            predicate=on_exception(ValueError),
        )
        def fn():
            call_count[0] += 1
            raise ValueError("retryable")

        with pytest.raises(RetryLimitExceeded):
            fn()
        assert call_count[0] == 3


class TestRetryBackoff:
    def test_exponential_backoff_used(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr("retryable.decorator.time.sleep", lambda s: sleep_calls.append(s))

        @retry(max_attempts=3, backoff=exponential(base=2, initial=1.0, max_delay=100))
        def fn():
            raise RuntimeError("fail")

        with pytest.raises(RetryLimitExceeded):
            fn()

        assert len(sleep_calls) == 2
        assert sleep_calls[0] < sleep_calls[1]

    def test_no_sleep_after_final_attempt(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr("retryable.decorator.time.sleep", lambda s: sleep_calls.append(s))

        @retry(max_attempts=2, backoff=constant(5))
        def fn():
            raise RuntimeError("fail")

        with pytest.raises(RetryLimitExceeded):
            fn()

        assert len(sleep_calls) == 1
