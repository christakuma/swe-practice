"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class _Node:
    """One position in the tree of paths.

    `children` maps a character to the node reached by consuming it, so the
    characters live on the **edges** rather than in the nodes -- a node is a
    prefix, identified by the path taken to reach it.

    `is_word` is what separates a stored word from a prefix of one. Without it
    the structure can only answer "does any word start here?", which is why
    `contains` and `starts_with` would collapse into the same function.

    `slots` because a trie over real data allocates one of these per character
    inserted, and the dict a normal instance carries would dominate the memory.
    """

    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.is_word = False


class Trie:
    """A prefix tree over strings.

    Every operation walks one node per character, so each is O(len(word)) and
    -- the property worth the whole structure -- **independent of how many
    words are stored**.

    A `set` of strings beats this for `contains`: O(1) and three characters of
    code. It cannot answer `starts_with` at all without scanning every stored
    word, which is O(total characters). The trie's value is entirely in the
    prefix query, and reaching for one when you only need exact membership is a
    mistake in the other direction.

    `children` is a dict rather than a fixed array of 26 slots because the
    prompt does not constrain the alphabet -- the same judgement as in
    `is-it-an-anagram`. The array is faster and correct only when the alphabet
    is written down.
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

    def _find(self, text: str) -> _Node | None:
        """The node reached by consuming `text`, or None if the path breaks.

        Both queries are this walk; they differ only in what they ask of the
        node at the end. Keeping it in one place is what stops `contains` and
        `starts_with` drifting apart.
        """
        node = self._root
        for character in text:
            child = node.children.get(character)
            if child is None:
                return None
            node = child
        return node

    def contains(self, word: str) -> bool:
        """Return whether `word` was inserted, exactly."""
        node = self._find(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        """Return whether any stored word begins with `prefix`.

        Reaching the node is *almost* sufficient, and the exception is worth
        the extra clause. Any node other than the root exists only because an
        insertion created it, so it necessarily has a word below it or is one
        itself -- no subtree search is ever needed.

        The root is the one node that exists without an insertion. So on an
        empty trie, `starts_with("")` finds the root and would answer True
        about a collection that contains nothing. Since the question is "does
        any *stored word* begin with this", the honest answer is False, and
        `node.is_word or node.children` is what distinguishes "this prefix was
        reached" from "the root happens to exist".
        """
        node = self._find(prefix)
        return node is not None and bool(node.is_word or node.children)
