"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import Counter


def changes_needed(first: str, second: str) -> int:
    """Return how many replacements make `second` an anagram of `first`.

    Count both strings. Wherever `second` has more of a character than
    `first` wants, the extras must be replaced, and nothing else needs to be.
    Because the lengths are equal, the total surplus equals the total
    shortfall, and each replacement turns one surplus character into one
    missing character -- so the surplus alone is the answer.

    `Counter` subtraction keeps only the positive differences, which is
    exactly "surplus".
    """
    if len(first) != len(second):
        return -1
    surplus = Counter(second) - Counter(first)
    return sum(surplus.values())
