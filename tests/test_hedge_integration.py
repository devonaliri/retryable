"""Integration tests for retryable.hedge_integration."""
from __future__ import annotations

import threading
import time

import pytest

from retryable.hedge import HedgeTimeout
from retryable.hedge_integration import hedged_wrap, make_hedge_hookset
from retryable.hooks import HookSet
from retryable.context import RetryContext


# ---------------------------------------------------------------------------
# hedged_wrap
# ---------------------------------------------------------------------------

class TestHedgedWrap:
    def test_returns_correct_value(self):
        wrapped = hedged_wrap(lambda x: x * 2, hedge_delay=10)
        assert wrapped(5) == 10

    def test_preserves_function_name(self):
        def my_fn():
            return 1

        wrapped = hedged_wrap(my_fn, hedge_delay=10)
        assert wrapped.__name__ == "my_fn"

    def test_wrapped_attribute_set(self):
        fn = lambda: None  # noqa: E731
        wrapped = hedged_wrap(fn, hedge_delay=10)
        assert wrapped.__wrapped__ is fn

    def test_kwargs_passed_through(self):
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}"

        wrapped = hedged_wrap(greet, hedge_delay=10)
        assert wrapped("World", greeting="Hi") == "Hi, World"

    def test_exception_propagates(self):
        def bad():
            raise ValueError("oops")

        wrapped = hedged_wrap(bad, hedge_delay=10)
        with pytest.raises(ValueError, match="oops"):
            wrapped()

    def test_deadline_triggers_hedge_timeout(self):
        barrier = threading.Event()

        def slow():
            barrier.wait(timeout=5)
            return 1

        wrapped = hedged_wrap(slow, hedge_delay=0.0, deadline_seconds=0.0)
        with pytest.raises(HedgeTimeout):
            wrapped()
        barrier.set()


# ---------------------------------------------------------------------------
# make_hedge_hookset
# ---------------------------------------------------------------------------

class TestMakeHedgeHookset:
    def _make_ctx(self) -> RetryContext:
        ctx = RetryContext(fn_name="test_fn")
        return ctx

    def test_returns_hookset(self):
        hs = make_hedge_hookset()
        assert isinstance(hs, HookSet)

    def test_before_hook_populates_metadata(self):
        hs = make_hedge_hookset(hedge_delay=0.2, deadline_seconds=5.0)
        ctx = self._make_ctx()
        hs.fire_before_attempt(ctx)
        assert "hedge" in ctx.metadata
        assert ctx.metadata["hedge"]["hedge_delay"] == 0.2
        assert ctx.metadata["hedge"]["deadline_seconds"] == 5.0

    def test_before_hook_does_not_overwrite_existing_metadata(self):
        hs = make_hedge_hookset(hedge_delay=0.5)
        ctx = self._make_ctx()
        ctx.metadata["hedge"] = {"hedge_delay": 99.0}
        hs.fire_before_attempt(ctx)
        assert ctx.metadata["hedge"]["hedge_delay"] == 99.0

    def test_after_hook_sets_hedge_timeout_flag_on_timeout(self):
        from retryable.context import AttemptRecord

        hs = make_hedge_hookset()
        ctx = self._make_ctx()
        record = AttemptRecord(exception=HedgeTimeout("timed out"), delay=0.0)
        hs.fire_after_attempt(ctx, record)
        assert ctx.metadata.get("hedge_timeout") is True

    def test_after_hook_does_not_set_flag_on_success(self):
        from retryable.context import AttemptRecord

        hs = make_hedge_hookset()
        ctx = self._make_ctx()
        record = AttemptRecord(exception=None, delay=0.0)
        hs.fire_after_attempt(ctx, record)
        assert "hedge_timeout" not in ctx.metadata
