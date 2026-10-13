"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import merge_lists

type Intervals = list[tuple[int, int]]


def by_marking_points(first: Intervals, second: Intervals) -> Intervals:
    """Mark every covered point on a doubled number line and read off the runs.

    Doubling leaves a gap between (1, 2) and (3, 4) and none between (1, 2)
    and (2, 3), which is exactly the closed-interval rule.
    """
    covered = set()
    for start, end in first + second:
        covered.update(range(2 * start, 2 * end + 1))
    runs: Intervals = []
    for point in sorted(covered):
        if runs and runs[-1][1] == point - 1:
            runs[-1] = (runs[-1][0], point)
        else:
            runs.append((point, point))
    return [(start // 2, end // 2) for start, end in runs]


def valid_lists(top: int) -> list[Intervals]:
    """Every sorted list of non-touching intervals with ends in 0..top."""
    found: list[Intervals] = [[]]
    points = range(top + 1)
    for count in (1, 2, 3):
        for ends in combinations(points, 2 * count):
            found.append([(ends[k], ends[k + 1]) for k in range(0, 2 * count, 2)])
    found.extend([(point, point)] for point in points)
    found.append([(0, 0), (top, top)])
    return found


def test_merges_intervals_that_overlap_across_the_lists() -> None:
    """Joins an interval from one list with one it overlaps in the other."""
    assert merge_lists([(1, 3), (8, 10)], [(2, 5), (12, 14)]) == [
        (1, 5),
        (8, 10),
        (12, 14),
    ]


def test_interleaves_intervals_that_do_not_overlap() -> None:
    """Puts intervals from both lists in order when none of them meet."""
    assert merge_lists([(1, 2), (9, 10)], [(4, 5), (13, 14)]) == [
        (1, 2),
        (4, 5),
        (9, 10),
        (13, 14),
    ]


def test_touching_intervals_merge() -> None:
    """Merges two intervals that share only an endpoint."""
    assert merge_lists([(1, 3)], [(3, 5)]) == [(1, 5)]
    assert merge_lists([(3, 5)], [(1, 3)]) == [(1, 5)]


def test_one_interval_swallows_several() -> None:
    """Absorbs several intervals of one list into one of the other."""
    assert merge_lists([(1, 2), (5, 6), (9, 10)], [(0, 20)]) == [(0, 20)]
    assert merge_lists([(0, 20)], [(1, 2), (5, 6), (9, 10)]) == [(0, 20)]
    assert merge_lists([(1, 2), (5, 6), (9, 10)], [(4, 9)]) == [(1, 2), (4, 10)]


def test_an_interval_inside_another_does_not_shorten_it() -> None:
    """Keeps the longer end when a later interval finishes earlier."""
    assert merge_lists([(1, 10)], [(2, 3)]) == [(1, 10)]
    assert merge_lists([(1, 10)], [(2, 3), (11, 12)]) == [(1, 10), (11, 12)]


def test_a_chain_alternating_between_the_lists_joins_up() -> None:
    """Merges a run of intervals that each touch the next one in the other list."""
    assert merge_lists([(1, 3), (5, 7)], [(3, 5), (7, 9)]) == [(1, 9)]
    assert merge_lists([(0, 2), (4, 6), (8, 10)], [(1, 5), (7, 9)]) == [(0, 6), (7, 10)]


def test_handles_empty_lists() -> None:
    """Returns the other list when one is empty, and nothing when both are."""
    assert merge_lists([], []) == []
    assert merge_lists([(1, 2), (4, 5)], []) == [(1, 2), (4, 5)]
    assert merge_lists([], [(4, 4)]) == [(4, 4)]


def test_identical_lists_merge_to_themselves() -> None:
    """Returns one copy when both lists are the same."""
    assert merge_lists([(1, 2), (4, 5)], [(1, 2), (4, 5)]) == [(1, 2), (4, 5)]


def test_handles_single_points_and_negatives() -> None:
    """Handles zero-length intervals and coordinates below zero."""
    assert merge_lists([(-5, -5), (0, 0)], [(-5, 0)]) == [(-5, 0)]
    assert merge_lists([(-3, -1)], [(-9, -7), (2, 2)]) == [(-9, -7), (-3, -1), (2, 2)]


def test_agrees_with_marking_every_point() -> None:
    """Matches a point-marking union for every pair of small lists.

    Every pair of valid lists of up to three intervals with ends in 0..5.
    """
    lists = valid_lists(5)
    for first in lists:
        for second in lists:
            expected = by_marking_points(first, second)
            assert merge_lists(first, second) == expected, (first, second)


def test_returns_a_new_list_and_leaves_the_inputs_alone() -> None:
    """Does not modify or return either of the lists it was given."""
    first, second = [(1, 2), (6, 7)], [(3, 4)]

    result = merge_lists(first, second)

    assert result is not first
    assert result is not second
    assert first == [(1, 2), (6, 7)]
    assert second == [(3, 4)]
    assert merge_lists(first, []) is not first


def test_merges_two_long_lists() -> None:
    """Merges two lists of a hundred thousand intervals within the time limit.

    The first list covers [4k, 4k + 1] and the second [4k + 2, 4k + 3], so
    nothing touches and the result has two hundred thousand intervals.
    Shifting the second list down by one makes every pair touch its
    neighbours, and the result is a single interval. Inserting one interval
    at a time into a growing list is ten thousand million steps.
    """
    count = 100_000
    first = [(4 * k, 4 * k + 1) for k in range(count)]
    apart = [(4 * k + 2, 4 * k + 3) for k in range(count)]
    touching = [(4 * k + 1, 4 * k + 4) for k in range(count)]

    assert len(merge_lists(first, apart)) == 2 * count
    assert merge_lists(first, touching) == [(0, 4 * count)]
