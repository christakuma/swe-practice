"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from functools import cache
from itertools import product

from solution import count_decodings


def reference(digits: str) -> int:
    """Top-down memoised recursion over suffixes -- an independent oracle.

    It counts forwards from each position rather than accumulating backwards,
    so it shares no seeds and no rolling variables with the intended solution.
    """
    if not digits:
        return 0

    @cache
    def ways(index: int) -> int:
        if index == len(digits):
            return 1
        total = 0
        if digits[index] != "0":
            total += ways(index + 1)
        if index + 1 < len(digits) and 10 <= int(digits[index : index + 2]) <= 26:
            total += ways(index + 2)
        return total

    return ways(0)


def test_handles_the_worked_examples() -> None:
    """Returns the documented counts."""
    assert count_decodings("12") == 2
    assert count_decodings("226") == 3


def test_rejects_a_leading_zero() -> None:
    """Returns 0 when a pair would need a leading zero.

    "06" is not a valid encoding of F. A solution that accepts any pair below
    27 reports 1.
    """
    assert count_decodings("06") == 0
    assert count_decodings("01") == 0


def test_rejects_a_standalone_zero() -> None:
    """Returns 0 for a zero that nothing can absorb."""
    assert count_decodings("0") == 0
    assert count_decodings("00") == 0
    assert count_decodings("100") == 0


def test_handles_an_empty_string() -> None:
    """Returns 0 for the empty string.

    "One way to decode nothing" is bookkeeping inside the recurrence; the
    problem says the empty string has zero decodings, so a solution returning
    its seed reports 1.
    """
    assert count_decodings("") == 0


def test_absorbs_a_zero_into_the_pair_before_it() -> None:
    """Counts a zero only as the second digit of 10 or 20."""
    assert count_decodings("10") == 1
    assert count_decodings("20") == 1
    assert count_decodings("30") == 0
    assert count_decodings("2101") == 1


def test_handles_a_single_digit() -> None:
    """Counts one way for each non-zero single digit."""
    for digit in "123456789":
        assert count_decodings(digit) == 1, digit
    assert count_decodings("0") == 0


def test_rejects_pairs_above_twenty_six() -> None:
    """Does not combine two digits reading above 26."""
    assert count_decodings("27") == 1
    assert count_decodings("26") == 2
    assert count_decodings("99") == 1


def test_counts_a_run_of_ones_like_fibonacci() -> None:
    """Counts a string of ones as a Fibonacci number.

    Every adjacent pair is 11, which is a valid letter, so each prefix can be
    extended one way or two -- making the counts 1, 2, 3, 5, 8, 13. An exact
    closed form rather than a spot value, so an off-by-one seed is visible.
    """
    expected = [1, 2, 3, 5, 8, 13, 21, 34]
    for length, count in enumerate(expected, start=1):
        assert count_decodings("1" * length) == count, length


def test_counts_a_two_digit_opening_once() -> None:
    """Does not drop the both-digits reading of the first pair.

    Seeding the second history variable at 0 halves the answer for any input
    starting with a valid pair, and still gets single-digit inputs right.
    """
    assert count_decodings("12") == 2
    assert count_decodings("11") == 2
    assert count_decodings("26") == 2


def test_handles_an_undecodable_string_without_an_early_return() -> None:
    """Returns 0 when the string becomes undecodable partway through.

    The zero propagates arithmetically: once a count is 0, every later count is
    a sum of zeros.
    """
    assert count_decodings("1200") == 0
    assert count_decodings("301") == 0
    assert count_decodings("1002") == 0


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(count_decodings("12")) is int


def test_agrees_with_a_memoised_recursion_on_every_short_string() -> None:
    """Matches the oracle for every digit string up to length eight over 0..3.

    And every string up to length six over a wider digit set. Around a hundred
    thousand cases in all. The zero rules and the seeds each fail only on
    particular digit patterns, so enumerating beats choosing.
    """
    for length in range(9):
        for digits in product("0123", repeat=length):
            text = "".join(digits)

            assert count_decodings(text) == reference(text), text

    for length in range(7):
        for digits in product("0126789", repeat=length):
            text = "".join(digits)

            assert count_decodings(text) == reference(text), text


def test_handles_a_long_string() -> None:
    """Handles ten thousand digits within the time limit.

    All ones, so the count is exactly a Fibonacci number -- the (n+1)th, since
    each prefix extends one way or two. Checked against a Fibonacci computed
    independently, which is a far stronger expectation than a magnitude: it has
    thousands of digits and Python holds it exactly, so a solution that caps,
    mods or floats the count disagrees immediately.
    """
    size = 10_000
    previous, current = 1, 1
    for _ in range(size):
        previous, current = current, previous + current

    assert count_decodings("1" * size) == previous
    assert count_decodings("1" * 10) == 89
