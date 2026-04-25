"""Jitter strategies for adding randomness to retry delays."""

import random
from typing import Callable

JitterStrategy = Callable[[float], float]


def none() -> JitterStrategy:
    """No jitter — returns the delay unchanged."""
    def strategy(delay: float) -> float:
        return delay
    strategy.__name__ = "none"
    return strategy


def full() -> JitterStrategy:
    """Full jitter — returns a random value in [0, delay].

    Recommended for high-concurrency scenarios to spread retries.
    See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    def strategy(delay: float) -> float:
        return random.uniform(0.0, delay)
    strategy.__name__ = "full"
    return strategy


def equal() -> JitterStrategy:
    """Equal jitter — returns delay/2 plus a random value in [0, delay/2].

    Balances between some minimum delay and randomness.
    """
    def strategy(delay: float) -> float:
        half = delay / 2.0
        return half + random.uniform(0.0, half)
    strategy.__name__ = "equal"
    return strategy


def bounded(min_factor: float = 0.5, max_factor: float = 1.5) -> JitterStrategy:
    """Bounded jitter — multiplies delay by a random factor in [min_factor, max_factor].

    Args:
        min_factor: Lower bound multiplier (default 0.5).
        max_factor: Upper bound multiplier (default 1.5).

    Raises:
        ValueError: If min_factor < 0 or min_factor > max_factor.
    """
    if min_factor < 0:
        raise ValueError("min_factor must be non-negative")
    if min_factor > max_factor:
        raise ValueError("min_factor must be <= max_factor")

    def strategy(delay: float) -> float:
        return delay * random.uniform(min_factor, max_factor)
    strategy.__name__ = "bounded"
    return strategy
