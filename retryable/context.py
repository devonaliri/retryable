"""Retry context tracking for capturing attempt metadata."""

from dataclasses import dataclass, field
from typing import Optional, List, Type
import time


@dataclass
class AttemptRecord:
    """Record of a single attempt."""
    attempt_number: int
    exception: Optional[BaseException] = None
    delay_before: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def succeeded(self) -> bool:
        return self.exception is None


@dataclass
class RetryContext:
    """Tracks state and metadata across retry attempts."""

    max_attempts: int
    exceptions: tuple
    attempts: List[AttemptRecord] = field(default_factory=list)
    _start_time: float = field(default_factory=time.time, init=False)

    def record_attempt(
        self,
        attempt_number: int,
        exception: Optional[BaseException] = None,
        delay_before: float = 0.0,
    ) -> AttemptRecord:
        """Record the result of an attempt."""
        record = AttemptRecord(
            attempt_number=attempt_number,
            exception=exception,
            delay_before=delay_before,
        )
        self.attempts.append(record)
        return record

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def failed_attempts(self) -> List[AttemptRecord]:
        return [a for a in self.attempts if not a.succeeded]

    @property
    def last_exception(self) -> Optional[BaseException]:
        failed = self.failed_attempts
        return failed[-1].exception if failed else None

    @property
    def elapsed(self) -> float:
        """Total elapsed time since context was created."""
        return time.time() - self._start_time

    @property
    def exhausted(self) -> bool:
        """Whether all attempts have been used."""
        return self.total_attempts >= self.max_attempts

    def __repr__(self) -> str:
        return (
            f"RetryContext(attempts={self.total_attempts}/{self.max_attempts}, "
            f"elapsed={self.elapsed:.3f}s)"
        )
