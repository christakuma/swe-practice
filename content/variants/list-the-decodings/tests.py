"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import decodings


def encoded(letters: str) -> str:
    return "".join(str(ord(letter) - 64) for letter in letters)


def how_many(digits: str) -> int:
    """The number of decodings, by the two-variable count."""
    if not digits:
        return 0
    before, here = 0, 1
    for at, digit in enumerate(digits):
        ways = here if digit != "0" else 0
        if at and digits[at - 1] != "0" and int(digits[at - 1 : at + 1]) <= 26:
            ways += before
        before, here = here, ways
    return here


def test_lists_the_documented_decodings() -> None:
    """Lists the decodings of the worked examples, in order."""
    assert decodings("12") == ["AB", "L"]
    assert decodings("226") == ["BBF", "BZ", "VF"]


def test_respects_zeros() -> None:
    """Uses a zero only as the second digit of 10 or 20."""
    assert decodings("10") == ["J"]
    assert decodings("2101") == ["BJA"]
    assert decodings("06") == []
    assert decodings("100") == []


def test_does_not_pair_digits_above_twenty_six() -> None:
    """Does not read 27 as one letter."""
    assert decodings("27") == ["BG"]


def test_returns_nothing_for_the_empty_string() -> None:
    """Returns an empty list for the empty string."""
    assert decodings("") == []


def test_every_decoding_is_right_and_none_is_missing() -> None:
    """Returns exactly the right strings for every short digit string.

    Each returned string must encode back to the digits; they must be
    distinct and sorted; and there must be as many as an independent count
    says there are.
    """
    for size in range(1, 8):
        for chosen in product("0123", repeat=size):
            digits = "".join(chosen)
            result = decodings(digits)
            assert all(encoded(letters) == digits for letters in result), digits
            assert result == sorted(set(result)), digits
            assert len(result) == how_many(digits), digits


def test_lists_a_long_string_of_ones() -> None:
    """Lists all 10,946 decodings of twenty ones within the time limit."""
    result = decodings("1" * 20)

    assert len(result) == 10_946
    assert result[0] == "A" * 20
    assert result[-1] == "K" * 10
