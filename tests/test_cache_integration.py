"""Integration tests for retryable.cache_integration."""
from __future__ import annotations

import pytest

from retryable.cache import RetryCache
from retryable.cache_integration import cached_call
from retryable.policy import RetryPolicy
from retryable.predicates import on_all_exceptions


class TestCachedCall:
    def test_returns_cached_value_without_calling_fn(self):
        cache = RetryCache()
        cache.put((7,), {}, "cached")

        calls = []

        def fn(x):
            calls.append(x)
            return x

        result = cached_call(fn, cache, (7,), {})
        assert result == "cached"
        assert calls == []

    def test_calls_fn_on_miss_and_stores_result(self):
        cache = RetryCache()

        def fn(x):
            return x + 1

        result = cached_call(fn, cache, (3,), {})
        assert result == 4
        hit, val = cache.get((3,), {})
        assert hit is True
        assert val == 4

    def test_uses_retry_fn_on_miss(self):
        cache = RetryCache()
        fn_calls = []
        retry_calls = []

        def fn(x):
            fn_calls.append(x)
            return x

        def retry_fn(x):
            retry_calls.append(x)
            return x * 10

        result = cached_call(fn, cache, (2,), {}, retry_fn=retry_fn)
        assert result == 20
        assert fn_calls == []
        assert retry_calls == [2]

    def test_second_call_hits_cache(self):
        cache = RetryCache()
        calls = []

        def fn(x):
            calls.append(x)
            return x ** 2

        cached_call(fn, cache, (4,), {})
        cached_call(fn, cache, (4,), {})
        assert len(calls) == 1

    def test_integration_with_retry_policy(self):
        """Verify that a flaky function is retried on miss, then cached."""
        attempt = [0]

        def flaky(x):
            attempt[0] += 1
            if attempt[0] < 3:
                raise ValueError("not yet")
            return x + 100

        policy = RetryPolicy(
            max_attempts=5,
            predicate=on_all_exceptions(),
        )
        retry_fn = policy(flaky)
        cache = RetryCache()

        result = cached_call(flaky, cache, (1,), {}, retry_fn=retry_fn)
        assert result == 101
        assert attempt[0] == 3

        # Second call must come from cache — attempt counter must not grow
        result2 = cached_call(flaky, cache, (1,), {}, retry_fn=retry_fn)
        assert result2 == 101
        assert attempt[0] == 3  # no new attempts
