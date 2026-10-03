"""Reference solution. CI asserts this passes every test in `tests.py`."""


def group_anagrams(words: list[str]) -> list[list[str]]:
    """Group words that are anagrams of one another.

    The whole problem is choosing a key: something equal for two words exactly
    when they are anagrams. Sorted letters is the obvious one and it is enough --
    `"eat"` and `"tea"` both key on `"aet"`.

    Comparing every pair instead is the version to write first and then throw
    away: it is quadratic in the number of words *and* pays the sort cost per
    comparison rather than once per word.

    A plain dict preserves insertion order in Python, so returning
    `list(groups.values())` gives the required ordering for free -- groups ordered
    by where each first appeared, words within a group in input order. That is a
    language guarantee since 3.7, not an implementation detail, and it is worth
    knowing rather than sorting afterwards to be safe.
    """
    groups: dict[str, list[str]] = {}
    for word in words:
        key = "".join(sorted(word))
        groups.setdefault(key, []).append(word)
    return list(groups.values())
