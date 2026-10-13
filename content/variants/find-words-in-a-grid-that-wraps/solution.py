"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
VISITED = "\x00"  # a sentinel no real board cell can hold


class _Node:
    """One position in the tree of words. Characters live on the edges."""

    __slots__ = ("children", "word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.word: str | None = None


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    """Return the words from `words` that appear in `board`, which wraps.

    The flat-grid search with one line changed: the neighbour is taken modulo
    the grid's size, and the bounds check that used to follow is gone because
    there is no longer anything out of bounds.

    What makes that one line safe is where the "used" mark lives. It is
    written into the cell, and the wrapped coordinate is what indexes the
    cell, so two routes to the same cell see the same mark. That covers the
    cases that look as if they need thought. On a grid one column wide,
    left and right both land on the cell being left, which is marked. On a
    grid two wide they land on the same neighbour, which is searched twice
    and found twice -- harmless, because a found word is cleared from the
    trie the first time.

    A solution that kept a set of visited coordinates and added the
    *unwrapped* ones would let a path walk round the grid and through its
    own start. That is the bug this version of the problem exists to find.
    """
    if not board or not board[0] or not words:
        return []

    rows, columns = len(board), len(board[0])
    capacity = rows * columns

    root = _Node()
    for word in words:
        if not word or len(word) > capacity:
            continue
        node = root
        for character in word:
            node = node.children.setdefault(character, _Node())
        node.word = word

    found: list[str] = []

    def search(row: int, column: int, node: _Node) -> None:
        letter = board[row][column]
        child = node.children.get(letter)
        if child is None:
            return

        if child.word is not None:
            found.append(child.word)
            child.word = None

        board[row][column] = VISITED
        for row_step, column_step in STEPS:
            search((row + row_step) % rows, (column + column_step) % columns, child)
        board[row][column] = letter

        if not child.children and child.word is None:
            del node.children[letter]

    for row in range(rows):
        for column in range(columns):
            search(row, column, root)

    return sorted(found)
