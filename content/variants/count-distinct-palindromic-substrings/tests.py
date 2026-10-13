"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_distinct_palindromes


def by_every_substring(text: str) -> int:
    pieces = {
        text[start:end]
        for start in range(len(text))
        for end in range(start + 1, len(text) + 1)
    }
    return sum(piece == piece[::-1] for piece in pieces)


def test_counts_a_repeated_palindrome_once() -> None:
    """Returns 3 for "aaa", where counting by position gives 6."""
    assert count_distinct_palindromes("aaa") == 3


def test_counts_odd_and_even_palindromes() -> None:
    """Counts palindromes centred on a character and on a gap."""
    assert count_distinct_palindromes("abab") == 4
    assert count_distinct_palindromes("abba") == 4


def test_counts_single_characters_once_each() -> None:
    """Counts each different character once."""
    assert count_distinct_palindromes("abc") == 3
    assert count_distinct_palindromes("aba") == 3


def test_handles_trivial_strings() -> None:
    """Returns 0 for an empty string and 1 for one character."""
    assert count_distinct_palindromes("") == 0
    assert count_distinct_palindromes("z") == 1


def test_counts_every_character_exactly() -> None:
    """Does not fold case or skip punctuation."""
    assert count_distinct_palindromes("aA") == 2
    assert count_distinct_palindromes("a,a") == 3


def test_agrees_with_listing_every_substring() -> None:
    """Matches a list-every-substring count for every short string."""
    for alphabet, longest in (("ab", 10), ("abc", 7)):
        for size in range(longest + 1):
            for letters in product(alphabet, repeat=size):
                text = "".join(letters)
                expected = by_every_substring(text)
                assert count_distinct_palindromes(text) == expected, text


def test_returns_an_int() -> None:
    """Returns an int rather than a set or a bool."""
    assert type(count_distinct_palindromes("ab")) is int


def test_handles_a_thousand_characters() -> None:
    """Handles a thousand characters within the time limit."""
    assert count_distinct_palindromes("a" * 1000) == 1000
    assert count_distinct_palindromes("ab" * 500) == 1000
