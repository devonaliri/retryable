"""Labelling support for retry calls — attach arbitrary key/value metadata
to a retry context so downstream hooks, metrics, and exporters can filter
or group results by label.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, Optional


class LabelSet:
    """An immutable-ish mapping of string labels attached to a retry call."""

    def __init__(self, labels: Optional[Dict[str, Any]] = None) -> None:
        self._labels: Dict[str, Any] = dict(labels) if labels else {}

    # ------------------------------------------------------------------
    # Read interface
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if absent."""
        return self._labels.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._labels[key]

    def __contains__(self, key: object) -> bool:
        return key in self._labels

    def __iter__(self) -> Iterator[str]:
        return iter(self._labels)

    def __len__(self) -> int:
        return len(self._labels)

    def as_dict(self) -> Dict[str, Any]:
        """Return a shallow copy of the underlying label mapping."""
        return dict(self._labels)

    # ------------------------------------------------------------------
    # Mutation helpers (returns a *new* LabelSet)
    # ------------------------------------------------------------------

    def merge(self, extra: Dict[str, Any]) -> "LabelSet":
        """Return a new LabelSet with *extra* merged on top."""
        merged = {**self._labels, **extra}
        return LabelSet(merged)

    def __repr__(self) -> str:  # pragma: no cover
        return f"LabelSet({self._labels!r})"


def make_label_hookset(labels: Dict[str, Any]):
    """Return a (before_hook, after_hook) pair that stamps *labels* onto
    every attempt's metadata so other hooks can read them."""
    label_set = LabelSet(labels)

    def before(ctx, **_kwargs) -> None:  # type: ignore[override]
        ctx.metadata.setdefault("labels", {})
        ctx.metadata["labels"].update(label_set.as_dict())

    def after(ctx, record, **_kwargs) -> None:  # type: ignore[override]
        record.metadata.setdefault("labels", {})
        record.metadata["labels"].update(label_set.as_dict())

    return before, after
