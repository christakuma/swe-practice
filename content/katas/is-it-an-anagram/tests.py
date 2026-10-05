"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections import Counter
from itertools import product

from solution import is_anagram


def test_accepts_a_rearrangement() -> None:
    """Reports True for a rearrangement of the same letters."""
    assert is_anagram("anagram", "nagaram") is True


def test_rejects_different_letters() -> None:
    """Reports False when the letters differ."""
    assert is_anagram("rat", "car") is False


def test_rejects_different_lengths() -> None:
    """Reports False when the strings are different lengths."""
    assert is_anagram("a", "ab") is False
    assert is_anagram("ab", "a") is False


def test_rejects_a_proper_prefix() -> None:
    """Reports False when the second string is a prefix of the first.

    A count-down tally only detects characters used too often; it never
    inspects the leftovers. Without a length check this returns True with a
    character still outstanding, and every proper prefix passes.
    """
    assert is_anagram("ab", "a") is False
    assert is_anagram("aab", "ab") is False
    assert is_anagram("abc", "") is False


def test_handles_empty_strings() -> None:
    """Reports True for two empty strings."""
    assert is_anagram("", "") is True
    assert is_anagram("", "a") is False


def test_respects_multiplicities() -> None:
    """Distinguishes strings with the same letters in different quantities.

    Both strings hold only a and b, so a solution comparing *sets* of
    characters accepts these.
    """
    assert is_anagram("aab", "abb") is False
    assert is_anagram("aabb", "abbb") is False
    assert is_anagram("aab", "aba") is True


def test_is_case_sensitive() -> None:
    """Treats upper and lower case as different characters."""
    assert is_anagram("Ab", "ab") is False
    assert is_anagram("Ab", "bA") is True


def test_includes_spaces_and_punctuation() -> None:
    """Counts every character, not just letters."""
    assert is_anagram("a b", "b a") is True
    assert is_anagram("a b", "ab ") is True
    assert is_anagram("a b", "ab") is False
    assert is_anagram("a!b", "b!a") is True


def test_handles_non_ascii_characters() -> None:
    """Counts characters outside ASCII the same way.

    A solution indexing a fixed array of twenty-six slots raises or silently
    miscounts here.
    """
    assert is_anagram("café", "éfac") is True
    assert is_anagram("café", "cafe") is False
    assert is_anagram("日本語", "語本日") is True


def test_handles_a_single_character() -> None:
    """Compares one-character strings."""
    assert is_anagram("a", "a") is True
    assert is_anagram("a", "b") is False


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert is_anagram("ab", "ba") is True
    assert is_anagram("ab", "bb") is False


def test_agrees_with_a_counter_on_every_short_pair() -> None:
    """Matches a Counter comparison for every pair of strings up to length five.

    Every string over three letters against every other, which is about a
    hundred and twenty thousand pairs. The failures in this kata -- a missing
    length check, comparing sets instead of counts -- are all about
    multiplicity, so enumerating the multiplicities beats choosing examples.
    """
    strings = [
        "".join(letters)
        for length in range(6)
        for letters in product("abc", repeat=length)
    ]
    for first in strings:
        for second in strings:
            expected = Counter(first) == Counter(second)

            assert is_anagram(first, second) is expected, (first, second)


def test_handles_long_strings() -> None:
    """Compares strings of a million characters within the time limit.

    Equal counts, different arrangements -- so the answer needs the full tally
    rather than an early mismatch.
    """
    first = "ab" * 500_000
    second = "a" * 500_000 + "b" * 500_000

    assert is_anagram(first, second) is True
    assert is_anagram(first, second[:-1] + "a") is False
