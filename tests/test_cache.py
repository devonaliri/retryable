"""Tests for retryable.cache."""
from __future__ import annotations

import time
import pytest

from retryable.cache import CacheEntry, RetryCache


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

class TestCacheEntry:
    def test_not_expired_without_ttl(self):
        entry = CacheEntry(value=42)
        assert entry.is_expired is False

    def test_not_expired_before_ttl(self):
        entry = CacheEntry(value=42, ttl=10.0)
        assert entry.is_expired is False

    def test_expired_after_ttl(self, monkeypatch):
        start = time.monotonic()
        monkeypatch.setattr("retryable.cache.time.monotonic", lambda: start + 5.0)
        entry = CacheEntry(value=42, ttl=3.0)
        # Simulate time passing beyond ttl
        monkeypatch.setattr("retryable.cache.time.monotonic", lambda: start + 10.0)
        assert entry.is_expired is True


# ---------------------------------------------------------------------------
# RetryCache construction
# ---------------------------------------------------------------------------

class TestRetryCacheInit:
    def test_defaults(self):
        c = RetryCache()
        assert c.ttl is None
        assert c.max_size == 256

    def test_custom_values(self):
        c = RetryCache(ttl=30.0, max_size=10)
        assert c.ttl == 30.0
        assert c.max_size == 10

    def test_zero_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl"):
            RetryCache(ttl=0)

    def test_negative_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl"):
            RetryCache(ttl=-1.0)

    def test_zero_max_size_raises(self):
        with pytest.raises(ValueError, match="max_size"):
            RetryCache(max_size=0)


# ---------------------------------------------------------------------------
# get / put / invalidate / clear
# ---------------------------------------------------------------------------

class TestRetryCacheOperations:
    def test_miss_on_empty(self):
        c = RetryCache()
        hit, val = c.get((1,), {})
        assert hit is False
        assert val is None

    def test_hit_after_put(self):
        c = RetryCache()
        c.put((1,), {}, "result")
        hit, val = c.get((1,), {})
        assert hit is True
        assert val == "result"

    def test_different_args_miss(self):
        c = RetryCache()
        c.put((1,), {}, "result")
        hit, _ = c.get((2,), {})
        assert hit is False

    def test_kwargs_included_in_key(self):
        c = RetryCache()
        c.put((), {"x": 1}, "a")
        hit1, v1 = c.get((), {"x": 1})
        hit2, v2 = c.get((), {"x": 2})
        assert hit1 is True and v1 == "a"
        assert hit2 is False

    def test_invalidate_removes_entry(self):
        c = RetryCache()
        c.put((1,), {}, "v")
        removed = c.invalidate((1,), {})
        assert removed is True
        hit, _ = c.get((1,), {})
        assert hit is False

    def test_invalidate_missing_returns_false(self):
        c = RetryCache()
        assert c.invalidate((99,), {}) is False

    def test_clear_empties_store(self):
        c = RetryCache()
        c.put((1,), {}, 1)
        c.put((2,), {}, 2)
        c.clear()
        assert len(c) == 0

    def test_evicts_oldest_when_full(self):
        c = RetryCache(max_size=2)
        c.put((1,), {}, "a")
        c.put((2,), {}, "b")
        c.put((3,), {}, "c")  # should evict (1,)
        assert len(c) == 2
        hit, _ = c.get((1,), {})
        assert hit is False

    def test_wrap_caches_result(self):
        calls = []

        def fn(x):
            calls.append(x)
            return x * 2

        c = RetryCache()
        wrapped = c.wrap(fn)
        assert wrapped(5) == 10
        assert wrapped(5) == 10  # from cache
        assert len(calls) == 1
