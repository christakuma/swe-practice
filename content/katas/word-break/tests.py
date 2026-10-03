"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import can_segment


def test_splits_into_two_words() -> None:
    """Splits a string into two dictionary words."""
    assert can_segment("leetcode", ["leet", "code"]) is True


def test_reuses_a_word() -> None:
    """Uses the same word twice."""
    assert can_segment("applepenapple", ["apple", "pen"]) is True


def test_refuses_a_string_that_cannot_be_split() -> None:
    """Returns False when no sequence of words covers the string."""
    words = ["cats", "dog", "sand", "and", "cat"]

    assert can_segment("catsandog", words) is False


def test_beats_the_longest_match_first() -> None:
    """Finds a split that greedy longest-match misses.

    The longest word matching the start of `cars` is `car`, which leaves `s`
    and fails. Taking the shorter `ca` first leaves `rs`, which is a word.
    Greedy has no way to go back and try the shorter match.
    """
    assert can_segment("cars", ["car", "ca", "rs"]) is True


def test_accepts_an_empty_string() -> None:
    """Returns True for an empty string: the empty sequence covers it."""
    assert can_segment("", ["a"]) is True


def test_refuses_anything_with_an_empty_dictionary() -> None:
    """Returns False for a non-empty string and no words."""
    assert can_segment("a", []) is False


def test_ignores_unused_words() -> None:
    """Does not require every word to be used."""
    assert can_segment("abcd", ["a", "abc", "b", "cd"]) is True


def test_handles_overlapping_short_words() -> None:
    """Splits a run that several words could cover."""
    assert can_segment("aaaaaaa", ["a", "aa", "aaa"]) is True


def test_handles_a_long_string_with_no_split_quickly() -> None:
    """Refuses a long string without trying every way to cut it.

    Three hundred a's followed by a b, with only a-words available. Every
    prefix is reachable and nothing covers the final b, so an exponential
    search explores astronomically many splits before giving up.
    """
    assert can_segment("a" * 300 + "b", ["a", "aa", "aaa", "aaaa"]) is False


def test_handles_a_long_string_with_a_split_quickly() -> None:
    """Accepts a long string made entirely of dictionary words."""
    assert can_segment("ab" * 500, ["ab", "ba"]) is True
