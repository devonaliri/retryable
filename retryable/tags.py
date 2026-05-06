"""Tagging support for retry operations.

Allows arbitrary string tags to be attached to a retry context's metadata,
enabling filtering, grouping, and reporting across retry sessions.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Set


class TagSet:
    """An immutable-ish set of string tags associated with a retry operation."""

    def __init__(self, tags: Iterable[str] = ()) -> None:
        invalid = [t for t in tags if not isinstance(t, str) or not t.strip()]
        if invalid:
            raise ValueError(f"All tags must be non-empty strings; got: {invalid!r}")
        self._tags: Set[str] = {t.strip() for t in tags}

    # ------------------------------------------------------------------
    # Mutation helpers (return new TagSet to keep immutable semantics)
    # ------------------------------------------------------------------

    def add(self, tag: str) -> "TagSet":
        """Return a new TagSet with *tag* included."""
        return TagSet(self._tags | {tag})

    def remove(self, tag: str) -> "TagSet":
        """Return a new TagSet without *tag* (no-op if absent)."""
        return TagSet(self._tags - {tag})

    def merge(self, other: "TagSet") -> "TagSet":
        """Return the union of this TagSet and *other*."""
        return TagSet(self._tags | other._tags)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def has(self, tag: str) -> bool:
        return tag in self._tags

    def __contains__(self, tag: object) -> bool:
        return tag in self._tags

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._tags))

    def __len__(self) -> int:
        return len(self._tags)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TagSet):
            return self._tags == other._tags
        return NotImplemented

    def __repr__(self) -> str:
        return f"TagSet({sorted(self._tags)!r})"

    def as_list(self) -> list:
        return sorted(self._tags)


def attach_tags(hookset, tags: Iterable[str]) -> None:
    """Register before/after hooks that stamp *tags* onto every attempt's metadata.

    The tags are stored under the key ``"tags"`` in ``AttemptRecord.metadata``
    (if the record exposes a ``metadata`` dict) and also on the context under
    ``ctx.metadata["tags"]``.
    """
    tag_set = TagSet(tags)
    tag_list = tag_set.as_list()

    def before(ctx):
        ctx.metadata["tags"] = tag_list

    def after(ctx, record):
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            record.metadata["tags"] = tag_list

    hookset.fire_before_attempt.__func__ if False else None  # noqa: keep import clean
    hookset._before.append(before)
    hookset._after.append(after)
