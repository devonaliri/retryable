"""Integration tests for pressure hooks wired into RetryPolicy."""
import pytest
from retryable.policy import RetryPolicy
from retryable.pressure import RetryPressure
from retryable.pressure_integration import make_pressure_hookset
from retryable.hooks import HookSet


def _policy(pressure: RetryPressure, max_retries: int = 3) -> RetryPolicy:
    hs = make_pressure_hookset(pressure)
    return RetryPolicy(max_retries=max_retries, hookset=hs)


class TestMakePressureHookSet:
    def test_returns_hookset(self):
        p = RetryPressure()
        hs = make_pressure_hookset(p)
        assert isinstance(hs, HookSet)

    def test_has_before_and_after_hooks(self):
        p = RetryPressure()
        hs = make_pressure_hookset(p)
        assert len(hs._before_hooks) == 1
        assert len(hs._after_hooks) == 1


class TestPressureWithPolicy:
    def test_immediate_success_records_one_call_no_retries(self):
        p = RetryPressure(max_retries=3)
        policy = _policy(p, max_retries=3)

        @policy
        def ok():
            return 42

        result = ok()
        assert result == 42
        snap = p.snapshot()
        assert snap.total_retries == 0
        assert snap.active_calls == 0

    def test_retried_success_records_retries(self):
        p = RetryPressure(max_retries=3)
        policy = _policy(p, max_retries=3)
        calls = {"n": 0}

        @policy
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("boom")
            return "ok"

        flaky()
        snap = p.snapshot()
        assert snap.total_retries == 2

    def test_metadata_key_populated_after_call(self):
        """The last RetryContext should carry a PressureSnapshot in metadata."""
        from retryable.pressure import PressureSnapshot
        p = RetryPressure(max_retries=3)
        captured = []

        def capture_after(ctx, record):
            if "pressure" in ctx.metadata:
                captured.append(ctx.metadata["pressure"])

        hs = make_pressure_hookset(p)
        hs._after_hooks.append(capture_after)
        policy = RetryPolicy(max_retries=3, hookset=hs)

        @policy
        def ok():
            return 1

        ok()
        assert len(captured) >= 1
        assert isinstance(captured[-1], PressureSnapshot)

    def test_custom_metadata_key(self):
        from retryable.pressure import PressureSnapshot
        p = RetryPressure()
        captured = []

        def capture_after(ctx, record):
            if "load" in ctx.metadata:
                captured.append(ctx.metadata["load"])

        hs = make_pressure_hookset(p, metadata_key="load")
        hs._after_hooks.append(capture_after)
        policy = RetryPolicy(max_retries=2, hookset=hs)

        @policy
        def ok():
            return 0

        ok()
        assert captured and isinstance(captured[-1], PressureSnapshot)
