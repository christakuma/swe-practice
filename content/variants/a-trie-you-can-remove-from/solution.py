"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class _Node:
    """One character's position, and how many stored words run through it."""

    __slots__ = ("children", "ends", "passing")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.passing = 0
        self.ends = False


class Trie:
    """A prefix tree over strings that supports removal.

    Each node counts the stored words whose path includes it. That count is
    what makes removal honest: a prefix exists while some word still passes
    through its node, and a node nothing passes through is deleted, so the
    structure never grows from words that are no longer in it.
    """

    def __init__(self) -> None:
        self._root = _Node()

    def _find(self, text: str) -> _Node | None:
        node = self._root
        for character in text:
            following = node.children.get(character)
            if following is None:
                return None
            node = following
        return node

    def insert(self, word: str) -> None:
        if self.contains(word):
            return
        node = self._root
        node.passing += 1
        for character in word:
            node = node.children.setdefault(character, _Node())
            node.passing += 1
        node.ends = True

    def contains(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.ends

    def starts_with(self, prefix: str) -> bool:
        node = self._find(prefix)
        return node is not None and node.passing > 0

    def remove(self, word: str) -> bool:
        if not self.contains(word):
            return False
        node = self._root
        node.passing -= 1
        for character in word:
            child = node.children[character]
            child.passing -= 1
            if child.passing == 0:
                del node.children[character]
                return True
            node = child
        node.ends = False
        return True
