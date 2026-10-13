"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_run


def by_every_window(text: str, k: int, target: str) -> int:
    return max(
        (
            end - start
            for start in range(len(text) + 1)
            for end in range(start, len(text) + 1)
            if sum(character != target for character in text[start:end]) <= k
        ),
        default=0,
    )


def test_makes_a_run_of_the_chosen_character() -> None:
    """Returns the longest run of the target, for either target."""
    assert longest_run("AABABBA", 1, "A") == 4
    assert longest_run("AABABBA", 1, "B") == 4


def test_the_target_decides_the_answer() -> None:
    """Gives different answers for different targets on the same string."""
    assert longest_run("AAAB", 0, "A") == 3
    assert longest_run("AAAB", 0, "B") == 1


def test_a_target_that_is_absent_costs_a_change_per_position() -> None:
    """Returns k, at most, when the target does not appear."""
    assert longest_run("AAAA", 0, "B") == 0
    assert longest_run("AAAA", 2, "B") == 2
    assert longest_run("AAAA", 9, "B") == 4


def test_handles_an_empty_string() -> None:
    """Returns 0 for an empty string."""
    assert longest_run("", 3, "A") == 0


def test_agrees_with_measuring_every_window() -> None:
    """Matches an every-window search for every short string, k and target."""
    for length in range(8):
        for letters in product("ABC", repeat=length):
            text = "".join(letters)
            for k in range(4):
                for target in "AZ":
                    expected = by_every_window(text, k, target)
                    assert longest_run(text, k, target) == expected, (text, k, target)


def test_scans_a_million_characters() -> None:
    """Scans a million characters within the time limit."""
    text = "AB" * 500_000

    assert longest_run(text, 100, "A") == 201
    assert longest_run(text, 0, "C") == 0
