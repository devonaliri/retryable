"""Backoff strategy functions for retry delays."""
from typing import Callable


def constant(delay: float = 1.0) -> Callable[[int], float]:
    """Return a fixed delay regardless of attempt number."""
    def strategy(attempt: int) -> float:
        return delay
    strategy.__name__ = f"constant(delay={delay})"
    return strategy


def linear(initial: float = 1.0, increment: float = 1.0) -> Callable[[int], float]:
    """Return a delay that grows linearly with each attempt.

    delay = initial + increment * (attempt - 1)
    """
    def strategy(attempt: int) -> float:
        return initial + increment * (attempt - 1)
    strategy.__name__ = f"linear(initial={initial}, increment={increment})"
    return strategy


def exponential(
    base: float = 2.0,
    initial: float = 1.0,
    max_delay: float = 60.0,
) -> Callable[[int], float]:
    """Return a delay that grows exponentially with each attempt.

    delay = min(initial * base ** (attempt - 1), max_delay)
    """
    def strategy(attempt: int) -> float:
        return min(initial * (base ** (attempt - 1)), max_delay)
    strategy.__name__ = f"exponential(base={base}, initial={initial}, max_delay={max_delay})"
    return strategy
