"""Integration tests for checkpoint hooks wired into the retry decorator."""
import pytest

from retryable.checkpoint import RetryCheckpoint
from retryable.checkpoint_integration import make_checkpoint_hookset, resume_attempts
from retryable.context import RetryContext, AttemptRecord


def _make_ctx(attempts: int = 0) -> RetryContext:
    ctx = RetryContext()
    for _ in range(attempts):
        ctx.record_attempt(AttemptRecord(exception=RuntimeError("boom"), delay=0.1))
    return ctx


def _make_failed_record(msg: str = "err") -> AttemptRecord:
    return AttemptRecord(exception=RuntimeError(msg), delay=0.0)


def _make_ok_record() -> AttemptRecord:
    return AttemptRecord(exception=None, delay=0.0)


class TestCheckpointHookSet:
    def test_saves_on_failure(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        hooks = make_checkpoint_hookset(cp, key="task1")
        ctx = _make_ctx(1)
        hooks.fire_after_attempt(ctx, _make_failed_record())
        assert cp.exists("task1")

    def test_saved_data_has_correct_attempts(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        hooks = make_checkpoint_hookset(cp, key="task2")
        ctx = _make_ctx(3)
        hooks.fire_after_attempt(ctx, _make_failed_record("oops"))
        data = cp.load("task2")
        assert data.attempts == 3
        assert data.last_exception_type == "RuntimeError"
        assert "oops" in data.last_exception_message

    def test_clears_on_success(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        hooks = make_checkpoint_hookset(cp, key="task3")
        ctx = _make_ctx(2)
        # first a failure to create the file
        hooks.fire_after_attempt(ctx, _make_failed_record())
        assert cp.exists("task3")
        # then success clears it
        hooks.fire_after_attempt(ctx, _make_ok_record())
        assert not cp.exists("task3")

    def test_no_file_created_on_immediate_success(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        hooks = make_checkpoint_hookset(cp, key="task4")
        ctx = _make_ctx(0)
        hooks.fire_after_attempt(ctx, _make_ok_record())
        assert not cp.exists("task4")


class TestResumeAttempts:
    def test_returns_zero_when_no_checkpoint(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        assert resume_attempts(cp, "missing") == 0

    def test_returns_stored_attempts(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        hooks = make_checkpoint_hookset(cp, key="resume1")
        ctx = _make_ctx(5)
        hooks.fire_after_attempt(ctx, _make_failed_record())
        assert resume_attempts(cp, "resume1") == 5
