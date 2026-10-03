"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`, so they are
written as sentences about what the solution must do.
"""

from solution import longest_unique_run


def test_finds_a_run_in_the_middle_of_a_string() -> None:
    """Finds the longest distinct run when it is not at the start."""
    assert longest_unique_run("pwwkew") == 3


def test_handles_a_string_with_no_repeats_at_all() -> None:
    """Returns the whole length when every character is distinct."""
    assert longest_unique_run("abcdef") == 6


def test_handles_a_string_that_is_all_one_character() -> None:
    """Returns one when every character is the same."""
    assert longest_unique_run("bbbbb") == 1


def test_handles_an_empty_string() -> None:
    """Returns zero for an empty string."""
    assert longest_unique_run("") == 0


def test_does_not_let_a_stale_index_drag_the_window_back() -> None:
    """Keeps the window valid when a repeat was last seen before it began.

    `abba` is the shortest input that separates a correct sliding window from
    one that moves `start` to `last_seen[c] + 1` unconditionally. At the final
    `a`, the previous `a` is at index 0 -- behind a window that already starts
    at 2 -- so an unguarded jump moves `start` backwards to 1 and reports 3.
    """
    assert longest_unique_run("abba") == 2


def test_handles_a_repeat_separated_by_the_whole_string() -> None:
    """Handles a character that repeats only at the very end."""
    assert longest_unique_run("abcdea") == 5


def test_handles_spaces_and_punctuation() -> None:
    """Treats every character as a character, spaces included."""
    assert longest_unique_run("a b!a") == 4


def test_handles_a_long_string_quickly() -> None:
    """Finds the answer in a string far too long to re-scan per character.

    Thirty thousand characters of a repeating four-character cycle. A window
    that walks `start` forward one step at a time is quadratic here; one that
    jumps past the previous occurrence is linear. The time limit is what fails
    the quadratic version -- the complexity you declare is never auto-graded.
    """
    assert longest_unique_run("abcd" * 7500) == 4
