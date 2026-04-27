"""Fallback strategies executed when all retry attempts are exhausted."""

from __future__ import annotations

from typing import Any, Callable, Optional


class Fallback:
    """Wraps a fallback callable or static value used after retry exhaustion."""

    def __init__(
        self,
        value: Any = None,
        *,
        handler: Optional[Callable[..., Any]] = None,
    ) -> None:
        if value is not None and handler is not None:
            raise ValueError("Specify either 'value' or 'handler', not both.")
        self._value = value
        self._handler = handler

    def __call__(self, exc: BaseException, *args: Any, **kwargs: Any) -> Any:
        """Invoke the fallback, forwarding original call args when a handler is set."""
        if self._handler is not None:
            return self._handler(exc, *args, **kwargs)
        return self._value

    @property
    def has_handler(self) -> bool:
        return self._handler is not None

    def __repr__(self) -> str:  # pragma: no cover
        if self._handler is not None:
            return f"Fallback(handler={self._handler!r})"
        return f"Fallback(value={self._value!r})"


def static(value: Any) -> Fallback:
    """Return a Fallback that always yields *value*."""
    return Fallback(value=value)


def from_handler(fn: Callable[..., Any]) -> Fallback:
    """Return a Fallback that delegates to *fn(exc, *args, **kwargs)*."""
    if not callable(fn):
        raise TypeError(f"handler must be callable, got {type(fn).__name__!r}")
    return Fallback(handler=fn)
