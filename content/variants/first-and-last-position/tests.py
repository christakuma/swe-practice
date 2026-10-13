"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator
from itertools import combinations_with_replacement

from solution import search


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


def by_scanning(numbers: list[int], target: int) -> tuple[int, int]:
    positions = [index for index, value in enumerate(numbers) if value == target]
    return (positions[0], positions[-1]) if positions else (-1, -1)


def test_finds_a_run_in_the_middle() -> None:
    """Returns where a repeated value starts and ends."""
    assert search([5, 7, 7, 8, 8, 10], 8) == (3, 4)
    assert search([5, 7, 7, 8, 8, 10], 7) == (1, 2)


def test_a_single_occurrence_starts_and_ends_together() -> None:
    """Returns the same position twice for a value that appears once."""
    assert search([5, 7, 7, 8, 8, 10], 5) == (0, 0)
    assert search([5, 7, 7, 8, 8, 10], 10) == (5, 5)
    assert search([4], 4) == (0, 0)


def test_returns_minus_ones_when_the_target_is_absent() -> None:
    """Returns (-1, -1) for a value between, below or above the values present."""
    assert search([5, 7, 7, 8, 8, 10], 6) == (-1, -1)
    assert search([5, 7, 7, 8, 8, 10], 1) == (-1, -1)
    assert search([5, 7, 7, 8, 8, 10], 99) == (-1, -1)


def test_handles_an_empty_list() -> None:
    """Returns (-1, -1) for an empty list."""
    assert search([], 3) == (-1, -1)


def test_a_run_may_cover_the_whole_list() -> None:
    """Returns the two ends when every value is the target."""
    assert search([2, 2, 2, 2], 2) == (0, 3)
    assert search([2, 2], 2) == (0, 1)


def test_a_run_may_touch_either_end() -> None:
    """Finds runs that begin at the first position or finish at the last."""
    assert search([1, 1, 1, 2, 3], 1) == (0, 2)
    assert search([1, 2, 3, 3, 3], 3) == (2, 4)


def test_returns_a_tuple() -> None:
    """Returns a tuple of two integers."""
    result = search([1, 2, 2], 2)

    assert isinstance(result, tuple)
    assert result == (1, 2)


def test_handles_negative_values() -> None:
    """Finds a run of negative values and a negative target that is absent."""
    assert search([-5, -3, -3, -3, 0, 2], -3) == (1, 3)
    assert search([-5, -3, -3, -3, 0, 2], -4) == (-1, -1)


def test_agrees_with_scanning_every_short_sorted_list() -> None:
    """Matches a linear scan for every short sorted list and every target.

    Every ascending list of up to seven values drawn from 0..3, against
    every target from -1 to 4.
    """
    for size in range(8):
        for chosen in combinations_with_replacement(range(4), size):
            numbers = list(chosen)
            for target in range(-1, 5):
                assert search(numbers, target) == by_scanning(numbers, target), (
                    numbers,
                    target,
                )


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    numbers = [1, 2, 2, 3]

    search(numbers, 2)

    assert numbers == [1, 2, 2, 3]


def test_reads_only_a_handful_of_values_however_long_the_run() -> None:
    """Reads at most a hundred and fifty of two million values per search.

    The middle million values are all 7. Finding one of them and walking
    outwards to the ends of the run reads a million; two boundary searches
    read about forty.
    """
    size = 2_000_000
    numbers = Watched([3] * 500_000 + [7] * 1_000_000 + [9] * 500_000)
    cases = {
        7: (500_000, 1_499_999),
        3: (0, 499_999),
        9: (1_500_000, size - 1),
        5: (-1, -1),
        10: (-1, -1),
    }

    for target, expected in cases.items():
        numbers.reads = 0
        assert search(numbers, target) == expected, target
        assert numbers.reads <= 150, f"read {numbers.reads} values"
