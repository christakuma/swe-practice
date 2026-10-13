"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import find_minimum


def test_finds_the_minimum_among_repeats() -> None:
    """Finds the smallest value when others repeat."""
    assert find_minimum([2, 2, 2, 0, 1]) == 0


def test_is_not_fooled_when_the_middle_equals_the_end() -> None:
    """Finds a minimum on either side of an uninformative comparison."""
    assert find_minimum([3, 3, 1, 3]) == 1
    assert find_minimum([3, 1, 3, 3]) == 1
    assert find_minimum([1, 1, 0, 1, 1, 1, 1]) == 0


def test_handles_lists_that_are_not_rotated() -> None:
    """Returns the first value of a list still in order."""
    assert find_minimum([1, 3, 3]) == 1
    assert find_minimum([1, 1, 2]) == 1


def test_handles_a_list_of_equal_values() -> None:
    """Returns the value when every value is the same."""
    assert find_minimum([5, 5, 5]) == 5
    assert find_minimum([5]) == 5


def test_agrees_with_min_for_every_small_rotated_list() -> None:
    """Matches the built-in minimum for every rotation of every short list."""
    for length in range(1, 9):
        for chosen in combinations_with_replacement(range(4), length):
            ordered = list(chosen)
            for turn in range(length):
                numbers = ordered[turn:] + ordered[:turn]
                assert find_minimum(numbers) == ordered[0], numbers


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [3, 3, 1, 2]

    find_minimum(numbers)

    assert numbers == [3, 3, 1, 2]


def test_answers_many_times_about_a_large_list() -> None:
    """Answers a thousand times about two million values in the time limit.

    The values are distinct, so each answer can halve its way down. Scanning
    for the minimum each time reads two billion values.
    """
    size = 2_000_000
    turn = 777_777
    numbers = list(range(turn, size)) + list(range(turn))

    for _ in range(1000):
        assert find_minimum(numbers) == 0
