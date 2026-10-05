"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

WILDCARD = "."


class _Node:
    """One position in the tree of paths. Characters live on the edges."""

    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.is_word = False


class WordStore:
    """A word store supporting single-character wildcard search.

    A trie, with the search turned into a depth-first search over it. That is
    the whole idea, and the reason the trie is the right substrate rather than
    a list of words:

    - at a **literal** character there is at most one child to follow, so the
      walk is a single path and the pattern's literals prune everything else;
    - at a **wildcard** there are as many branches as the node has children,
      and any one of them matching is enough.

    So a pattern with no wildcards costs O(len(pattern)) -- unchanged from an
    ordinary trie lookup -- and only the wildcards cost branching. A list of
    words would pay O(total characters) for every search regardless, which is
    the whole reason this is not just `any(fnmatch(...))`.

    `len(pattern) == len(word)` is enforced structurally rather than checked:
    every step consumes exactly one pattern character and descends exactly one
    level, so success requires the pattern to run out at a node that is a
    stored word. A `.` matching zero or several characters would need a
    different recursion entirely.

    **No backtracking marks are needed**, which is worth contrasting with
    `find-a-word-in-a-grid`. There the search could revisit a cell, so a mark
    had to be set and unset. Here each step consumes a pattern character and
    moves strictly downward, so the recursion cannot return to a node it is
    already inside -- the state that would need undoing does not exist. The
    difference is that the grid is a graph with cycles and a trie is a tree.
    """

    def __init__(self) -> None:
        """Create an empty store."""
        self._root = _Node()

    def add(self, word: str) -> None:
        """Store `word`. Adding the same word twice changes nothing."""
        node = self._root
        for character in word:
            node = node.children.setdefault(character, _Node())
        node.is_word = True

    def search(self, pattern: str) -> bool:
        """Return whether any stored word matches `pattern`."""

        def matches(node: _Node, index: int) -> bool:
            if index == len(pattern):
                return node.is_word
            character = pattern[index]
            if character == WILDCARD:
                return any(
                    matches(child, index + 1) for child in node.children.values()
                )
            child = node.children.get(character)
            return child is not None and matches(child, index + 1)

        return matches(self._root, 0)
