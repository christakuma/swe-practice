"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_non_decreasing


def by_table(numbers: list[int]) -> int:
    """The quadratic table: the best subsequence ending at each position."""
    best = [1] * len(numbers)
    for end in range(len(numbers)):
        for earlier in range(end):
            if numbers[earlier] <= numbers[end]:
                best[end] = max(best[end], best[earlier] + 1)
    return max(best, default=0)


def test_counts_equal_values() -> None:
    """Lets a repeated value extend the subsequence."""
    assert longest_non_decreasing([7, 7, 7, 7]) == 4


def test_mixes_rises_and_repeats() -> None:
    """Finds a subsequence that both rises and repeats."""
    assert longest_non_decreasing([1, 3, 3, 2, 3]) == 4
    assert longest_non_decreasing([2, 2, 1, 2, 2]) == 4


def test_still_rejects_a_fall() -> None:
    """Returns 1 when every value is smaller than the last."""
    assert longest_non_decreasing([5, 4, 3, 2, 1]) == 1


def test_handles_trivial_lists() -> None:
    """Returns 0 for nothing and 1 for one value."""
    assert longest_non_decreasing([]) == 0
    assert longest_non_decreasing([9]) == 1


def test_agrees_with_the_quadratic_table() -> None:
    """Matches the quadratic table for every list up to length seven."""
    for length in range(8):
        for chosen in product(range(4), repeat=length):
            numbers = list(chosen)
            assert longest_non_decreasing(numbers) == by_table(numbers), numbers


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [3, 1, 2]

    longest_non_decreasing(numbers)

    assert numbers == [3, 1, 2]


def test_handles_a_hundred_thousand_values() -> None:
    """Handles a hundred thousand values within the time limit."""
    size = 100_000
    sawtooth = [index % 1000 for index in range(size)]

    assert longest_non_decreasing(sawtooth) == 1000 + 99
    assert longest_non_decreasing([5] * size) == size
