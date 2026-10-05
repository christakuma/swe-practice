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
        """Store `word`. Adding the same word twice changes nothing."""
        raise NotImplementedError

    def search(self, pattern: str) -> bool:
        """Return whether any stored word matches `pattern`.

        A `.` in `pattern` matches exactly one character of any kind, so the
        pattern and the word must be the same length.
        """
        raise NotImplementedError
