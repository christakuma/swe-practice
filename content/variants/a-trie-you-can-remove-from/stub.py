"""Your solution goes here. The tests import from this module."""

from __future__ import annotations


class Trie:
    """A prefix tree over strings that supports removal."""

    def __init__(self) -> None:
        """Create an empty trie."""
        raise NotImplementedError

    def insert(self, word: str) -> None:
        """Add `word`. Inserting the same word twice changes nothing.

        Args:
            word: the word to add. May be empty.
        """
        raise NotImplementedError

    def contains(self, word: str) -> bool:
        """Return whether `word` is stored, exactly.

        Args:
            word: the word to look up.

        Returns:
            True if `word` itself is stored; a prefix of a stored word is not
            enough.
        """
        raise NotImplementedError

    def starts_with(self, prefix: str) -> bool:
        """Return whether any stored word begins with `prefix`.

        Args:
            prefix: the start to look for. May be empty.

        Returns:
            True if some stored word begins with `prefix`, False otherwise.
        """
        raise NotImplementedError

    def remove(self, word: str) -> bool:
        """Remove `word`. Return whether it was stored.

        Args:
            word: the word to remove.

        Returns:
            True if `word` was stored and has been removed, False if it was not
            stored.
        """
        raise NotImplementedError
