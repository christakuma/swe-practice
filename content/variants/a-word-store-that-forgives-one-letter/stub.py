"""Your solution goes here.

The tests import `WordStore` from this module.
"""

from __future__ import annotations


class WordStore:
    """A word store whose search forgives exactly one wrong character."""

    def __init__(self) -> None:
        """Create an empty store."""
        raise NotImplementedError

    def add(self, word: str) -> None:
        """Store `word`. Adding the same word twice changes nothing.

        Args:
            word: the word to store. May be empty.
        """
        raise NotImplementedError

    def search(self, word: str) -> bool:
        """Return whether a stored word differs from `word` in one position.

        The stored word must be the same length as `word` and differ from it
        in exactly one position -- not zero, and not two.

        Args:
            word: the word to compare against every stored word.

        Returns:
            True if some stored word differs from `word` in exactly one
            position, False otherwise.
        """
        raise NotImplementedError
