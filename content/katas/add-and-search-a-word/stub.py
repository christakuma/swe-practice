"""Your solution goes here.

The tests import `WordStore` from this module.
"""

from __future__ import annotations


class WordStore:
    """A word store supporting single-character wildcard search."""

    def __init__(self) -> None:
        """Create an empty store."""
        raise NotImplementedError

    def add(self, word: str) -> None:
        """Store `word`. Adding the same word twice changes nothing.

        Args:
            word: the word to store. May be empty.
        """
        raise NotImplementedError

    def search(self, pattern: str) -> bool:
        """Return whether any stored word matches `pattern`.

        A `.` in `pattern` matches exactly one character of any kind, so the
        pattern and the word must be the same length.

        Args:
            pattern: the word to look for, with `.` for any one character.

        Returns:
            True if some stored word matches `pattern`, False otherwise.
        """
        raise NotImplementedError
