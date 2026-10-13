"""Your solution goes here. The tests import from this module."""

from __future__ import annotations


class Trie:
    """A prefix tree over strings that supports removal."""

    def __init__(self) -> None:
        """Create an empty trie."""
        raise NotImplementedError

    def insert(self, word: str) -> None:
        """Add `word`. Inserting the same word twice changes nothing."""
        raise NotImplementedError

    def contains(self, word: str) -> bool:
        """Return whether `word` is stored, exactly."""
        raise NotImplementedError

    def starts_with(self, prefix: str) -> bool:
        """Return whether any stored word begins with `prefix`."""
        raise NotImplementedError

    def remove(self, word: str) -> bool:
        """Remove `word`. Return whether it was stored."""
        raise NotImplementedError
