"""Tests for retryable.tags — TagSet and attach_tags."""
import pytest

from retryable.tags import TagSet, attach_tags


# ---------------------------------------------------------------------------
# TagSet construction
# ---------------------------------------------------------------------------

class TestTagSetInit:
    def test_empty_by_default(self):
        ts = TagSet()
        assert len(ts) == 0

    def test_stores_tags(self):
        ts = TagSet(["critical", "network"])
        assert "critical" in ts
        assert "network" in ts

    def test_strips_whitespace(self):
        ts = TagSet(["  slow  ", "db"])
        assert "slow" in ts
        assert "db" in ts

    def test_deduplicates(self):
        ts = TagSet(["a", "a", "b"])
        assert len(ts) == 2

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            TagSet([""])

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            TagSet(["   "])

    def test_non_string_raises(self):
        with pytest.raises(ValueError):
            TagSet([123])  # type: ignore


# ---------------------------------------------------------------------------
# TagSet mutation (immutable semantics)
# ---------------------------------------------------------------------------

class TestTagSetMutation:
    def test_add_returns_new_set(self):
        ts = TagSet(["a"])
        ts2 = ts.add("b")
        assert "b" in ts2
        assert "b" not in ts  # original unchanged

    def test_remove_returns_new_set(self):
        ts = TagSet(["a", "b"])
        ts2 = ts.remove("a")
        assert "a" not in ts2
        assert "a" in ts

    def test_remove_absent_tag_is_noop(self):
        ts = TagSet(["a"])
        ts2 = ts.remove("z")
        assert ts2 == ts

    def test_merge_combines_tags(self):
        ts1 = TagSet(["a", "b"])
        ts2 = TagSet(["b", "c"])
        merged = ts1.merge(ts2)
        assert set(merged) == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# TagSet query / dunder helpers
# ---------------------------------------------------------------------------

class TestTagSetQuery:
    def test_has(self):
        ts = TagSet(["x"])
        assert ts.has("x") is True
        assert ts.has("y") is False

    def test_iter_sorted(self):
        ts = TagSet(["c", "a", "b"])
        assert list(ts) == ["a", "b", "c"]

    def test_as_list(self):
        ts = TagSet(["z", "m"])
        assert ts.as_list() == ["m", "z"]

    def test_equality(self):
        assert TagSet(["a", "b"]) == TagSet(["b", "a"])

    def test_repr(self):
        ts = TagSet(["beta", "alpha"])
        assert "alpha" in repr(ts)
        assert "beta" in repr(ts)


# ---------------------------------------------------------------------------
# attach_tags integration
# ---------------------------------------------------------------------------

class _FakeRecord:
    def __init__(self):
        self.metadata = {}


class _FakeCtx:
    def __init__(self):
        self.metadata = {}


class _FakeHookSet:
    def __init__(self):
        self._before = []
        self._after = []


class TestAttachTags:
    def test_before_hook_stamps_ctx_metadata(self):
        hs = _FakeHookSet()
        attach_tags(hs, ["db", "slow"])
        ctx = _FakeCtx()
        hs._before[0](ctx)
        assert ctx.metadata["tags"] == ["db", "slow"]

    def test_after_hook_stamps_record_metadata(self):
        hs = _FakeHookSet()
        attach_tags(hs, ["critical"])
        ctx = _FakeCtx()
        record = _FakeRecord()
        hs._after[0](ctx, record)
        assert record.metadata["tags"] == ["critical"]

    def test_hooks_registered_on_hookset(self):
        hs = _FakeHookSet()
        attach_tags(hs, ["x"])
        assert len(hs._before) == 1
        assert len(hs._after) == 1
