"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections import Counter
from itertools import product

from solution import longest_run


def reference(text: str, k: int) -> int:
    """Longest feasible window by checking every substring -- an oracle.

    It recounts each window from scratch, so it shares nothing with the
    sliding-window bookkeeping and in particular nothing with the stale
    most-common counter.
    """
    best = 0
    for start in range(len(text)):
        for stop in range(start + 1, len(text) + 1):
            window = text[start:stop]
            if len(window) - max(Counter(window).values()) <= k:
                best = max(best, len(window))
    return best


def test_handles_the_worked_examples() -> None:
    """Returns the documented answers."""
    assert longest_run("ABAB", 2) == 4
    assert longest_run("AABABBA", 1) == 4


def test_handles_no_budget() -> None:
    """Returns the longest existing run when no changes are allowed."""
    assert longest_run("ABCDE", 0) == 1
    assert longest_run("AABBBCC", 0) == 3
    assert longest_run("AAAA", 0) == 4


def test_handles_an_empty_string() -> None:
    """Returns 0 for an empty string, whatever the budget."""
    assert longest_run("", 0) == 0
    assert longest_run("", 5) == 0


def test_handles_a_budget_bigger_than_the_string() -> None:
    """Returns the whole length when everything can be replaced."""
    assert longest_run("ABCDE", 5) == 5
    assert longest_run("ABCDE", 100) == 5
    assert longest_run("A", 10) == 1


def test_handles_a_uniform_string() -> None:
    """Returns the full length when no changes are needed."""
    assert longest_run("AAAAA", 0) == 5
    assert longest_run("AAAAA", 3) == 5


def test_does_not_count_a_window_it_cannot_afford() -> None:
    """Keeps the window within budget.

    One replacement cannot make "ABCDE" uniform beyond two characters. A
    solution that never shrinks the window reports 5.
    """
    assert longest_run("ABCDE", 1) == 2
    assert longest_run("ABCDE", 2) == 3


def test_finds_a_run_that_is_not_at_the_start() -> None:
    """Finds the best window in the middle or at the end of the string."""
    assert longest_run("ABCDDDDE", 1) == 5
    assert longest_run("XYZAAAA", 1) == 5


def test_prefers_the_cheaper_majority_character() -> None:
    """Chooses whichever character is most common in the window.

    The window's best character is not always the string's most common one --
    here the Bs cluster even though there are more As overall.
    """
    assert longest_run("AABBBBAA", 1) == 5


def test_treats_case_as_significant() -> None:
    """Does not fold case."""
    assert longest_run("aA", 0) == 1
    assert longest_run("aA", 1) == 2


def test_handles_non_letter_characters() -> None:
    """Works for any characters, not just letters.

    A solution indexing a fixed array of twenty-six slots fails here.
    """
    assert longest_run("..::..", 0) == 2
    assert longest_run("1223", 1) == 3


def test_agrees_with_brute_force_on_every_binary_string() -> None:
    """Matches the substring search for every string of A and B up to length nine.

    Crossed with every budget from 0 to 3, which is about four thousand cases.
    This is also what pins the never-decreased most-common counter: it is
    deliberately allowed to go stale, and a sweep against an oracle that
    recounts every window is how that is justified rather than assumed.
    """
    for length in range(10):
        for characters in product("AB", repeat=length):
            text = "".join(characters)
            for k in range(4):
                assert longest_run(text, k) == reference(text, k), (text, k)


def test_agrees_with_brute_force_on_every_ternary_string() -> None:
    """Matches the substring search for every string of A, B and C up to length six.

    A third character makes the most-common count change hands more often
    inside a single window, which is where the stale counter is under the most
    pressure.
    """
    for length in range(7):
        for characters in product("ABC", repeat=length):
            text = "".join(characters)
            for k in range(4):
                assert longest_run(text, k) == reference(text, k), (text, k)


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(longest_run("AB", 1)) is int


def test_scans_a_long_string_in_one_pass() -> None:
    """Handles a million characters within the time limit.

    Checking every substring is five times ten to the eleventh windows. The
    answer spans a long uniform run plus the budget, so it requires the window
    to have grown across most of the string.
    """
    text = "AB" * 250_000 + "C" * 500_000

    assert longest_run(text, 0) == 500_000
    assert longest_run(text, 2) == 500_002
