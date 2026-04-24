"""Tests for retryable.predicates."""

import pytest

from retryable.predicates import (
    combine,
    exclude_exceptions,
    on_all_exceptions,
    on_exception,
)


class TestOnException:
    def test_matches_single_type(self):
        pred = on_exception(ValueError)
        assert pred(ValueError("bad")) is True

    def test_does_not_match_other_type(self):
        pred = on_exception(ValueError)
        assert pred(RuntimeError("oops")) is False

    def test_matches_any_of_multiple_types(self):
        pred = on_exception(ValueError, TypeError)
        assert pred(ValueError("v")) is True
        assert pred(TypeError("t")) is True

    def test_does_not_match_unlisted_type(self):
        pred = on_exception(ValueError, TypeError)
        assert pred(KeyError("k")) is False

    def test_matches_subclass(self):
        pred = on_exception(OSError)
        assert pred(FileNotFoundError("missing")) is True

    def test_raises_when_no_types_given(self):
        with pytest.raises(ValueError):
            on_exception()

    def test_predicate_has_descriptive_name(self):
        pred = on_exception(ValueError)
        assert "ValueError" in pred.__name__


class TestOnAllExceptions:
    def test_returns_true_for_any_exception(self):
        assert on_all_exceptions(ValueError("x")) is True
        assert on_all_exceptions(RuntimeError("y")) is True
        assert on_all_exceptions(Exception()) is True


class TestExcludeExceptions:
    def test_returns_false_for_excluded_type(self):
        pred = exclude_exceptions(ValueError)
        assert pred(ValueError("bad")) is False

    def test_returns_true_for_non_excluded_type(self):
        pred = exclude_exceptions(ValueError)
        assert pred(RuntimeError("ok")) is True

    def test_excludes_multiple_types(self):
        pred = exclude_exceptions(ValueError, TypeError)
        assert pred(ValueError("v")) is False
        assert pred(TypeError("t")) is False
        assert pred(KeyError("k")) is True

    def test_raises_when_no_types_given(self):
        with pytest.raises(ValueError):
            exclude_exceptions()

    def test_predicate_has_descriptive_name(self):
        pred = exclude_exceptions(KeyError)
        assert "KeyError" in pred.__name__


class TestCombine:
    def test_all_true_returns_true(self):
        pred = combine(on_all_exceptions, on_exception(ValueError))
        assert pred(ValueError("x")) is True

    def test_one_false_returns_false(self):
        pred = combine(on_all_exceptions, on_exception(ValueError))
        assert pred(RuntimeError("x")) is False

    def test_raises_when_no_predicates_given(self):
        with pytest.raises(ValueError):
            combine()

    def test_single_predicate_passthrough(self):
        pred = combine(on_exception(TypeError))
        assert pred(TypeError()) is True
        assert pred(ValueError()) is False
