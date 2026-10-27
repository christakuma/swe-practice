"""Your solution goes here. The tests import from this module."""

from __future__ import annotations


class WordStore:
    """A word store that counts matches for a single-character wildcard."""

    def __init__(self) -> None:
        """Create an empty store."""
        raise NotImplementedError

    def add(self, word: str) -> None:
        """Store `word`. Adding the same word twice changes nothing.

        Args:
            word: the word to store. May be empty.
        """
        raise NotImplementedError

    def count(self, pattern: str) -> int:
        """Return how many stored words match `pattern`.

        A `.` in `pattern` matches exactly one character of any kind, so the
        pattern and a matching word are the same length.

        Args:
            pattern: the word to look for, with `.` for any one character.

        Returns:
            The number of distinct stored words that match `pattern`.
        """
        raise NotImplementedError
