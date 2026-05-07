"""Retry signal — allows in-flight cancellation or forced success of a retry loop."""
from __future__ import annotations

from enum import Enum, auto
from threading import Lock
from typing import Optional


class SignalAction(Enum):
    NONE = auto()
    CANCEL = auto()   # abort the retry loop, raise RetryLimitExceeded
    SUCCEED = auto()  # force the loop to return a provided value immediately


class RetrySignal:
    """Thread-safe signal that can interrupt a running retry loop."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._action: SignalAction = SignalAction.NONE
        self._forced_value: object = None

    # ------------------------------------------------------------------
    # Control API
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request that the retry loop abort on its next iteration."""
        with self._lock:
            self._action = SignalAction.CANCEL

    def force_success(self, value: object = None) -> None:
        """Request that the retry loop return *value* on its next iteration."""
        with self._lock:
            self._action = SignalAction.SUCCEED
            self._forced_value = value

    def reset(self) -> None:
        """Clear any pending signal (idempotent)."""
        with self._lock:
            self._action = SignalAction.NONE
            self._forced_value = None

    # ------------------------------------------------------------------
    # Query API (used by the retry loop)
    # ------------------------------------------------------------------

    @property
    def action(self) -> SignalAction:
        with self._lock:
            return self._action

    @property
    def forced_value(self) -> object:
        with self._lock:
            return self._forced_value

    def is_set(self) -> bool:
        return self.action is not SignalAction.NONE

    def __repr__(self) -> str:  # pragma: no cover
        return f"RetrySignal(action={self._action.name})"
