"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import smallest_window


def by_every_substring(text: str) -> str:
    needed = set(text)
    best = ""
    for start in range(len(text)):
        for end in range(start + 1, len(text) + 1):
            piece = text[start:end]
            if set(piece) == needed and (not best or len(piece) < len(best)):
                best = piece
    return best


def test_finds_the_shortest_window() -> None:
    """Returns the shortest substring with every character of the text."""
    assert smallest_window("aabcbcdbca") == "dbca"


def test_one_of_each_is_enough() -> None:
    """Does not require a character as often as the text has it."""
    assert smallest_window("aaaa") == "a"
    assert smallest_window("aabb") == "ab"


def test_returns_the_earliest_of_equals() -> None:
    """Returns the leftmost window when several tie."""
    assert smallest_window("abca") == "abc"
    assert smallest_window("abab") == "ab"


def test_handles_trivial_strings() -> None:
    """Returns "" for an empty string and the character for a single one."""
    assert smallest_window("") == ""
    assert smallest_window("z") == "z"


def test_returns_the_whole_text_when_nothing_shorter_works() -> None:
    """Returns the entire string when every character is needed."""
    assert smallest_window("abc") == "abc"
    assert smallest_window("abbbc") == "abbbc"


def test_compares_exactly() -> None:
    """Treats case and punctuation as distinct characters."""
    assert smallest_window("aAa") == "aA"
    assert smallest_window("a a") == "a "


def test_agrees_with_checking_every_substring() -> None:
    """Matches an every-substring search for every short string."""
    for alphabet, longest in (("ab", 9), ("abc", 7), ("abcd", 5)):
        for size in range(longest + 1):
            for letters in product(alphabet, repeat=size):
                text = "".join(letters)
                assert smallest_window(text) == by_every_substring(text), text


def test_searches_a_million_characters() -> None:
    """Searches a million characters within the time limit."""
    text = "a" * 500_000 + "bc" + "a" * 500_000

    assert smallest_window(text) == "abc"
