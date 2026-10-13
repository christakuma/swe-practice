"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def is_sorted(words: list[str], alphabet: str) -> bool:
    """Return whether `words` is in order under the given alphabet.

    Each word is translated into the list of its characters' positions in
    the alphabet. Lists compare element by element and treat a proper prefix
    as smaller, which are exactly the two rules of dictionary order, so the
    check is that no neighbouring pair is out of order.
    """
    rank = {character: position for position, character in enumerate(alphabet)}
    keys = [[rank[character] for character in word] for word in words]
    return all(first <= second for first, second in pairwise(keys))
