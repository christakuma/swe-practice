"""Your solution goes here.

The tests import `Trie` from this module.
"""

from __future__ import annotations


class Trie:
    """A prefix tree that lists the words beginning with a prefix."""

    def __init__(self) -> None:
        """Create an empty trie."""
        raise NotImplementedError

    def insert(self, word: str) -> None:
        """Add `word`. Inserting the same word twice changes nothing."""
        raise NotImplementedError

    def complete(self, prefix: str, limit: int) -> list[str]:
        """Return up to `limit` stored words that begin with `prefix`.

        The words are in ascending order, and are the first `limit` of all
        the matches in that order. A stored word is a prefix of itself.
        """
        raise NotImplementedError
