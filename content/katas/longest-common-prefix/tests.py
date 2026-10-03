"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import longest_common_prefix


def test_finds_a_shared_prefix() -> None:
    """Returns the characters every word begins with."""
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"


def test_returns_nothing_when_there_is_no_shared_prefix() -> None:
    """Returns the empty string when the first characters differ."""
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""


def test_handles_one_word_being_the_prefix() -> None:
    """Returns the shortest word when it is a prefix of the others.

    A solution driven by the length of the *first* word reads past the end of
    a shorter one here, or returns "interview".
    """
    assert longest_common_prefix(["interview", "inter", "internal"]) == "inter"


def test_handles_the_shortest_word_coming_last() -> None:
    """Does not depend on where the shortest word appears."""
    assert longest_common_prefix(["internal", "interview", "inter"]) == "inter"


def test_handles_a_single_word() -> None:
    """Returns the whole word when there is only one."""
    assert longest_common_prefix(["alone"]) == "alone"


def test_handles_no_words() -> None:
    """Returns the empty string for no words."""
    assert longest_common_prefix([]) == ""


def test_handles_an_empty_string_among_the_words() -> None:
    """Returns nothing when any word is empty."""
    assert longest_common_prefix(["abc", "", "abd"]) == ""


def test_handles_identical_words() -> None:
    """Returns the whole word when every word is the same."""
    assert longest_common_prefix(["same", "same", "same"]) == "same"


def test_is_case_sensitive() -> None:
    """Treats upper and lower case as different characters."""
    assert longest_common_prefix(["Apple", "apple"]) == ""


def test_handles_many_long_words_quickly() -> None:
    """Handles a long list of long words.

    Five thousand words sharing a two-hundred-character prefix. The answer is
    found by shrinking a candidate, not by comparing every pair of words.
    """
    words = [("x" * 200) + f"{index}" for index in range(5_000)]

    assert longest_common_prefix(words) == "x" * 200
