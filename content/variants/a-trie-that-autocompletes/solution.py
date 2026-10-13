"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class _Node:
    """One position in the tree of paths. Characters live on the edges."""

    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.is_word = False


class Trie:
    """A prefix tree that lists the words beginning with a prefix.

    `complete` is `starts_with` with a second half. The first half walks down
    to the node the prefix leads to. The second lists what is stored at and
    below that node, by a depth-first walk that takes children in sorted
    order and reports a node's own word before descending -- which is
    ascending string order, since a word sorts before every extension of it.

    The walk uses an explicit stack and returns as soon as `limit` words have
    been found, so a short list of suggestions costs a short walk however
    many words lie below the prefix. Children are pushed in reverse so the
    smallest is popped first.
    """

    def __init__(self) -> None:
        """Create an empty trie."""
        self._root = _Node()

    def insert(self, word: str) -> None:
        """Add `word`. Inserting the same word twice changes nothing."""
        node = self._root
        for character in word:
            node = node.children.setdefault(character, _Node())
        node.is_word = True

    def complete(self, prefix: str, limit: int) -> list[str]:
        """Return up to `limit` stored words that begin with `prefix`."""
        node = self._root
        for character in prefix:
            child = node.children.get(character)
            if child is None:
                return []
            node = child

        found: list[str] = []
        stack = [(node, prefix)]
        while stack and len(found) < limit:
            node, word = stack.pop()
            if node.is_word:
                found.append(word)
            for character in sorted(node.children, reverse=True):
                stack.append((node.children[character], word + character))
        return found
