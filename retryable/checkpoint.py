"""Checkpoint support: persist and restore retry state across process boundaries."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CheckpointData:
    """Serialisable snapshot of in-progress retry state."""

    key: str
    attempts: int
    last_exception_type: Optional[str]
    last_exception_message: Optional[str]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointData":
        return cls(**data)


class RetryCheckpoint:
    """Store and retrieve CheckpointData using a simple JSON file backend."""

    def __init__(self, store_path: str | Path) -> None:
        self._path = Path(store_path)
        self._path.mkdir(parents=True, exist_ok=True)

    def _file(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_")
        return self._path / f"{safe}.json"

    def save(self, data: CheckpointData) -> None:
        """Persist checkpoint to disk."""
        data.updated_at = time.time()
        self._file(data.key).write_text(json.dumps(data.to_dict(), indent=2))

    def load(self, key: str) -> Optional[CheckpointData]:
        """Return stored checkpoint or *None* if not found."""
        f = self._file(key)
        if not f.exists():
            return None
        return CheckpointData.from_dict(json.loads(f.read_text()))

    def clear(self, key: str) -> None:
        """Remove a checkpoint once the operation has succeeded."""
        f = self._file(key)
        if f.exists():
            f.unlink()

    def exists(self, key: str) -> bool:
        return self._file(key).exists()
