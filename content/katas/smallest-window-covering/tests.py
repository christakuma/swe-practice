"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections import Counter
from itertools import product

from solution import smallest_window


def reference(text: str, needed: str) -> str:
    """Shortest covering window by checking substrings -- an independent oracle.

    It recounts each candidate from scratch and never lets a tally go negative,
    so it shares none of the sliding window's bookkeeping.
    """
    if not needed:
        return ""
    need = Counter(needed)
    best: str | None = None
    for start in range(len(text)):
        for stop in range(start + 1, len(text) + 1):
            window = text[start:stop]
            counts = Counter(window)
            if all(counts[character] >= count for character, count in need.items()):
                if best is None or len(window) < len(best):
                    best = window
                break  # the shortest window starting here
    return best or ""


def test_finds_the_worked_example() -> None:
    """Returns the shortest covering window."""
    assert smallest_window("ADOBECODEBANC", "ABC") == "BANC"


def test_handles_a_single_character() -> None:
    """Covers a one-character requirement."""
    assert smallest_window("a", "a") == "a"
    assert smallest_window("xax", "a") == "a"


def test_requires_every_copy() -> None:
    """Returns "" when a character is not available often enough.

    Covering "aa" needs two a's. A solution comparing sets of characters, or
    one clamping its tally at zero, reports "a" here.
    """
    assert smallest_window("a", "aa") == ""
    assert smallest_window("aba", "aaa") == ""


def test_covers_repeated_requirements() -> None:
    """Covers a requirement that repeats a character."""
    assert smallest_window("aa", "aa") == "aa"
    assert smallest_window("abba", "ab") == "ab"
    assert smallest_window("aabba", "aab") == "aab"


def test_does_not_satisfy_a_requirement_twice() -> None:
    """Counts a repeated character against its own requirement only once.

    "AA" holds two A's and needs one A and one B. Decrementing the outstanding
    counter without checking the character was still needed reports "AA" as
    covering.
    """
    assert smallest_window("AA", "AB") == ""
    assert smallest_window("aaab", "ab") == "ab"


def test_handles_an_empty_requirement() -> None:
    """Returns "" when nothing needs covering."""
    assert smallest_window("ab", "") == ""
    assert smallest_window("", "") == ""


def test_handles_an_empty_text() -> None:
    """Returns "" when there is nothing to search."""
    assert smallest_window("", "a") == ""


def test_returns_the_earliest_of_several_shortest() -> None:
    """Returns the leftmost window when several tie for shortest.

    Two windows of width two cover "ab". A width comparison using <= instead
    of < replaces the first with the second.
    """
    assert smallest_window("abxab", "ab") == "ab"


def test_shrinks_past_surplus_characters() -> None:
    """Drops leading characters that are no longer needed.

    The window has to contract past the first a once a later a has arrived,
    which only works if the tally is allowed to record a surplus.
    """
    assert smallest_window("aaab", "ab") == "ab"
    assert smallest_window("acccb", "ab") == "acccb"
    assert smallest_window("aXXXab", "ab") == "ab"


def test_handles_a_window_that_is_the_whole_string() -> None:
    """Returns the entire string when nothing shorter covers."""
    assert smallest_window("abc", "abc") == "abc"
    assert smallest_window("cba", "abc") == "cba"


def test_ignores_characters_that_are_not_needed() -> None:
    """Allows extra characters inside the window."""
    assert smallest_window("aZZZb", "ab") == "aZZZb"


def test_is_case_sensitive() -> None:
    """Treats upper and lower case as different characters."""
    assert smallest_window("aB", "ab") == ""
    assert smallest_window("aBb", "ab") == "aBb"


def test_agrees_with_brute_force_across_every_small_pair() -> None:
    """Matches the substring oracle for every short text and requirement.

    Texts up to length seven over three characters, crossed with requirements
    up to length three over two -- around thirty thousand pairs. All three
    hazards here (clamping the tally, double-counting a requirement, the
    tie-break) need particular multiplicities to show up.
    """
    texts = [
        "".join(characters)
        for length in range(8)
        for characters in product("abc", repeat=length)
    ]
    requirements = [
        "".join(characters)
        for length in range(4)
        for characters in product("ab", repeat=length)
    ]
    for text in texts:
        for needed in requirements:
            assert smallest_window(text, needed) == reference(text, needed), (
                text,
                needed,
            )


def test_returns_an_actual_substring() -> None:
    """Returns a slice of the text that really does cover the requirement."""
    text = "ADOBECODEBANC"
    needed = "ABC"

    result = smallest_window(text, needed)

    assert result in text
    counts = Counter(result)
    assert all(
        counts[character] >= count for character, count in Counter(needed).items()
    )


def test_scans_a_long_text_in_one_pass() -> None:
    """Searches half a million characters within the time limit.

    A quarter million a's, then a quarter million b's, then a single c.
    Checking every substring is over a hundred billion windows.

    Covering "abc" has to reach from the last a all the way to the c, spanning
    the whole b block -- so the window grows to a quarter of the input and the
    shrink loop has to walk every b without ever being able to drop one.
    Covering "bc" is two characters at the very end, which is the same scan
    with the opposite outcome.
    """
    text = "a" * 250_000 + "b" * 250_000 + "c"

    covering_abc = smallest_window(text, "abc")
    assert len(covering_abc) == 250_002
    assert covering_abc == "a" + "b" * 250_000 + "c"

    assert smallest_window(text, "bc") == "bc"
    assert smallest_window(text, "d") == ""
