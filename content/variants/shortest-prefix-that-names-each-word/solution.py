"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def shortest_unique_prefixes(words: list[str]) -> list[str]:
    """Return, for each word, the shortest prefix no other word starts with.

    A prefix of length `p` is shared with some other word exactly when the
    word has `p` or more leading characters in common with it. So the answer
    for a word is one more than the *most* it shares with any other word --
    and the word that shares the most is always a neighbour in sorted order,
    because sorting puts words with a common prefix in one unbroken block.

    That turns "compare with every other word" into "compare with two".

    Positions are sorted and not the words themselves, so each answer can be
    written back to where its word was. `shared[k]` is the number of leading
    characters the `k`th and `k + 1`th words in sorted order have in common.

    Slicing does the awkward cases without being asked. If the word is a
    prefix of its neighbour, or equal to it, the shared stretch is the whole
    word, `need` is one past its end, and `word[:need]` is the word.
    """
    order = sorted(range(len(words)), key=words.__getitem__)
    shared = [_common(words[left], words[right]) for left, right in pairwise(order)]

    prefixes = [""] * len(words)
    for rank, position in enumerate(order):
        before = shared[rank - 1] if rank > 0 else 0
        after = shared[rank] if rank < len(shared) else 0
        need = max(before, after) + 1
        prefixes[position] = words[position][:need]
    return prefixes


def _common(first: str, second: str) -> int:
    """How many leading characters two words share."""
    length = 0
    for a, b in zip(first, second, strict=False):
        if a != b:
            break
        length += 1
    return length
