"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class _Node:
    """One position in the tree of paths. Characters live on the edges."""

    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.is_word = False


class WordStore:
    """A word store whose search forgives exactly one wrong character.

    The wildcard search with the wildcard moved: instead of the pattern saying
    where any character will do, the walk carries one difference it may spend
    anywhere. Until it is spent every child is followed -- the matching one
    for free, each of the others by spending it. After that only the matching
    child is, so the walk is a single path again.

    "Exactly one" is the last line of `matches`: reaching a stored word with
    the difference unspent is the word itself, and that does not count.
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

    def search(self, word: str) -> bool:
        """Return whether a stored word differs from `word` in one position."""

        def matches(node: _Node, index: int, spent: bool) -> bool:
            if index == len(word):
                return spent and node.is_word
            if spent:
                child = node.children.get(word[index])
                return child is not None and matches(child, index + 1, True)
            return any(
                matches(child, index + 1, character != word[index])
                for character, child in node.children.items()
            )

        return matches(self._root, 0, False)
