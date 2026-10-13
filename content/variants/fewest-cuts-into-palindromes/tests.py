"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import fewest_cuts


def by_trying_every_cutting(text: str) -> int:
    """The fewest cuts among every way of cutting that leaves only palindromes."""
    gaps = len(text) - 1
    best = max(gaps, 0)
    for chosen in range(2 ** max(gaps, 0)):
        pieces = []
        start = 0
        for gap in range(gaps):
            if chosen >> gap & 1:
                pieces.append(text[start : gap + 1])
                start = gap + 1
        pieces.append(text[start:])
        if all(piece == piece[::-1] for piece in pieces):
            best = min(best, len(pieces) - 1)
    return best


def test_a_palindrome_needs_no_cuts() -> None:
    """Returns 0 for a string that is already a palindrome."""
    assert fewest_cuts("racecar") == 0
    assert fewest_cuts("abba") == 0
    assert fewest_cuts("a") == 0


def test_the_empty_string_needs_no_cuts() -> None:
    """Returns 0 for the empty string."""
    assert fewest_cuts("") == 0


def test_cuts_once() -> None:
    """Returns 1 when two palindromes cover the string."""
    assert fewest_cuts("aab") == 1
    assert fewest_cuts("ab") == 1
    assert fewest_cuts("abbac") == 1


def test_cuts_between_every_character_when_it_must() -> None:
    """Returns one less than the length when no two characters can share a piece."""
    assert fewest_cuts("abc") == 2
    assert fewest_cuts("abcdef") == 5


def test_uses_even_length_palindromes() -> None:
    """Finds pieces of even length, which have no middle character."""
    assert fewest_cuts("aabb") == 1
    assert fewest_cuts("baabcc") == 1
    assert fewest_cuts("xaax") == 0


def test_does_not_take_the_longest_piece_first() -> None:
    """Passes over the longest palindrome at the front when a shorter one is better."""
    assert fewest_cuts("abaab") == 1
    assert fewest_cuts("aaabaa") == 1


def test_counts_cuts_and_not_pieces() -> None:
    """Returns the number of cuts, which is one less than the number of pieces."""
    assert fewest_cuts("aabbcc") == 2
    assert fewest_cuts("abacdc") == 1


def test_compares_characters_exactly() -> None:
    """Treats upper and lower case, and punctuation, as different characters."""
    assert fewest_cuts("Aa") == 1
    assert fewest_cuts("a,a") == 0
    assert fewest_cuts("a, a") == 3


def test_agrees_with_trying_every_cutting() -> None:
    """Matches an exhaustive search for every short string.

    Every string of up to nine characters over "ab", and up to six over "abc".
    """
    for alphabet, longest in (("ab", 9), ("abc", 6)):
        for size in range(longest + 1):
            for letters in product(alphabet, repeat=size):
                text = "".join(letters)
                assert fewest_cuts(text) == by_trying_every_cutting(text), text


def test_handles_a_long_string_of_one_character() -> None:
    """Handles a thousand equal characters, where every substring is a palindrome."""
    assert fewest_cuts("a" * 1000) == 0
    assert fewest_cuts("a" * 500 + "b" + "a" * 499) == 1


def test_handles_a_long_string_with_no_repeats_nearby() -> None:
    """Handles a thousand characters that need a cut between every pair."""
    text = "abcd" * 250

    assert fewest_cuts(text) == 999
