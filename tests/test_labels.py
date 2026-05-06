"""Tests for retryable.labels — LabelSet and make_label_hookset."""
from __future__ import annotations

import pytest

from retryable.labels import LabelSet, make_label_hookset


# ---------------------------------------------------------------------------
# LabelSet
# ---------------------------------------------------------------------------

class TestLabelSetBasics:
    def test_empty_by_default(self):
        ls = LabelSet()
        assert len(ls) == 0
        assert ls.as_dict() == {}

    def test_stores_labels(self):
        ls = LabelSet({"env": "prod", "version": 2})
        assert ls["env"] == "prod"
        assert ls.get("version") == 2

    def test_get_missing_returns_default(self):
        ls = LabelSet({"a": 1})
        assert ls.get("missing") is None
        assert ls.get("missing", 42) == 42

    def test_contains(self):
        ls = LabelSet({"x": True})
        assert "x" in ls
        assert "y" not in ls

    def test_iter(self):
        ls = LabelSet({"a": 1, "b": 2})
        assert set(ls) == {"a", "b"}

    def test_as_dict_is_copy(self):
        original = {"k": "v"}
        ls = LabelSet(original)
        d = ls.as_dict()
        d["k"] = "mutated"
        assert ls["k"] == "v"  # original unchanged

    def test_merge_returns_new_labelset(self):
        ls = LabelSet({"a": 1})
        merged = ls.merge({"b": 2})
        assert merged["a"] == 1
        assert merged["b"] == 2
        assert "b" not in ls  # original unchanged

    def test_merge_overwrites_existing_key(self):
        ls = LabelSet({"a": 1})
        merged = ls.merge({"a": 99})
        assert merged["a"] == 99
        assert ls["a"] == 1

    def test_getitem_raises_for_missing_key(self):
        ls = LabelSet()
        with pytest.raises(KeyError):
            _ = ls["nope"]


# ---------------------------------------------------------------------------
# make_label_hookset
# ---------------------------------------------------------------------------

class _FakeRecord:
    def __init__(self):
        self.metadata: dict = {}


class _FakeCtx:
    def __init__(self):
        self.metadata: dict = {}


class TestMakeLabelHookset:
    def test_before_stamps_ctx_metadata(self):
        before, _ = make_label_hookset({"service": "auth"})
        ctx = _FakeCtx()
        before(ctx)
        assert ctx.metadata["labels"]["service"] == "auth"

    def test_after_stamps_record_metadata(self):
        _, after = make_label_hookset({"env": "staging"})
        ctx = _FakeCtx()
        record = _FakeRecord()
        after(ctx, record)
        assert record.metadata["labels"]["env"] == "staging"

    def test_multiple_labels_all_present(self):
        before, after = make_label_hookset({"a": 1, "b": 2})
        ctx = _FakeCtx()
        record = _FakeRecord()
        before(ctx)
        after(ctx, record)
        assert ctx.metadata["labels"] == {"a": 1, "b": 2}
        assert record.metadata["labels"] == {"a": 1, "b": 2}

    def test_before_merges_with_existing_metadata(self):
        before, _ = make_label_hookset({"new": "val"})
        ctx = _FakeCtx()
        ctx.metadata["labels"] = {"existing": "yes"}
        before(ctx)
        assert ctx.metadata["labels"]["existing"] == "yes"
        assert ctx.metadata["labels"]["new"] == "val"
