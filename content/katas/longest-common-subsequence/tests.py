"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from functools import cache
from itertools import product

from solution import lcs_length


def reference(first: str, second: str) -> int:
    """Top-down memoised recursion -- an independent oracle.

    It keeps a full memo keyed on index pairs, so it shares nothing with the
    rolled-up single-row version, and in particular nothing with the saved
    diagonal.
    """

    @cache
    def best(i: int, j: int) -> int:
        if i == 0 or j == 0:
            return 0
        if first[i - 1] == second[j - 1]:
            return 1 + best(i - 1, j - 1)
        return max(best(i - 1, j), best(i, j - 1))

    return best(len(first), len(second))


def test_handles_the_worked_example() -> None:
    """Returns the length of a non-contiguous common subsequence."""
    assert lcs_length("abcde", "ace") == 3


def test_handles_identical_strings() -> None:
    """Returns the full length when the strings are equal."""
    assert lcs_length("abc", "abc") == 3
    assert lcs_length("a", "a") == 1


def test_handles_no_common_characters() -> None:
    """Returns 0 when nothing is shared."""
    assert lcs_length("abc", "def") == 0


def test_handles_empty_strings() -> None:
    """Returns 0 when either string is empty."""
    assert lcs_length("", "abc") == 0
    assert lcs_length("abc", "") == 0
    assert lcs_length("", "") == 0


def test_is_not_a_substring_search() -> None:
    """Allows the common characters to be non-adjacent.

    The longest common *substring* of these is 1; the longest common
    subsequence is 3. A recurrence that resets to zero on a mismatch -- which
    is the substring recurrence -- reports 1.
    """
    assert lcs_length("abcde", "ace") == 3
    assert lcs_length("axbycz", "abc") == 3


def test_is_symmetric() -> None:
    """Gives the same answer with the arguments swapped.

    "Common" is symmetric, so the answer cannot depend on argument order. This
    catches a solution that swaps the strings to keep the shorter one in the
    row and then indexes them inconsistently.
    """
    pairs = (("abcde", "ace"), ("abc", "abcdef"), ("aab", "aba"), ("", "x"))
    for first, second in pairs:
        assert lcs_length(first, second) == lcs_length(second, first), (first, second)


def test_handles_repeated_characters() -> None:
    """Counts repeated characters as separate matches when both strings have them."""
    assert lcs_length("aaa", "aa") == 2
    assert lcs_length("aaa", "aaa") == 3
    assert lcs_length("abab", "baba") == 3


def test_respects_order() -> None:
    """Requires the common characters to appear in the same order.

    Both strings hold a, b and c, but reversed -- so no subsequence of length
    more than one is common. A solution counting shared characters reports 3.
    """
    assert lcs_length("abc", "cba") == 1


def test_is_case_sensitive() -> None:
    """Treats upper and lower case as different characters."""
    assert lcs_length("ABC", "abc") == 0
    assert lcs_length("aBc", "abc") == 2


def test_handles_a_subsequence_at_the_ends() -> None:
    """Finds matches at the very start and the very end."""
    assert lcs_length("axxxxb", "ab") == 2
    assert lcs_length("ab", "axxxxb") == 2


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(lcs_length("a", "a")) is int


def test_agrees_with_a_memoised_recursion_on_every_short_pair() -> None:
    """Matches the oracle for every pair of strings up to length five over a, b, c.

    About a hundred and fifty thousand pairs. The diagonal dependency is the
    thing that breaks when the table is collapsed to one row, and it goes wrong
    only when a match follows a mismatch in a particular pattern.
    """
    strings = [
        "".join(characters)
        for length in range(6)
        for characters in product("abc", repeat=length)
    ]
    for first in strings:
        for second in strings:
            assert lcs_length(first, second) == reference(first, second), (
                first,
                second,
            )


def test_handles_long_strings() -> None:
    """Handles two strings of a thousand characters within the time limit.

    A million table cells. The answer is known by construction: the second
    string is every other character of the first, so it is entirely a
    subsequence of it.
    """
    first = "".join("abcd"[value % 4] for value in range(1_000))
    second = first[::2]

    assert lcs_length(first, second) == len(second)


def test_handles_two_long_unrelated_strings() -> None:
    """Handles long strings with nothing in common."""
    first = "a" * 800
    second = "b" * 800

    assert lcs_length(first, second) == 0
