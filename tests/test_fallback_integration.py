"""Integration tests: Fallback combined with RetryPolicy / @retry decorator."""

import pytest

from retryable.exceptions import RetryLimitExceeded
from retryable.fallback import from_handler, static
from retryable.policy import RetryPolicy


class TestStaticFallbackWithPolicy:
    def test_returns_static_value_after_exhaustion(self):
        calls = {"n": 0}

        def always_fails():
            calls["n"] += 1
            raise RuntimeError("fail")

        policy = RetryPolicy(max_attempts=2, fallback=static("default"))
        result = policy.apply(always_fails)
        assert result == "default"
        assert calls["n"] == 2

    def test_fallback_not_invoked_on_success(self):
        policy = RetryPolicy(max_attempts=3, fallback=static("fallback"))
        result = policy.apply(lambda: "ok")
        assert result == "ok"

    def test_fallback_none_value_returned(self):
        policy = RetryPolicy(max_attempts=1, fallback=static(None))
        result = policy.apply(lambda: (_ for _ in ()).throw(ValueError()))
        assert result is None


class TestHandlerFallbackWithPolicy:
    def test_handler_receives_last_exception(self):
        sentinel = {}

        def handler(exc):
            sentinel["exc"] = exc
            return "recovered"

        policy = RetryPolicy(max_attempts=2, fallback=from_handler(handler))
        result = policy.apply(lambda: (_ for _ in ()).throw(IOError("disk")))
        assert result == "recovered"
        assert isinstance(sentinel["exc"], IOError)

    def test_handler_receives_original_call_args(self):
        received = {}

        def flaky_fn(x, y=0):
            raise ValueError("nope")

        def handler(exc, x, y=0):
            received["x"] = x
            received["y"] = y
            return x + y

        policy = RetryPolicy(max_attempts=1, fallback=from_handler(handler))
        result = policy.apply(flaky_fn, 3, y=7)
        assert result == 10
        assert received == {"x": 3, "y": 7}


class TestNoFallbackRaisesOnExhaustion:
    def test_raises_retry_limit_exceeded_without_fallback(self):
        policy = RetryPolicy(max_attempts=2)
        with pytest.raises(RetryLimitExceeded):
            policy.apply(lambda: (_ for _ in ()).throw(RuntimeError()))


class TestPolicyAsDecorator:
    def test_decorator_uses_fallback(self):
        policy = RetryPolicy(max_attempts=2, fallback=static(-1))

        @policy
        def broken():
            raise TypeError("oops")

        assert broken() == -1
