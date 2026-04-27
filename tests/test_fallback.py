"""Tests for retryable.fallback."""

import pytest

from retryable.fallback import Fallback, from_handler, static


_EXC = ValueError("boom")


class TestFallbackInit:
    def test_default_value_is_none(self):
        fb = Fallback()
        assert fb(exc=_EXC) is None

    def test_static_value_returned(self):
        fb = Fallback(value=42)
        assert fb(_EXC) == 42

    def test_handler_called_with_exc_and_args(self):
        received = {}

        def handler(exc, x, y=0):
            received["exc"] = exc
            received["x"] = x
            received["y"] = y
            return "handled"

        fb = Fallback(handler=handler)
        result = fb(_EXC, 10, y=20)
        assert result == "handled"
        assert received["exc"] is _EXC
        assert received["x"] == 10
        assert received["y"] == 20

    def test_both_value_and_handler_raises(self):
        with pytest.raises(ValueError, match="not both"):
            Fallback(value=1, handler=lambda e: e)

    def test_has_handler_false_for_value(self):
        assert Fallback(value="x").has_handler is False

    def test_has_handler_true_for_handler(self):
        assert Fallback(handler=lambda e: None).has_handler is True


class TestStaticHelper:
    def test_returns_fallback_instance(self):
        fb = static("default")
        assert isinstance(fb, Fallback)

    def test_always_returns_same_value(self):
        fb = static(99)
        assert fb(_EXC) == 99
        assert fb(RuntimeError()) == 99

    def test_none_value(self):
        fb = static(None)
        assert fb(_EXC) is None


class TestFromHandlerHelper:
    def test_returns_fallback_instance(self):
        fb = from_handler(lambda e: "ok")
        assert isinstance(fb, Fallback)

    def test_handler_receives_exception(self):
        exc = KeyError("missing")
        fb = from_handler(lambda e: str(e))
        assert "missing" in fb(exc)

    def test_non_callable_raises(self):
        with pytest.raises(TypeError, match="callable"):
            from_handler("not_a_function")  # type: ignore[arg-type]

    def test_handler_with_extra_args(self):
        fb = from_handler(lambda e, a, b: a + b)
        assert fb(_EXC, 3, 4) == 7
