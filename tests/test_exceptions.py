"""Tests for retryable.exceptions module."""

import pytest

from retryable.exceptions import (
    NonRetryableError,
    RetryError,
    RetryLimitExceeded,
    is_non_retryable,
    is_retryable,
)


class TestRetryError:
    def test_stores_last_exception_and_attempts(self):
        original = ValueError("something went wrong")
        err = RetryError("all retries failed", last_exception=original, attempts=3)
        assert err.last_exception is original
        assert err.attempts == 3

    def test_str_includes_context(self):
        original = ConnectionError("timeout")
        err = RetryError("failed", last_exception=original, attempts=5)
        result = str(err)
        assert "ConnectionError" in result
        assert "timeout" in result
        assert "5" in result

    def test_is_exception_subclass(self):
        original = RuntimeError("boom")
        err = RetryError("failed", last_exception=original, attempts=1)
        assert isinstance(err, Exception)


class TestRetryLimitExceeded:
    def test_is_subclass_of_retry_error(self):
        original = IOError("disk full")
        err = RetryLimitExceeded("limit hit", last_exception=original, attempts=10)
        assert isinstance(err, RetryError)

    def test_stores_attempts(self):
        original = TimeoutError()
        err = RetryLimitExceeded("limit", last_exception=original, attempts=7)
        assert err.attempts == 7


class TestNonRetryableError:
    def test_stores_original_exception(self):
        original = PermissionError("access denied")
        err = NonRetryableError("not retryable", original_exception=original)
        assert err.original_exception is original

    def test_is_exception_subclass(self):
        original = KeyError("missing")
        err = NonRetryableError("skip", original_exception=original)
        assert isinstance(err, Exception)


class TestIsRetryable:
    def test_single_matching_type(self):
        assert is_retryable(ValueError("x"), ValueError) is True

    def test_single_non_matching_type(self):
        assert is_retryable(TypeError("x"), ValueError) is False

    def test_list_with_matching_type(self):
        assert is_retryable(ConnectionError("x"), [ValueError, ConnectionError]) is True

    def test_list_with_no_match(self):
        assert is_retryable(KeyError("x"), [ValueError, TypeError]) is False

    def test_tuple_with_matching_type(self):
        assert is_retryable(OSError("x"), (OSError, RuntimeError)) is True


class TestIsNonRetryable:
    def test_single_matching_type(self):
        assert is_non_retryable(PermissionError("x"), PermissionError) is True

    def test_single_non_matching_type(self):
        assert is_non_retryable(ValueError("x"), PermissionError) is False

    def test_list_with_matching_type(self):
        assert is_non_retryable(KeyboardInterrupt(), [KeyboardInterrupt, SystemExit]) is True

    def test_list_with_no_match(self):
        assert is_non_retryable(RuntimeError("x"), [ValueError, TypeError]) is False
