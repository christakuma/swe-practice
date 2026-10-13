"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import merge_intervals


def by_groups(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Group the intervals by who overlaps whom, with no sorting involved.

    Every interval starts in a group of its own, and two groups are joined
    whenever any member of one shares time with any member of the other. Each
    group is then reported as its earliest start and its latest end.
    """
    groups = [[interval] for interval in intervals]
    joined = True
    while joined:
        joined = False
        for first in range(len(groups)):
            for second in range(first + 1, len(groups)):
                if any(
                    a[0] < b[1] and b[0] < a[1]
                    for a in groups[first]
                    for b in groups[second]
                ):
                    groups[first] += groups.pop(second)
                    joined = True
                    break
            if joined:
                break
    return sorted(
        (min(start for start, _ in group), max(end for _, end in group))
        for group in groups
    )


def test_does_not_merge_intervals_that_only_touch() -> None:
    """Keeps two intervals separate when one ends as the other begins."""
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 3), (3, 5)]


def test_merges_intervals_that_overlap_by_one_unit() -> None:
    """Merges two intervals that share a single unit of time."""
    assert merge_intervals([(1, 4), (3, 5)]) == [(1, 5)]


def test_sorts_the_result() -> None:
    """Returns the result sorted by start, whatever order it arrived in."""
    assert merge_intervals([(6, 7), (1, 3), (2, 6)]) == [(1, 6), (6, 7)]


def test_merges_through_a_containing_interval() -> None:
    """Merges intervals that only touch each other but lie inside a third."""
    assert merge_intervals([(1, 10), (3, 4), (4, 5)]) == [(1, 10)]


def test_keeps_the_wider_end() -> None:
    """Keeps the later end when one interval lies inside another."""
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_merges_a_chain_of_overlaps() -> None:
    """Merges a run in which each interval overlaps only the next."""
    assert merge_intervals([(1, 3), (2, 5), (4, 8)]) == [(1, 8)]


def test_keeps_a_chain_of_touches_apart() -> None:
    """Keeps a run of back-to-back intervals as separate intervals."""
    assert merge_intervals([(1, 2), (2, 3), (3, 4)]) == [(1, 2), (2, 3), (3, 4)]


def test_collapses_identical_intervals() -> None:
    """Merges an interval with a copy of itself."""
    assert merge_intervals([(1, 2), (1, 2)]) == [(1, 2)]


def test_handles_nothing_and_one_interval() -> None:
    """Returns nothing for nothing and one interval unchanged."""
    assert merge_intervals([]) == []
    assert merge_intervals([(4, 9)]) == [(4, 9)]


def test_agrees_with_grouping_for_every_small_list() -> None:
    """Matches an overlap-grouping for every list of up to three intervals.

    Every interval with endpoints in 0..4, taken up to three at a time in
    every order.
    """
    choices = [(start, end) for start in range(5) for end in range(start + 1, 5)]
    for size in range(4):
        for chosen in product(choices, repeat=size):
            intervals = list(chosen)
            assert merge_intervals(intervals) == by_groups(intervals), intervals


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    intervals = [(5, 6), (1, 2)]

    merge_intervals(intervals)

    assert intervals == [(5, 6), (1, 2)]


def test_merges_a_hundred_thousand_intervals() -> None:
    """Handles a hundred thousand intervals within the time limit.

    Back-to-back intervals, handed over in reverse: nothing overlaps, so all
    hundred thousand come back. Then every one is stretched by a unit, and
    they collapse into a single interval.
    """
    count = 100_000
    apart = [(2 * index, 2 * index + 2) for index in reversed(range(count))]

    assert merge_intervals(apart) == sorted(apart)

    overlapping = [(start, end + 1) for start, end in apart]

    assert merge_intervals(overlapping) == [(0, 2 * count + 1)]
