"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_decodings


def plain(digits: str) -> int:
    """Decodings of a string with no stars, by trying both splits every time."""
    if not digits:
        return 1
    ways = 0
    if digits[0] != "0":
        ways += plain(digits[1:])
        if len(digits) > 1 and int(digits[:2]) <= 26:
            ways += plain(digits[2:])
    return ways


def by_expanding(digits: str) -> int:
    """Replace every star with each digit 1-9 in turn and add up the results."""
    if not digits:
        return 0
    position = digits.find("*")
    if position < 0:
        return plain(digits)
    return sum(
        by_expanding(digits[:position] + str(digit) + digits[position + 1 :])
        for digit in range(1, 10)
    )


def test_a_single_star_is_nine_letters() -> None:
    """Counts nine decodings for one star."""
    assert count_decodings("*") == 9


def test_strings_without_stars_are_unchanged() -> None:
    """Gives the standard answers when there is no star."""
    assert count_decodings("12") == 2
    assert count_decodings("226") == 3
    assert count_decodings("06") == 0
    assert count_decodings("10") == 1
    assert count_decodings("27") == 1


def test_the_empty_string_has_no_decodings() -> None:
    """Returns 0 for the empty string."""
    assert count_decodings("") == 0


def test_a_digit_followed_by_a_star() -> None:
    """Counts the pairs a star can complete after a 1, a 2 and anything else."""
    assert count_decodings("1*") == 18
    assert count_decodings("2*") == 15
    assert count_decodings("3*") == 9
    assert count_decodings("0*") == 0


def test_a_star_followed_by_a_digit() -> None:
    """Counts the pairs a star can begin before a small digit and a large one."""
    assert count_decodings("*1") == 11
    assert count_decodings("*6") == 11
    assert count_decodings("*7") == 10
    assert count_decodings("*9") == 10


def test_a_star_before_a_zero_must_be_one_or_two() -> None:
    """Counts only 10 and 20 when a star is followed by a zero."""
    assert count_decodings("*0") == 2
    assert count_decodings("*0*") == 18


def test_two_stars_are_not_eighty_one_plus_twenty_six() -> None:
    """Counts fifteen two-digit letters for two stars, not eighteen or twenty-six.

    A star is never zero, so 10 and 20 are not among them, and 27, 28 and 29
    are not letters.
    """
    assert count_decodings("**") == 96
    assert count_decodings("***") == 999


def test_agrees_with_expanding_every_star() -> None:
    """Matches a count over every expansion, for every short string.

    Every string of up to four characters over 0, 1, 2, 6, 7, 9 and the star.
    """
    for size in range(1, 5):
        for characters in product("012679*", repeat=size):
            digits = "".join(characters)
            assert count_decodings(digits) == by_expanding(digits), digits


def test_returns_an_exact_integer_for_a_long_string() -> None:
    """Returns an exact count for ten thousand stars, without recursing.

    The count satisfies ways(n) = 9 * ways(n-1) + 15 * ways(n-2), which is
    checked here over the last few terms.
    """
    counts = [count_decodings("*" * size) for size in (9_998, 9_999, 10_000)]

    assert all(isinstance(count, int) for count in counts)
    assert counts[2] == 9 * counts[1] + 15 * counts[0]
    assert counts[2] > 10**9000


def test_a_long_string_with_one_dead_end() -> None:
    """Returns 0 when a single undecodable pair sits inside a long string."""
    assert count_decodings("*" * 500 + "30" + "*" * 500) == 0
