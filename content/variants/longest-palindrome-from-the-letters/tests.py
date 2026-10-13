"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement, permutations

from solution import longest_palindrome


def by_trying_every_arrangement(text: str) -> str:
    """The answer by building every string the characters allow. An oracle."""
    best = ""
    for size in range(1, len(text) + 1):
        for letters in set(permutations(text, size)):
            candidate = "".join(letters)
            if candidate != candidate[::-1]:
                continue
            if len(candidate) > len(best) or candidate < best:
                best = candidate
    return best


def test_builds_a_palindrome_from_pairs_and_a_centre() -> None:
    """Uses every pair and puts the smallest spare character in the middle."""
    assert longest_palindrome("abccccdd") == "ccdadcc"


def test_rearranges_a_string_that_is_already_a_palindrome() -> None:
    """Returns the first palindrome in sorted order, not the one it was given."""
    assert longest_palindrome("racecar") == "acrerca"
    assert longest_palindrome("abba") == "abba"
    assert longest_palindrome("baab") == "abba"


def test_handles_an_empty_string_and_a_single_character() -> None:
    """Returns the empty string for no characters and the character for one."""
    assert longest_palindrome("") == ""
    assert longest_palindrome("x") == "x"


def test_with_no_pairs_returns_the_smallest_character() -> None:
    """Returns one character, the first in sorted order, when nothing repeats."""
    assert longest_palindrome("abc") == "a"
    assert longest_palindrome("cba") == "a"
    assert longest_palindrome("zyx") == "x"


def test_has_no_centre_when_every_count_is_even() -> None:
    """Returns an even-length palindrome when no character is left over."""
    assert longest_palindrome("aabb") == "abba"
    assert longest_palindrome("bbbbaa") == "abbbba"


def test_uses_the_pairs_inside_an_odd_count() -> None:
    """Takes pairs from a character that appears three or five times.

    Using only the characters with even counts would throw away two of the
    three a's.
    """
    assert longest_palindrome("aaab") == "aaa"
    assert longest_palindrome("aaabbbbb") == "abbabba"
    assert longest_palindrome("ccc") == "ccc"


def test_the_centre_is_the_smallest_spare_character() -> None:
    """Chooses the centre by sorted order, not by position or by count.

    In "abbb" the b's supply a pair and both letters have one to spare. The
    a sorts first, so it is the centre even though there are more b's.
    """
    assert longest_palindrome("abbb") == "bab"
    assert longest_palindrome("bbba") == "bab"
    assert longest_palindrome("cbaaa") == "aaa"
    assert longest_palindrome("zzyxx") == "xzyzx"


def test_the_left_half_is_sorted() -> None:
    """Arranges the pairs in ascending order from the outside in."""
    assert longest_palindrome("ccbbaa") == "abccba"
    assert longest_palindrome("dcbadcba") == "abcddcba"


def test_case_matters() -> None:
    """Does not pair an upper-case letter with its lower-case form."""
    assert longest_palindrome("Aa") == "A"
    assert longest_palindrome("AaAa") == "AaaA"
    assert longest_palindrome("aA") == "A"


def test_every_character_counts() -> None:
    """Treats spaces, digits and punctuation as characters like any other.

    A space sorts before every letter, so the pair of spaces goes outside.
    """
    assert longest_palindrome("a b a") == " aba "
    assert longest_palindrome("1!1!?") == "!1?1!"


def test_agrees_with_trying_every_arrangement() -> None:
    """Matches a build-everything search for every multiset of up to six letters.

    Every combination of a, b, c and B, of every size up to six, handed over
    in descending order so that the input is never already sorted.
    """
    for size in range(7):
        for letters in combinations_with_replacement("Babc", size):
            text = "".join(reversed(letters))
            assert longest_palindrome(text) == by_trying_every_arrangement(text), text


def test_handles_a_hundred_thousand_characters() -> None:
    """Builds a palindrome from a hundred thousand characters.

    Twenty-five letters appear four thousand times each, so the answer has
    no centre and its left half is two thousand of each letter in order.
    """
    letters = "abcdefghijklmnopqrstuvwxy"
    text = (letters[::-1] * 4_000)[:100_000]
    half = "".join(letter * 2_000 for letter in letters)

    assert longest_palindrome(text) == half + half[::-1]
