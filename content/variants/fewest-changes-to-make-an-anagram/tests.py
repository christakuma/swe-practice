"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import changes_needed


def by_searching(first: str, second: str, alphabet: str) -> int:
    """The fewest positions at which some anagram of `first` differs from `second`."""
    if len(first) != len(second):
        return -1
    target = sorted(first)
    return min(
        sum(a != b for a, b in zip(candidate, second, strict=True))
        for candidate in product(alphabet, repeat=len(second))
        if sorted(candidate) == target
    )


def test_anagrams_need_no_changes() -> None:
    """Returns 0 when the second string is already a rearrangement."""
    assert changes_needed("listen", "silent") == 0
    assert changes_needed("aab", "aba") == 0


def test_identical_strings_need_no_changes() -> None:
    """Returns 0 for equal strings, including two empty ones."""
    assert changes_needed("same", "same") == 0
    assert changes_needed("", "") == 0


def test_counts_one_replacement_for_one_swap_of_counts() -> None:
    """Counts a surplus and the shortfall it fills as a single change."""
    assert changes_needed("bab", "aba") == 1
    assert changes_needed("abcd", "abcc") == 1


def test_counts_every_character_when_nothing_is_shared() -> None:
    """Returns the length when the strings have no characters in common."""
    assert changes_needed("abc", "xyz") == 3
    assert changes_needed("aaaa", "bbbb") == 4


def test_position_does_not_matter() -> None:
    """Ignores where the characters are and looks only at how many there are.

    These pairs differ at every position and are anagrams all the same.
    """
    assert changes_needed("abcd", "dcba") == 0
    assert changes_needed("aabb", "bbaa") == 0
    assert changes_needed("abab", "babb") == 1


def test_multiplicity_matters() -> None:
    """Counts repeated characters as many times as they are short."""
    assert changes_needed("aaab", "abbb") == 2
    assert changes_needed("aabbcc", "abcabd") == 1


def test_different_lengths_cannot_be_fixed() -> None:
    """Returns -1 when the strings are different lengths."""
    assert changes_needed("ab", "abc") == -1
    assert changes_needed("abc", "ab") == -1
    assert changes_needed("", "a") == -1


def test_compares_characters_exactly() -> None:
    """Treats case, spaces and accents as distinguishing characters."""
    assert changes_needed("Ab", "ab") == 1
    assert changes_needed("a b", "ab ") == 0
    assert changes_needed("é", "e") == 1


def test_is_symmetric() -> None:
    """Gives the same count whichever string is the one being changed."""
    assert changes_needed("aabbb", "abccc") == changes_needed("abccc", "aabbb") == 3


def test_agrees_with_searching_every_anagram() -> None:
    """Matches a search over every anagram for every short pair.

    Every pair of strings of up to four characters over "abc".
    """
    words = [
        "".join(letters) for size in range(5) for letters in product("abc", repeat=size)
    ]
    for first in words:
        for second in words:
            if abs(len(first) - len(second)) <= 1:
                expected = by_searching(first, second, "abc")
                assert changes_needed(first, second) == expected, (first, second)


def test_handles_a_million_characters() -> None:
    """Counts two strings of a million characters within the time limit."""
    first = "abcde" * 200_000
    second = "abcdf" * 200_000

    assert changes_needed(first, second) == 200_000
    assert changes_needed(first, first[::-1]) == 0
