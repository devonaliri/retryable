"""Tests for the HookSet lifecycle hook system."""
import pytest
from unittest.mock import MagicMock, call

from retryable.hooks import HookSet, on_retry, EMPTY_HOOKS
from retryable.context import RetryContext, AttemptRecord
from retryable.decorator import retry
from retryable.exceptions import RetryLimitExceeded


def _make_ctx():
    def dummy(): pass
    return RetryContext(func=dummy, max_attempts=3)


def _make_record(n=1):
    r = AttemptRecord(attempt_number=n, delay=0.0)
    return r


class TestHookSet:
    def test_fires_before_attempt(self):
        hook = MagicMock()
        hs = HookSet(before_attempt=hook)
        ctx, rec = _make_ctx(), _make_record()
        hs.fire_before_attempt(ctx, rec)
        hook.assert_called_once_with(ctx, rec)

    def test_fires_after_attempt(self):
        hook = MagicMock()
        hs = HookSet(after_attempt=hook)
        ctx, rec = _make_ctx(), _make_record()
        hs.fire_after_attempt(ctx, rec)
        hook.assert_called_once_with(ctx, rec)

    def test_fires_on_failure(self):
        hook = MagicMock()
        hs = HookSet(on_failure=hook)
        ctx, rec = _make_ctx(), _make_record()
        hs.fire_on_failure(ctx, rec)
        hook.assert_called_once_with(ctx, rec)

    def test_fires_on_success(self):
        hook = MagicMock()
        hs = HookSet(on_success=hook)
        ctx, rec = _make_ctx(), _make_record()
        hs.fire_on_success(ctx, rec)
        hook.assert_called_once_with(ctx, rec)

    def test_empty_hooks_do_not_raise(self):
        ctx, rec = _make_ctx(), _make_record()
        EMPTY_HOOKS.fire_before_attempt(ctx, rec)
        EMPTY_HOOKS.fire_after_attempt(ctx, rec)
        EMPTY_HOOKS.fire_on_failure(ctx, rec)
        EMPTY_HOOKS.fire_on_success(ctx, rec)

    def test_on_retry_is_identity(self):
        fn = lambda ctx, rec: None
        assert on_retry(fn) is fn


class TestHooksIntegration:
    def test_success_hook_called_on_success(self):
        success_hook = MagicMock()
        hs = HookSet(on_success=success_hook)

        @retry(max_attempts=3, hooks=hs)
        def always_ok():
            return 42

        result = always_ok()
        assert result == 42
        success_hook.assert_called_once()

    def test_failure_hook_called_each_retry(self):
        failure_hook = MagicMock()
        hs = HookSet(on_failure=failure_hook)

        @retry(max_attempts=3, backoff=lambda n: 0, hooks=hs)
        def always_fail():
            raise ValueError("boom")

        with pytest.raises(RetryLimitExceeded):
            always_fail()

        assert failure_hook.call_count == 3

    def test_before_attempt_called_every_attempt(self):
        before_hook = MagicMock()
        hs = HookSet(before_attempt=before_hook)
        calls = []

        @retry(max_attempts=2, backoff=lambda n: 0, hooks=hs)
        def fail_then_pass():
            if len(calls) == 0:
                calls.append(1)
                raise RuntimeError("first")
            return "ok"

        result = fail_then_pass()
        assert result == "ok"
        assert before_hook.call_count == 2
