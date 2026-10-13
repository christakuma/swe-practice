"""Reference solution. CI asserts this passes every test in `tests.py`."""


def _pattern(word: str) -> tuple[int, ...]:
    """The word with each letter replaced by the order it first appeared in."""
    first_seen: dict[str, int] = {}
    return tuple(first_seen.setdefault(letter, len(first_seen)) for letter in word)


def group_by_pattern(words: list[str]) -> list[list[str]]:
    """Group words that share a letter pattern.

    The anagram solution with a different key. Grouping is always "compute a
    canonical form, collect by it"; only the canonical form is specific to
    the problem. Here it renames letters by first appearance, so the key
    records where letters repeat and nothing about which letters they are.

    Two words get the same key exactly when a consistent, one-to-one renaming
    connects them: equal keys give the renaming directly, position by
    position, and it is one-to-one because distinct numbers stand for
    distinct letters on both sides.

    A dict preserves insertion order, so the groups come out in the order
    their first words appeared without any further work.
    """
    groups: dict[tuple[int, ...], list[str]] = {}
    for word in words:
        groups.setdefault(_pattern(word), []).append(word)
    return list(groups.values())
