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
        """Add `word`. Inserting the same word twice changes nothing.

        Args:
            word: the word to add. May be empty.
        """
        raise NotImplementedError

    def contains(self, word: str) -> bool:
        """Return whether `word` was inserted, exactly.

        Args:
            word: the word to look up.

        Returns:
            True if `word` itself was inserted; a prefix of a stored word is
            not enough.
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
