"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import longest_palindromic_subsequence


def by_every_subsequence(text: str) -> int:
    for size in range(len(text), 0, -1):
        for kept in combinations(range(len(text)), size):
            candidate = [text[index] for index in kept]
            if candidate == candidate[::-1]:
                return size
    return 0


def test_skips_a_character_to_make_a_longer_palindrome() -> None:
    """Returns 4 where the longest palindromic substring is 3."""
    assert longest_palindromic_subsequence("bbbab") == 4


def test_finds_a_short_answer() -> None:
    """Finds the pair in a string with little symmetry."""
    assert longest_palindromic_subsequence("cbbd") == 2


def test_picks_characters_that_are_far_apart() -> None:
    """Builds a palindrome from characters that are not adjacent."""
    assert longest_palindromic_subsequence("character") == 5


def test_handles_trivial_strings() -> None:
    """Returns 0 for nothing, 1 for one character and 1 for all different."""
    assert longest_palindromic_subsequence("") == 0
    assert longest_palindromic_subsequence("x") == 1
    assert longest_palindromic_subsequence("abcd") == 1


def test_returns_the_whole_length_of_a_palindrome() -> None:
    """Returns the full length when the string is already a palindrome."""
    assert longest_palindromic_subsequence("racecar") == 7
    assert longest_palindromic_subsequence("aaaa") == 4


def test_counts_every_character_exactly() -> None:
    """Does not fold case or skip punctuation."""
    assert longest_palindromic_subsequence("Aa") == 1
    assert longest_palindromic_subsequence("a,a") == 3


def test_agrees_with_trying_every_subsequence() -> None:
    """Matches an every-subsequence search for every short string."""
    for alphabet, longest in (("ab", 9), ("abc", 7)):
        for size in range(longest + 1):
            for letters in product(alphabet, repeat=size):
                text = "".join(letters)
                expected = by_every_subsequence(text)
                assert longest_palindromic_subsequence(text) == expected, text


def test_handles_a_thousand_characters() -> None:
    """Handles a thousand characters within the time limit."""
    assert longest_palindromic_subsequence("ab" * 500) == 999
    assert longest_palindromic_subsequence("a" * 1000) == 1000
