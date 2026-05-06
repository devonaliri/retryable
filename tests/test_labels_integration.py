"""Integration tests for attach_labels wired into a real RetryPolicy."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryable.hooks import HookSet
from retryable.labels_integration import attach_labels


def _make_hookset() -> HookSet:
    return HookSet()


class TestAttachLabels:
    def test_returns_same_hookset(self):
        hs = _make_hookset()
        returned = attach_labels(hs, {"k": "v"})
        assert returned is hs

    def test_before_hook_registered(self):
        hs = _make_hookset()
        attach_labels(hs, {"env": "test"})
        assert len(hs.before_attempt) == 1

    def test_after_hook_registered(self):
        hs = _make_hookset()
        attach_labels(hs, {"env": "test"})
        assert len(hs.after_attempt) == 1

    def test_before_hook_stamps_ctx(self):
        hs = _make_hookset()
        attach_labels(hs, {"region": "eu-west"})
        ctx = MagicMock()
        ctx.metadata = {}
        hs.fire_before_attempt(ctx)
        assert ctx.metadata["labels"]["region"] == "eu-west"

    def test_after_hook_stamps_record(self):
        hs = _make_hookset()
        attach_labels(hs, {"tier": "premium"})
        ctx = MagicMock()
        ctx.metadata = {}
        record = MagicMock()
        record.metadata = {}
        hs.fire_after_attempt(ctx, record)
        assert record.metadata["labels"]["tier"] == "premium"

    def test_multiple_calls_accumulate_hooks(self):
        hs = _make_hookset()
        attach_labels(hs, {"a": 1})
        attach_labels(hs, {"b": 2})
        assert len(hs.before_attempt) == 2
        assert len(hs.after_attempt) == 2

    def test_empty_labels_dict_is_valid(self):
        hs = _make_hookset()
        attach_labels(hs, {})
        ctx = MagicMock()
        ctx.metadata = {}
        hs.fire_before_attempt(ctx)  # should not raise
        assert ctx.metadata.get("labels") == {}
