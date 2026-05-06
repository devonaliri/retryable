"""Hedged retry strategy: launch a speculative second attempt after a delay.

A hedge fires a duplicate call after `hedge_delay` seconds if the original
has not yet returned.  The first result to arrive wins; the other is
ignored.  This trades extra resource usage for lower tail latency.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional


class HedgeTimeout(Exception):
    """Raised when all hedged attempts exceed the total deadline."""


class HedgeResult:
    """Holds the outcome of a hedged call."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: Any = None
        self._exc: Optional[BaseException] = None
        self._done = threading.Event()

    def set_value(self, value: Any) -> bool:
        with self._lock:
            if self._done.is_set():
                return False
            self._value = value
            self._done.set()
            return True

    def set_exception(self, exc: BaseException) -> bool:
        with self._lock:
            if self._done.is_set():
                return False
            self._exc = exc
            self._done.set()
            return True

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done.wait(timeout=timeout)

    @property
    def value(self) -> Any:
        if self._exc is not None:
            raise self._exc
        return self._value


def hedged_call(
    fn: Callable[..., Any],
    args: tuple,
    kwargs: dict,
    *,
    hedge_delay: float = 0.1,
    deadline: Optional[float] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    """Call *fn* and, after *hedge_delay* seconds, launch a speculative twin.

    Parameters
    ----------
    fn:           The callable to invoke.
    args/kwargs:  Forwarded to *fn*.
    hedge_delay:  Seconds to wait before firing the speculative attempt.
    deadline:     Absolute monotonic time by which a result must arrive.
    sleep_fn:     Injection point for the sleep implementation.
    """
    if hedge_delay < 0:
        raise ValueError("hedge_delay must be >= 0")

    result = HedgeResult()

    def _run() -> None:
        try:
            value = fn(*args, **kwargs)
            result.set_value(value)
        except Exception as exc:  # noqa: BLE001
            result.set_exception(exc)

    primary = threading.Thread(target=_run, daemon=True)
    primary.start()

    arrived = result.wait(timeout=hedge_delay)
    if not arrived:
        hedge = threading.Thread(target=_run, daemon=True)
        hedge.start()

    remaining: Optional[float] = None
    if deadline is not None:
        remaining = max(0.0, deadline - time.monotonic())

    if not result.wait(timeout=remaining):
        raise HedgeTimeout("Hedged call did not complete within the deadline")

    return result.value
