"""Tests for the retry decorator and backoff strategies."""
import pytest
from unittest.mock import MagicMock, patch

from retryable import retry
from retryable.backoff import constant, linear, exponential


# ---------------------------------------------------------------------------
# Backoff strategy tests
# ---------------------------------------------------------------------------

class TestBackoffStrategies:
    def test_constant_always_same(self):
        s = constant(delay=2.0)
        assert s(1) == 2.0
        assert s(5) == 2.0

    def test_linear_grows(self):
        s = linear(initial=1.0, increment=2.0)
        assert s(1) == 1.0
        assert s(2) == 3.0
        assert s(3) == 5.0

    def test_exponential_grows(self):
        s = exponential(base=2.0, initial=1.0, max_delay=60.0)
        assert s(1) == 1.0
        assert s(2) == 2.0
        assert s(3) == 4.0

    def test_exponential_caps_at_max_delay(self):
        s = exponential(base=2.0, initial=1.0, max_delay=5.0)
        assert s(10) == 5.0


# ---------------------------------------------------------------------------
# Retry decorator tests
# ---------------------------------------------------------------------------

class TestRetryDecorator:
    @patch("retryable.decorator.time.sleep")
    def test_succeeds_on_first_attempt(self, mock_sleep):
        func = MagicMock(return_value="ok")
        decorated = retry(max_attempts=3)(func)
        assert decorated() == "ok"
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("retryable.decorator.time.sleep")
    def test_retries_and_eventually_succeeds(self, mock_sleep):
        func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
        decorated = retry(max_attempts=3, exceptions=ValueError, backoff=constant(0))(func)
        assert decorated() == "ok"
        assert func.call_count == 3

    @patch("retryable.decorator.time.sleep")
    def test_raises_after_max_attempts(self, mock_sleep):
        func = MagicMock(side_effect=ValueError("always fails"))
        decorated = retry(max_attempts=3, exceptions=ValueError, backoff=constant(0))(func)
        with pytest.raises(ValueError, match="always fails"):
            decorated()
        assert func.call_count == 3

    @patch("retryable.decorator.time.sleep")
    def test_on_retry_callback_invoked(self, mock_sleep):
        callback = MagicMock()
        func = MagicMock(side_effect=[RuntimeError("e"), "ok"])
        decorated = retry(max_attempts=2, exceptions=RuntimeError, backoff=constant(0), on_retry=callback)(func)
        decorated()
        callback.assert_called_once()
        attempt, exc = callback.call_args[0]
        assert attempt == 1
        assert isinstance(exc, RuntimeError)

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError):
            retry(max_attempts=0)

    @patch("retryable.decorator.time.sleep")
    def test_does_not_catch_unspecified_exception(self, mock_sleep):
        func = MagicMock(side_effect=KeyError("nope"))
        decorated = retry(max_attempts=3, exceptions=ValueError, backoff=constant(0))(func)
        with pytest.raises(KeyError):
            decorated()
        assert func.call_count == 1
