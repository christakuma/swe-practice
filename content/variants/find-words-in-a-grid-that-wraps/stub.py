"""Your solution goes here."""

from __future__ import annotations


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    """Return the words from `words` that appear in `board`, which wraps.

    Args:
        board: a grid of single-character strings whose opposite edges are
            joined. May be empty.
        words: the words to look for. May be empty or hold duplicates.

    Returns:
        Each present word once, sorted ascending. A path may step up, down,
        left or right, wrapping at the edges, and may not reuse a cell.
    """
    raise NotImplementedError
