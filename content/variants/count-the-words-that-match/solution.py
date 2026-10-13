"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations

_END = ""


class WordStore:
    """A word store that counts matches for a single-character wildcard.

    A trie of nested dicts, with the empty-string key marking the end of a
    word -- a key no single character can collide with. Counting is the
    yes-or-no search with `any` replaced by `sum`: a literal follows one
    child, a wildcard adds up all of them.
    """

    def __init__(self) -> None:
        self._root: dict[str, dict] = {}

    def add(self, word: str) -> None:
        node = self._root
        for character in word:
            node = node.setdefault(character, {})
        node[_END] = {}

    def count(self, pattern: str) -> int:
        def below(node: dict[str, dict], at: int) -> int:
            if at == len(pattern):
                return 1 if _END in node else 0
            character = pattern[at]
            if character != ".":
                child = node.get(character)
                return below(child, at + 1) if child is not None else 0
            return sum(
                below(child, at + 1) for key, child in node.items() if key != _END
            )

        return below(self._root, 0)
