"""Reference solution. CI asserts this passes every test in `tests.py`."""


def group_shifted(words: list[str]) -> list[list[str]]:
    """Group words that are shifts of one another.

    A shift moves every letter by the same amount, so it leaves each letter's
    distance from the first letter unchanged. That tuple of distances is the
    key. The `% 26` is not optional: "az" has a gap of 25 and "ba" a gap of
    -1, and they are the same word shifted by one.

    A dict keeps insertion order, which is the order the groups are wanted in.
    """
    groups: dict[tuple[int, ...], list[str]] = {}
    for word in words:
        key = tuple((ord(letter) - ord(word[0])) % 26 for letter in word)
        groups.setdefault(key, []).append(word)
    return list(groups.values())
