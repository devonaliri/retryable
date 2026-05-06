"""Unit tests for retryable.fingerprint."""
from __future__ import annotations

import pytest

from retryable.context import RetryContext
from retryable.fingerprint import (
    FingerprintRegistry,
    _sanitise,
    default_fingerprint,
    hashed_fingerprint,
)


def _make_ctx(fn) -> RetryContext:
    ctx = RetryContext(fn=fn)
    return ctx


# ---------------------------------------------------------------------------
# _sanitise
# ---------------------------------------------------------------------------


def test_sanitise_lowercases():
    assert _sanitise("MyModule") == "mymodule"


def test_sanitise_replaces_dots_and_spaces():
    assert _sanitise("my.module name") == "my_module_name"


def test_sanitise_strips_leading_trailing_underscores():
    assert _sanitise("__dunder__") == "dunder"


# ---------------------------------------------------------------------------
# default_fingerprint
# ---------------------------------------------------------------------------


def test_default_fingerprint_contains_function_name():
    def my_operation():
        pass

    ctx = _make_ctx(my_operation)
    fp = default_fingerprint(ctx)
    assert "my_operation" in fp


def test_default_fingerprint_is_string():
    def fn():
        pass

    assert isinstance(default_fingerprint(_make_ctx(fn)), str)


# ---------------------------------------------------------------------------
# hashed_fingerprint
# ---------------------------------------------------------------------------


def test_hashed_fingerprint_length():
    def fn():
        pass

    fp = hashed_fingerprint(_make_ctx(fn), length=12)
    assert len(fp) == 12


def test_hashed_fingerprint_default_length():
    def fn():
        pass

    fp = hashed_fingerprint(_make_ctx(fn))
    assert len(fp) == 8


def test_hashed_fingerprint_is_hex():
    def fn():
        pass

    fp = hashed_fingerprint(_make_ctx(fn))
    int(fp, 16)  # raises ValueError if not valid hex


# ---------------------------------------------------------------------------
# FingerprintRegistry
# ---------------------------------------------------------------------------


def test_registry_count_zero_for_unknown():
    reg = FingerprintRegistry()
    assert reg.count("nonexistent") == 0


def test_registry_record_increments_count():
    def fn():
        pass

    reg = FingerprintRegistry()
    ctx = _make_ctx(fn)
    fp = reg.record(ctx)
    assert reg.count(fp) == 1
    reg.record(ctx)
    assert reg.count(fp) == 2


def test_registry_latest_returns_context():
    def fn():
        pass

    reg = FingerprintRegistry()
    ctx = _make_ctx(fn)
    fp = reg.record(ctx)
    assert reg.latest(fp) is ctx


def test_registry_latest_none_for_unknown():
    reg = FingerprintRegistry()
    assert reg.latest("ghost") is None


def test_all_fingerprints_sorted():
    def alpha():
        pass

    def beta():
        pass

    reg = FingerprintRegistry()
    reg.record(_make_ctx(beta))
    reg.record(_make_ctx(alpha))
    fps = reg.all_fingerprints
    assert fps == sorted(fps)


def test_custom_strategy_used():
    def fn():
        pass

    reg = FingerprintRegistry(strategy=lambda _ctx: "fixed_key")
    fp = reg.record(_make_ctx(fn))
    assert fp == "fixed_key"
    assert reg.count("fixed_key") == 1
