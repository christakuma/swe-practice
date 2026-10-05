"""Your solution goes here.

The tests import `Trie` from this module.
"""

from __future__ import annotations


class Trie:
    """A prefix tree over strings."""

    def __init__(self) -> None:
        """Create an empty trie."""
        raise NotImplementedError

    def insert(self, word: str) -> None:
        """Add `word`. Inserting the same word twice changes nothing."""
        raise NotImplementedError

    def contains(self, word: str) -> bool:
        """Return whether `word` was inserted, exactly."""
        raise NotImplementedError

    def starts_with(self, prefix: str) -> bool:
        """Return whether any stored word begins with `prefix`."""
        raise NotImplementedError
