"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_run


def by_sorting(numbers: list[int]) -> tuple[int, int] | None:
    runs: list[tuple[int, int]] = []
    for value in sorted(set(numbers)):
        if runs and runs[-1][1] == value - 1:
            runs[-1] = (runs[-1][0], value)
        else:
            runs.append((value, value))
    return min(runs, key=lambda run: (run[0] - run[1], run[0]), default=None)


def test_returns_the_ends_of_the_longest_run() -> None:
    """Returns the lowest and highest values of the longest run."""
    assert longest_run([100, 4, 200, 1, 3, 2]) == (1, 4)


def test_breaks_a_tie_towards_the_lower_start() -> None:
    """Returns the lower-starting run when two are equally long."""
    assert longest_run([10, 11, 1, 2]) == (1, 2)
    assert longest_run([1, 2, 10, 11]) == (1, 2)
    assert longest_run([7, 3]) == (3, 3)


def test_handles_duplicates_and_single_values() -> None:
    """Returns a run of one for a repeated value."""
    assert longest_run([5, 5, 5]) == (5, 5)
    assert longest_run([9]) == (9, 9)


def test_returns_none_for_an_empty_list() -> None:
    """Returns None when there are no values."""
    assert longest_run([]) is None


def test_spans_zero() -> None:
    """Follows a run through negative values and zero."""
    assert longest_run([-1, 1, 0, -2, 5]) == (-2, 1)


def test_agrees_with_sorting_for_every_short_list() -> None:
    """Matches a sort-based search for every list up to length six."""
    for length in range(7):
        for chosen in product(range(-2, 4), repeat=length):
            numbers = list(chosen)
            assert longest_run(numbers) == by_sorting(numbers), numbers


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [3, 1, 2]

    longest_run(numbers)

    assert numbers == [3, 1, 2]


def test_handles_a_long_run_and_many_short_ones() -> None:
    """Handles 200,000 values within the time limit."""
    size = 200_000

    assert longest_run(list(range(size, 0, -1))) == (1, size)
    assert longest_run(
        [3 * index + offset for index in range(size // 2) for offset in (0, 1)]
    ) == (0, 1)
