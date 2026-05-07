"""Token bucket rate limiter for retry throttling."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


class BucketDepleted(Exception):
    """Raised when the token bucket has no tokens available."""

    def __init__(self, available: float, requested: float) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Token bucket depleted: requested {requested:.2f}, available {available:.2f}"
        )


@dataclass
class TokenBucket:
    """Token bucket with configurable refill rate and capacity.

    Tokens refill continuously at *rate* tokens per second up to *capacity*.
    Each :meth:`consume` call removes *tokens* from the bucket.
    """

    _rate: float
    _capacity: float
    _clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        if self._rate <= 0:
            raise ValueError("rate must be positive")
        if self._capacity <= 0:
            raise ValueError("capacity must be positive")
        self._tokens = self._capacity
        self._last_refill = self._clock()

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def capacity(self) -> float:
        return self._capacity

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    @property
    def available(self) -> float:
        self._refill()
        return self._tokens

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume *tokens* from the bucket.

        Returns ``True`` on success, ``False`` if insufficient tokens.
        """
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def consume_or_raise(self, tokens: float = 1.0) -> None:
        """Consume *tokens* or raise :exc:`BucketDepleted`."""
        if not self.consume(tokens):
            raise BucketDepleted(available=self._tokens, requested=tokens)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TokenBucket(rate={self._rate}, capacity={self._capacity}, "
            f"available={self._tokens:.2f})"
        )
