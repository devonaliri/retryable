"""Integration tests for retryable.fingerprint_integration."""
from __future__ import annotations

import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.fingerprint import FingerprintRegistry
from retryable.fingerprint_integration import (
    _METADATA_KEY,
    make_fingerprint_hookset,
)


def _make_ctx(fn) -> RetryContext:
    return RetryContext(fn=fn)


def _make_record(*, exc=None) -> AttemptRecord:
    return AttemptRecord(exception=exc)


# ---------------------------------------------------------------------------
# make_fingerprint_hookset
# ---------------------------------------------------------------------------


def test_returns_hookset_and_registry():
    from retryable.hooks import HookSet

    hs, reg = make_fingerprint_hookset()
    assert isinstance(hs, HookSet)
    assert isinstance(reg, FingerprintRegistry)


def test_before_hook_populates_metadata():
    def fn():
        pass

    hs, reg = make_fingerprint_hookset()
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    assert _METADATA_KEY in ctx.metadata
    assert isinstance(ctx.metadata[_METADATA_KEY], str)


def test_before_hook_records_in_registry():
    def fn():
        pass

    hs, reg = make_fingerprint_hookset()
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    fp = ctx.metadata[_METADATA_KEY]
    assert reg.count(fp) == 1


def test_multiple_calls_increment_count():
    def fn():
        pass

    hs, reg = make_fingerprint_hookset()
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    hs.fire_before_attempt(ctx)
    fp = ctx.metadata[_METADATA_KEY]
    assert reg.count(fp) == 2


def test_reuse_existing_registry():
    def fn():
        pass

    existing = FingerprintRegistry()
    hs, reg = make_fingerprint_hookset(registry=existing)
    assert reg is existing
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    fp = ctx.metadata[_METADATA_KEY]
    assert existing.count(fp) == 1


def test_after_hook_sets_fingerprint_when_missing():
    """After hook should add fingerprint if before hook was never called."""

    def fn():
        pass

    hs, reg = make_fingerprint_hookset()
    ctx = _make_ctx(fn)
    record = _make_record()
    hs.fire_after_attempt(ctx, record)
    assert _METADATA_KEY in ctx.metadata


def test_after_hook_does_not_overwrite_existing_fingerprint():
    def fn():
        pass

    hs, reg = make_fingerprint_hookset()
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    original = ctx.metadata[_METADATA_KEY]
    record = _make_record()
    hs.fire_after_attempt(ctx, record)
    assert ctx.metadata[_METADATA_KEY] == original


def test_custom_strategy_propagated():
    def fn():
        pass

    hs, reg = make_fingerprint_hookset(strategy=lambda _ctx: "custom")
    ctx = _make_ctx(fn)
    hs.fire_before_attempt(ctx)
    assert ctx.metadata[_METADATA_KEY] == "custom"
