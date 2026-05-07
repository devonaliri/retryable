"""Integration tests for RetrySignal with HookSet."""
import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.signal import RetrySignal, SignalAction
from retryable.signal_integration import (
    SignalCancelledError,
    _make_after_hook,
    _make_before_hook,
    make_signal_hookset,
)


def _make_ctx(attempts: int = 0) -> RetryContext:
    ctx = RetryContext(fn_name="test_fn")
    for _ in range(attempts):
        ctx.record_attempt(AttemptRecord())
    return ctx


def _make_record() -> AttemptRecord:
    return AttemptRecord()


class TestBeforeHook:
    def test_no_signal_does_nothing(self):
        s = RetrySignal()
        hook = _make_before_hook(s)
        ctx = _make_ctx()
        hook(ctx)  # should not raise

    def test_cancel_signal_raises(self):
        s = RetrySignal()
        s.cancel()
        hook = _make_before_hook(s)
        with pytest.raises(SignalCancelledError):
            hook(_make_ctx(1))

    def test_succeed_signal_does_not_raise_in_before(self):
        s = RetrySignal()
        s.force_success("ok")
        hook = _make_before_hook(s)
        hook(_make_ctx())  # must not raise


class TestAfterHook:
    def test_no_signal_leaves_metadata_clean(self):
        s = RetrySignal()
        hook = _make_after_hook(s)
        ctx = _make_ctx()
        hook(ctx, _make_record())
        assert "__signal_forced_value__" not in ctx.metadata

    def test_succeed_signal_stores_value_in_metadata(self):
        s = RetrySignal()
        s.force_success("forced")
        hook = _make_after_hook(s)
        ctx = _make_ctx()
        hook(ctx, _make_record())
        assert ctx.metadata["__signal_forced_value__"] == "forced"

    def test_cancel_signal_does_not_write_metadata(self):
        s = RetrySignal()
        s.cancel()
        hook = _make_after_hook(s)
        ctx = _make_ctx()
        hook(ctx, _make_record())
        assert "__signal_forced_value__" not in ctx.metadata


class TestMakeSignalHookSet:
    def test_returns_hookset_with_both_hooks(self):
        from retryable.hooks import HookSet
        s = RetrySignal()
        hs = make_signal_hookset(s)
        assert isinstance(hs, HookSet)
        assert len(hs.before_attempt) == 1
        assert len(hs.after_attempt) == 1

    def test_cancelled_error_is_retry_limit_exceeded_subclass(self):
        from retryable.exceptions import RetryLimitExceeded
        assert issubclass(SignalCancelledError, RetryLimitExceeded)
