"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import is_almost_palindrome


def by_deleting(text: str) -> bool:
    """Try the string as it is, then with each character removed in turn."""
    candidates = [text] + [text[:at] + text[at + 1 :] for at in range(len(text))]
    return any(candidate == candidate[::-1] for candidate in candidates)


def test_accepts_a_string_one_deletion_from_a_palindrome() -> None:
    """Accepts a string that one deletion turns into a palindrome."""
    assert is_almost_palindrome("abca") is True


def test_accepts_a_palindrome_as_it_is() -> None:
    """Accepts a string that is already a palindrome."""
    assert is_almost_palindrome("racecar") is True
    assert is_almost_palindrome("abba") is True


def test_rejects_a_string_that_needs_two_deletions() -> None:
    """Rejects a string that one deletion cannot fix."""
    assert is_almost_palindrome("abc") is False
    assert is_almost_palindrome("abcdea") is False


def test_handles_empty_and_very_short_strings() -> None:
    """Accepts the empty string and any string of one or two characters."""
    assert is_almost_palindrome("") is True
    assert is_almost_palindrome("x") is True
    assert is_almost_palindrome("xy") is True


def test_tries_deleting_from_the_right() -> None:
    """Accepts a string that only deleting the right-hand character fixes."""
    assert is_almost_palindrome("abbca") is True


def test_tries_deleting_from_the_left() -> None:
    """Accepts a string that only deleting the left-hand character fixes."""
    assert is_almost_palindrome("acbba") is True


def test_counts_every_character_exactly() -> None:
    """Does not fold case or skip punctuation.

    The standard version calls both of these palindromes. Here "A, a" is
    four characters and no single deletion mirrors them.
    """
    assert is_almost_palindrome("Aa") is True
    assert is_almost_palindrome("AbBa") is False
    assert is_almost_palindrome("A, a") is False


def test_does_not_allow_a_second_deletion_further_in() -> None:
    """Rejects a string whose inside needs a deletion of its own."""
    assert is_almost_palindrome("xabcay") is False
    assert is_almost_palindrome("abcbda") is True
    assert is_almost_palindrome("abcbdea") is False


def test_agrees_with_trying_every_deletion() -> None:
    """Matches a try-every-deletion check for every short string.

    Every string over a and b up to length ten, and over a, b and c up to
    length seven.
    """
    for alphabet, longest in (("ab", 10), ("abc", 7)):
        for length in range(longest + 1):
            for letters in product(alphabet, repeat=length):
                text = "".join(letters)
                assert is_almost_palindrome(text) is by_deleting(text), text


def test_checks_two_hundred_thousand_characters() -> None:
    """Checks a long string within the time limit.

    A hundred thousand a's each side of one stray b off-centre, which one
    deletion fixes; then a second stray character, which it cannot. Trying
    each deletion in turn is two hundred thousand scans of two hundred
    thousand characters.
    """
    half = "a" * 100_000

    assert is_almost_palindrome(half[:-7] + "b" + half) is True
    assert is_almost_palindrome(half[:-7] + "b" + half[:-9] + "c" + "a" * 20) is False
