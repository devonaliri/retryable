"""Predicates for determining whether an exception should trigger a retry."""

from typing import Callable, Sequence, Type, Union

ExceptionTypes = Union[Type[BaseException], Sequence[Type[BaseException]]]


def on_exception(*exc_types: Type[BaseException]) -> Callable[[BaseException], bool]:
    """Return a predicate that retries on any of the given exception types.

    Args:
        *exc_types: Exception classes that should trigger a retry.

    Returns:
        A callable that returns True if the exception matches any of the given types.

    Example:
        >>> pred = on_exception(ValueError, TypeError)
        >>> pred(ValueError("bad"))
        True
        >>> pred(RuntimeError("oops"))
        False
    """
    if not exc_types:
        raise ValueError("At least one exception type must be provided.")

    def predicate(exc: BaseException) -> bool:
        return isinstance(exc, tuple(exc_types))

    predicate.__name__ = f"on_exception({', '.join(t.__name__ for t in exc_types)})"
    return predicate


def on_all_exceptions(exc: BaseException) -> bool:
    """Predicate that retries on every exception.

    Args:
        exc: The raised exception.

    Returns:
        Always True.
    """
    return True


def exclude_exceptions(*exc_types: Type[BaseException]) -> Callable[[BaseException], bool]:
    """Return a predicate that retries on any exception *except* the given types.

    Args:
        *exc_types: Exception classes that should NOT trigger a retry.

    Returns:
        A callable that returns False if the exception matches any excluded type.
    """
    if not exc_types:
        raise ValueError("At least one exception type must be provided.")

    def predicate(exc: BaseException) -> bool:
        return not isinstance(exc, tuple(exc_types))

    predicate.__name__ = f"exclude_exceptions({', '.join(t.__name__ for t in exc_types)})"
    return predicate


def combine(*predicates: Callable[[BaseException], bool]) -> Callable[[BaseException], bool]:
    """Combine multiple predicates with logical AND — all must return True to retry.

    Args:
        *predicates: Predicate callables to combine.

    Returns:
        A callable that returns True only when every predicate returns True.
    """
    if not predicates:
        raise ValueError("At least one predicate must be provided.")

    def predicate(exc: BaseException) -> bool:
        return all(p(exc) for p in predicates)

    return predicate


def combine_any(*predicates: Callable[[BaseException], bool]) -> Callable[[BaseException], bool]:
    """Combine multiple predicates with logical OR — any one returning True triggers a retry.

    Args:
        *predicates: Predicate callables to combine.

    Returns:
        A callable that returns True when at least one predicate returns True.

    Example:
        >>> pred = combine_any(on_exception(ValueError), on_exception(TypeError))
        >>> pred(ValueError("bad"))
        True
        >>> pred(RuntimeError("oops"))
        False
    """
    if not predicates:
        raise ValueError("At least one predicate must be provided.")

    def predicate(exc: BaseException) -> bool:
        return any(p(exc) for p in predicates)

    return predicate
