"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import combinations

from solution import find_peak


class Watched(list[int]):
    """A list that counts how many of its values have been read."""

    reads = 0

    def __getitem__(self, index):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN204
        if isinstance(index, slice):
            self.reads += len(range(*index.indices(len(self))))
        else:
            self.reads += 1
        return super().__getitem__(index)

    def __iter__(self) -> Iterator[int]:
        for position in range(len(self)):
            yield self[position]


def mountain(size: int, peak: int) -> list[int]:
    """`size` values that rise to position `peak` and fall after it."""
    return [-abs(position - peak) * 3 for position in range(size)]


def test_finds_a_peak_in_the_middle() -> None:
    """Finds the largest value when both slopes are present."""
    assert find_peak([1, 3, 7, 4, 2]) == 7
    assert find_peak([0, 10, 9, 8, 7, 6, 5]) == 10
    assert find_peak([5, 6, 7, 8, 9, 10, 0]) == 10


def test_a_list_that_only_rises_peaks_at_the_end() -> None:
    """Returns the last value of a strictly increasing list."""
    assert find_peak([1, 2, 3, 4]) == 4
    assert find_peak([1, 2]) == 2


def test_a_list_that_only_falls_peaks_at_the_start() -> None:
    """Returns the first value of a strictly decreasing list."""
    assert find_peak([9, 5, 1]) == 9
    assert find_peak([2, 1]) == 2


def test_a_single_value_is_the_peak() -> None:
    """Returns the only value of a one-value list."""
    assert find_peak([42]) == 42


def test_handles_negative_values() -> None:
    """Finds a peak that is below zero."""
    assert find_peak([-9, -4, -1, -6]) == -1
    assert find_peak([-3, -2, -1]) == -1


def test_the_same_value_may_be_on_both_slopes() -> None:
    """Handles a symmetric mountain, where both slopes hold the same values."""
    assert find_peak([1, 2, 3, 2, 1]) == 3
    assert find_peak([4, 8, 4]) == 8


def test_finds_every_peak_of_every_short_mountain() -> None:
    """Matches the built-in maximum for every mountain of up to eight values.

    The values 0..n-1 with the largest as the peak and every way of dealing
    the others between the two slopes.
    """
    for size in range(1, 9):
        lower = range(size - 1)
        for count in range(size):
            for left in combinations(lower, count):
                right = sorted(set(lower) - set(left), reverse=True)
                numbers = [*left, size - 1, *right]
                assert find_peak(numbers) == max(numbers), numbers


def test_finds_a_peak_at_every_position() -> None:
    """Finds the peak wherever it sits in a list of two hundred values."""
    for peak in range(200):
        assert find_peak(mountain(200, peak)) == 0, peak


def test_leaves_the_list_alone() -> None:
    """Does not sort or modify the list it was given."""
    numbers = [1, 5, 4, 3]

    find_peak(numbers)

    assert numbers == [1, 5, 4, 3]


def test_reads_only_a_handful_of_values() -> None:
    """Reads at most a hundred of two million values, wherever the peak is.

    Halving two million takes twenty-one rounds, and each round reads two
    values. A scan for the maximum reads all of them.
    """
    size = 2_000_000
    for peak in (0, 1, 777_777, size // 2, size - 2, size - 1):
        numbers = Watched(range(peak, 0, -1))
        numbers.reverse()
        numbers.extend(range(peak, peak - (size - peak), -1))
        numbers.reads = 0

        assert len(numbers) == size
        assert find_peak(numbers) == peak, peak
        assert numbers.reads <= 100, f"read {numbers.reads} values"
