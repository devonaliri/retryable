"""Tests for retryable.logging and retryable.observer."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.hooks import HookSet
from retryable.logging import make_after_hook, make_before_hook
from retryable.observer import LoggingObserver


def _ctx(attempts: int = 1) -> RetryContext:
    ctx = RetryContext()
    for _ in range(attempts):
        ctx.record_attempt(AttemptRecord(exception=None, delay=0.0))
    return ctx


def _record(ok: bool = True) -> AttemptRecord:
    exc = None if ok else ValueError("boom")
    return AttemptRecord(exception=exc, delay=0.5)


class TestMakeBeforeHook:
    def test_calls_logger_on_invoke(self):
        logger = MagicMock(spec=logging.Logger)
        hook = make_before_hook(logger=logger, level=logging.DEBUG)
        hook(_ctx(0))
        logger.log.assert_called_once()

    def test_log_level_respected(self):
        logger = MagicMock(spec=logging.Logger)
        hook = make_before_hook(logger=logger, level=logging.INFO)
        hook(_ctx(0))
        args = logger.log.call_args[0]
        assert args[0] == logging.INFO

    def test_uses_default_logger_when_none(self):
        hook = make_before_hook()
        # Should not raise
        hook(_ctx(0))


class TestMakeAfterHook:
    def test_logs_success(self):
        logger = MagicMock(spec=logging.Logger)
        hook = make_after_hook(logger=logger)
        hook(_ctx(1), _record(ok=True))
        logger.log.assert_called_once()
        args = logger.log.call_args[0]
        assert args[0] == logging.DEBUG

    def test_logs_failure_at_warning(self):
        logger = MagicMock(spec=logging.Logger)
        hook = make_after_hook(logger=logger, failure_level=logging.WARNING)
        hook(_ctx(1), _record(ok=False))
        args = logger.log.call_args[0]
        assert args[0] == logging.WARNING

    def test_failure_payload_includes_exception(self):
        logger = MagicMock(spec=logging.Logger)
        hook = make_after_hook(logger=logger)
        hook(_ctx(1), _record(ok=False))
        call_args = logger.log.call_args[0]
        payload = call_args[-1]
        assert "exception_type" in payload
        assert payload["exception_type"] == "ValueError"


class TestLoggingObserver:
    def test_attach_registers_hooks(self):
        hs = HookSet()
        obs = LoggingObserver.default()
        obs.attach(hs)
        assert len(hs.before) == 1
        assert len(hs.after) == 1

    def test_custom_logger_passed_through(self):
        logger = MagicMock(spec=logging.Logger)
        obs = LoggingObserver(logger=logger)
        hs = HookSet()
        obs.attach(hs)
        ctx = _ctx(0)
        hs.fire_before_attempt(ctx)
        logger.log.assert_called_once()

    def test_default_classmethod(self):
        obs = LoggingObserver.default()
        assert isinstance(obs, LoggingObserver)
