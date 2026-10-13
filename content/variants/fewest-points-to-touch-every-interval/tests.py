"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import fewest_points


def by_trying(intervals: list[tuple[int, int]]) -> int:
    """Try every set of candidate points, smallest sets first."""
    candidates = sorted({end for _, end in intervals})
    for size in range(len(candidates) + 1):
        for chosen in combinations(candidates, size):
            if all(
                any(start <= point <= end for point in chosen)
                for start, end in intervals
            ):
                return size
    return len(candidates)


def test_shares_a_point_between_overlapping_intervals() -> None:
    """Uses one point for intervals that overlap."""
    assert fewest_points([(1, 6), (2, 8), (7, 12), (10, 16)]) == 2


def test_shares_a_point_between_intervals_that_touch() -> None:
    """Counts a point on a shared end as inside both intervals."""
    assert fewest_points([(1, 2), (2, 3)]) == 1
    assert fewest_points([(1, 2), (2, 3), (3, 4)]) == 2


def test_is_not_misled_by_a_long_interval() -> None:
    """Needs two points for two short intervals inside a long one."""
    assert fewest_points([(1, 10), (2, 3), (4, 5)]) == 2


def test_handles_trivial_lists() -> None:
    """Returns 0 for nothing, 1 for one interval and 1 for copies of it."""
    assert fewest_points([]) == 0
    assert fewest_points([(3, 3)]) == 1
    assert fewest_points([(1, 4), (1, 4), (1, 4)]) == 1


def test_agrees_with_trying_every_set_of_points() -> None:
    """Matches an exhaustive search for every list of up to three intervals."""
    choices = [(start, end) for start in range(5) for end in range(start, 5)]
    for size in range(4):
        for chosen in product(choices, repeat=size):
            intervals = list(chosen)
            assert fewest_points(intervals) == by_trying(intervals), intervals


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    intervals = [(5, 6), (1, 2)]

    fewest_points(intervals)

    assert intervals == [(5, 6), (1, 2)]


def test_handles_two_hundred_thousand_intervals() -> None:
    """Handles two hundred thousand intervals within the time limit."""
    count = 200_000
    chained = [(index, index + 1) for index in reversed(range(count))]

    assert fewest_points(chained) == count // 2
