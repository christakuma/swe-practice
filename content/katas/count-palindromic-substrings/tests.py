"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_palindromes


def reference(text: str) -> int:
    """Count by testing every substring -- an independent oracle."""
    return sum(
        1
        for start in range(len(text))
        for stop in range(start + 1, len(text) + 1)
        if text[start:stop] == text[start:stop][::-1]
    )


def test_counts_single_characters() -> None:
    """Counts each character as a palindrome when nothing longer is one."""
    assert count_palindromes("abc") == 3


def test_counts_overlapping_palindromes() -> None:
    """Counts identical substrings at different positions separately.

    "aaa" holds three single characters, two different "aa"s and one "aaa".
    A solution that collects distinct strings in a set reports 3.
    """
    assert count_palindromes("aaa") == 6


def test_handles_an_empty_string() -> None:
    """Counts nothing in an empty string."""
    assert count_palindromes("") == 0


def test_handles_a_single_character() -> None:
    """Counts one palindrome in a one-character string."""
    assert count_palindromes("a") == 1


def test_counts_even_length_palindromes() -> None:
    """Counts palindromes centred on a gap.

    The discriminating test: counting only character-centres gives 2 for "aa"
    and 4 for "aaa" -- numbers that look plausible and are wrong.
    """
    assert count_palindromes("aa") == 3
    assert count_palindromes("abba") == 6


def test_counts_a_fully_uniform_string() -> None:
    """Counts every substring of a uniform string.

    All n*(n+1)/2 substrings are palindromes when every character is equal,
    which makes this an exact closed-form check rather than a spot value.
    """
    for size in range(1, 12):
        expected = size * (size + 1) // 2

        assert count_palindromes("z" * size) == expected, size


def test_counts_nothing_longer_than_one_in_a_distinct_string() -> None:
    """Counts exactly n when no two characters are equal."""
    assert count_palindromes("abcdefg") == 7


def test_counts_a_nested_palindrome() -> None:
    """Counts the palindromes inside a longer palindrome."""
    assert count_palindromes("racecar") == 10


def test_treats_every_character_as_significant() -> None:
    """Does not fold case or skip punctuation."""
    assert count_palindromes("Aa") == 2
    assert count_palindromes("a,a") == 4
    assert count_palindromes("1221") == 6


def test_agrees_with_brute_force_on_every_binary_string() -> None:
    """Matches the substring count for every string of a and b up to length ten.

    Binary alphabets maximise palindrome density, so the gap-centre handling
    and the overlap counting are under constant pressure. About two thousand
    strings.
    """
    for length in range(11):
        for characters in product("ab", repeat=length):
            text = "".join(characters)

            assert count_palindromes(text) == reference(text), text


def test_agrees_with_brute_force_on_every_ternary_string() -> None:
    """Matches the substring count for every string of a, b and c up to length seven.

    A third character makes the "nothing longer than one" case common, which
    the binary sweep barely reaches.
    """
    for length in range(8):
        for characters in product("abc", repeat=length):
            text = "".join(characters)

            assert count_palindromes(text) == reference(text), text


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool or a float."""
    assert type(count_palindromes("aa")) is int


def test_counts_a_long_uniform_string_without_cubic_work() -> None:
    """Counts a three-thousand character uniform string within the time limit.

    The worst case for centre expansion: every centre grows to the full width,
    and there are about four and a half million palindromes to count. Building
    or slicing a string per palindrome does not finish.
    """
    size = 3_000

    assert count_palindromes("a" * size) == size * (size + 1) // 2
