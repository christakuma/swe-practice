"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import is_one_edit_away


def distance(source: str, target: str) -> int:
    """The full edit distance, by the standard table."""
    row = list(range(len(target) + 1))
    for i, a in enumerate(source, start=1):
        previous, row = row, [i] + [0] * len(target)
        for j, b in enumerate(target, start=1):
            row[j] = min(previous[j] + 1, row[j - 1] + 1, previous[j - 1] + (a != b))
    return row[-1]


def test_accepts_a_deletion_and_an_insertion() -> None:
    """Accepts strings that differ by one missing character, either way round."""
    assert is_one_edit_away("pale", "ple") is True
    assert is_one_edit_away("ple", "pale") is True


def test_accepts_a_replacement() -> None:
    """Accepts strings that differ in one position."""
    assert is_one_edit_away("pale", "bale") is True


def test_rejects_two_edits() -> None:
    """Rejects strings that need two edits."""
    assert is_one_edit_away("pale", "bake") is False
    assert is_one_edit_away("abc", "a") is False
    assert is_one_edit_away("ab", "ba") is False


def test_accepts_equal_strings() -> None:
    """Accepts equal strings, which need no edit."""
    assert is_one_edit_away("same", "same") is True
    assert is_one_edit_away("", "") is True


def test_handles_an_edit_at_either_end() -> None:
    """Accepts an insertion at the very start or the very end."""
    assert is_one_edit_away("bc", "abc") is True
    assert is_one_edit_away("ab", "abc") is True
    assert is_one_edit_away("", "x") is True


def test_agrees_with_the_edit_distance() -> None:
    """Matches "distance at most 1" for every pair of short strings."""
    words = [
        "".join(letters) for size in range(6) for letters in product("ab", repeat=size)
    ]
    for source in words:
        for target in words:
            expected = distance(source, target) <= 1
            assert is_one_edit_away(source, target) is expected, (source, target)


def test_compares_a_million_characters() -> None:
    """Compares two strings of a million characters within the time limit."""
    half = "ab" * 250_000
    source = half + "x" + half

    assert is_one_edit_away(source, half + "y" + half) is True
    assert is_one_edit_away(source, half + half) is True
    assert is_one_edit_away(source, half + "y" + half[:-1] + "z") is False
