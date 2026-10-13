"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_common_substring


def by_every_substring(first: str, second: str) -> int:
    pieces = {
        first[start:end]
        for start in range(len(first))
        for end in range(start + 1, len(first) + 1)
    }
    return max((len(piece) for piece in pieces if piece in second), default=0)


def test_requires_the_characters_to_be_adjacent() -> None:
    """Returns 1 where the longest common subsequence would be 3."""
    assert longest_common_substring("abcde", "ace") == 1


def test_finds_a_run_in_the_middle() -> None:
    """Finds a common run surrounded by different characters."""
    assert longest_common_substring("xabcdy", "zabcdw") == 4


def test_finds_overlapping_candidates() -> None:
    """Returns the longest run when several overlap."""
    assert longest_common_substring("abab", "baba") == 3


def test_returns_zero_when_nothing_is_shared() -> None:
    """Returns 0 for strings with no character in common, or an empty one."""
    assert longest_common_substring("abc", "def") == 0
    assert longest_common_substring("", "abc") == 0
    assert longest_common_substring("", "") == 0


def test_handles_equal_and_nested_strings() -> None:
    """Returns the full length when one string contains the other."""
    assert longest_common_substring("same", "same") == 4
    assert longest_common_substring("needle", "a needle here") == 6


def test_is_case_sensitive_and_symmetric() -> None:
    """Treats case as significant and gives the same answer either way round."""
    assert longest_common_substring("ABc", "abc") == 1
    assert longest_common_substring("zabcdw", "xabcdy") == 4


def test_agrees_with_listing_every_substring() -> None:
    """Matches a list-every-substring search for every pair of short strings."""
    words = [
        "".join(letters) for size in range(6) for letters in product("ab", repeat=size)
    ]
    for first in words:
        for second in words:
            expected = by_every_substring(first, second)
            assert longest_common_substring(first, second) == expected, (first, second)


def test_handles_two_long_strings() -> None:
    """Handles two strings of a thousand characters within the time limit."""
    first = "ab" * 500
    second = "ba" * 400 + "x" + "ab" * 99

    assert longest_common_substring(first, second) == 800
    assert longest_common_substring("a" * 1000, "b" * 1000) == 0
