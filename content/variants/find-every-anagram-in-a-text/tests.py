"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import anagram_positions


def by_sorting(text: str, pattern: str) -> list[int]:
    width = len(pattern)
    return [
        start
        for start in range(len(text) - width + 1)
        if sorted(text[start : start + width]) == sorted(pattern)
    ]


def test_finds_the_documented_positions() -> None:
    """Finds both anagrams in the worked example."""
    assert anagram_positions("cbaebabacd", "abc") == [0, 6]


def test_counts_overlapping_matches() -> None:
    """Reports every overlapping match."""
    assert anagram_positions("abab", "ab") == [0, 1, 2]
    assert anagram_positions("aaaa", "aa") == [0, 1, 2]


def test_compares_counts_not_just_letters() -> None:
    """Rejects a window with the right letters in the wrong quantities."""
    assert anagram_positions("aab", "ab") == [1]
    assert anagram_positions("abb", "aab") == []


def test_handles_a_pattern_longer_than_the_text() -> None:
    """Returns nothing when the pattern cannot fit."""
    assert anagram_positions("ab", "abc") == []
    assert anagram_positions("", "a") == []


def test_compares_exactly() -> None:
    """Distinguishes case and counts every character."""
    assert anagram_positions("aA a", "Aa") == [0]
    assert anagram_positions("a b", " a") == [0]


def test_agrees_with_sorting_each_window() -> None:
    """Matches a sort-every-window search for every short text and pattern."""
    for alphabet, longest in (("ab", 8), ("abc", 6)):
        for size in range(longest + 1):
            for letters in product(alphabet, repeat=size):
                text = "".join(letters)
                for width in range(1, 4):
                    for chosen in product(alphabet, repeat=width):
                        pattern = "".join(chosen)
                        expected = by_sorting(text, pattern)
                        assert anagram_positions(text, pattern) == expected, (
                            text,
                            pattern,
                        )


def test_searches_a_long_text_for_a_long_pattern() -> None:
    """Searches 300,000 characters for a 100,000-character pattern in time."""
    pattern = "ab" * 50_000
    text = "ab" * 150_000

    assert anagram_positions(text, pattern) == list(range(200_001))
    assert anagram_positions(text, pattern + "c") == []
