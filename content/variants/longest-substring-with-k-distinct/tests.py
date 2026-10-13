"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_run_with_k_distinct


def by_every_substring(text: str, k: int) -> int:
    """Measure every substring and keep the longest that is within the limit."""
    return max(
        (
            end - start
            for start in range(len(text) + 1)
            for end in range(start, len(text) + 1)
            if len(set(text[start:end])) <= k
        ),
        default=0,
    )


def test_finds_the_longest_substring_within_the_limit() -> None:
    """Returns the length of the longest substring with at most k distinct."""
    assert longest_run_with_k_distinct("eceba", 2) == 3


def test_allows_a_character_to_repeat() -> None:
    """Counts repeats of an allowed character, unlike the standard version."""
    assert longest_run_with_k_distinct("aaaa", 1) == 4
    assert longest_run_with_k_distinct("aabbaa", 2) == 6


def test_stops_at_one_character_too_many() -> None:
    """Does not extend into a character that would exceed the limit."""
    assert longest_run_with_k_distinct("aaabbbccc", 1) == 3
    assert longest_run_with_k_distinct("aaabbbccc", 2) == 6


def test_takes_the_whole_string_when_the_limit_allows() -> None:
    """Returns the full length when the string has no more than k distinct."""
    assert longest_run_with_k_distinct("abcabc", 3) == 6
    assert longest_run_with_k_distinct("abc", 10) == 3


def test_returns_zero_when_nothing_is_allowed() -> None:
    """Returns 0 for a limit of zero and for an empty string."""
    assert longest_run_with_k_distinct("abc", 0) == 0
    assert longest_run_with_k_distinct("", 3) == 0
    assert longest_run_with_k_distinct("", 0) == 0


def test_keeps_what_it_can_when_the_window_shrinks() -> None:
    """Shrinks the window only as far as it has to.

    To let the c's in, the window over "aba" has to lose its b -- and the a
    before it -- but the a after the b stays. A window that restarts from the
    new character finds "ccc" and reports 3.
    """
    assert longest_run_with_k_distinct("abaccc", 2) == 4


def test_forgets_a_character_that_has_left_the_window() -> None:
    """Stops counting a character once none of it is left in the window."""
    assert longest_run_with_k_distinct("abcbbbbcccbdddadacb", 2) == 10


def test_treats_every_character_as_distinct_from_the_rest() -> None:
    """Distinguishes case, spaces and punctuation."""
    assert longest_run_with_k_distinct("aA", 1) == 1
    assert longest_run_with_k_distinct("a a!", 2) == 3


def test_agrees_with_measuring_every_substring() -> None:
    """Matches an every-substring search for every short string and limit."""
    for alphabet, longest in (("ab", 8), ("abc", 6), ("abcd", 5)):
        for length in range(longest + 1):
            for letters in product(alphabet, repeat=length):
                text = "".join(letters)
                for k in range(5):
                    expected = by_every_substring(text, k)
                    assert longest_run_with_k_distinct(text, k) == expected, (text, k)


def test_scans_a_long_string() -> None:
    """Scans three hundred thousand characters within the time limit."""
    text = "abc" * 100_000

    assert longest_run_with_k_distinct(text, 2) == 2
    assert longest_run_with_k_distinct(text, 3) == 300_000
