"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
VISITED = "\x00"  # a sentinel no real board cell can hold


class _Node:
    """One position in the tree of words. Characters live on the edges."""

    __slots__ = ("children", "word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        # The whole word ending here, or None. Storing the word rather than a
        # boolean means a hit needs no reconstruction from the path.
        self.word: str | None = None


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    """Return the words from `words` that appear in `board`.

    This is `find-a-word-in-a-grid` and `implement-a-trie` composed, and the
    composition is the point rather than either half.

    Running the single-word search once per word repeats the same grid walk for
    every word sharing a prefix -- and a word list is mostly shared prefixes.
    **Inverting the loops fixes it**: search the grid once, carrying a trie node
    alongside the position, so a step is only worth taking if that character is
    a child of the current node. Shared prefixes become shared work, and the
    word list stops multiplying the cost.

    Two kinds of state move together and only one of them needs undoing:

    - the **cell mark** is set and restored around the recursion, because the
      grid has cycles and a path must not reuse a cell;
    - the **trie descent** needs no undoing at all, because it only ever moves
      downward -- `node.children[letter]` is passed to the callee and the
      caller's own `node` is untouched.

    That asymmetry is the lesson. Whether a DFS needs backtracking marks is a
    property of the *structure*, not the algorithm: a graph with cycles needs
    them, a tree does not, and here one search runs over both at once.

    Three prunings, and they are what make this finish rather than merely
    terminate:

    `node.word = None` after recording a hit stops the same word being found
    again by another path, and makes the result naturally duplicate-free.

    Deleting an exhausted child -- a node with no children and no word left --
    shrinks the trie as the search proceeds, so later cells do not re-explore
    branches that can no longer produce anything. This is what keeps a large
    word list from costing a large amount per starting cell.

    And a word longer than the grid has cells cannot fit, so it is dropped
    before the trie is built rather than explored.
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
            # Only once: clearing the marker keeps the result duplicate-free
            # and stops other paths re-finding it.
            child.word = None

        board[row][column] = VISITED
        for row_step, column_step in STEPS:
            next_row, next_column = row + row_step, column + column_step
            if 0 <= next_row < rows and 0 <= next_column < columns:
                search(next_row, next_column, child)
        board[row][column] = letter

        if not child.children and child.word is None:
            del node.children[letter]  # exhausted branch; never explore it again

    for row in range(rows):
        for column in range(columns):
            search(row, column, root)

    return sorted(found)
