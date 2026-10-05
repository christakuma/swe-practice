"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, pairwise

from solution import insert


def reference(
    intervals: list[tuple[int, int]],
    new: tuple[int, int],
) -> list[tuple[int, int]]:
    """Throw everything together, sort, and merge -- an independent oracle.

    It discards the "already sorted and disjoint" guarantee the real solution
    exploits, so it shares none of the three-group reasoning.
    """
    out: list[tuple[int, int]] = []
    for start, end in sorted([*intervals, new]):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def disjoint_lists(points: range, size: int) -> list[list[tuple[int, int]]]:
    """Sorted non-overlapping interval lists of `size`, drawn from `points`."""
    out = []
    for starts in combinations(points, size):
        intervals = [(start, start + 1) for start in starts]
        if all(a[1] < b[0] for a, b in pairwise(intervals)):
            out.append(intervals)
    return out


def test_merges_one_overlap() -> None:
    """Merges the new interval with the one it overlaps."""
    assert insert([(1, 3), (6, 9)], (2, 5)) == [(1, 5), (6, 9)]


def test_merges_several_overlaps() -> None:
    """Swallows every interval the new one spans.

    (4, 8) reaches across three intervals. A solution that emits the merged
    block as soon as it finds one overlap produces several pieces instead of
    one.
    """
    assert insert([(1, 2), (3, 5), (6, 7), (8, 10)], (4, 8)) == [(1, 2), (3, 10)]


def test_handles_an_empty_list() -> None:
    """Returns just the new interval when there is nothing to insert into."""
    assert insert([], (5, 7)) == [(5, 7)]


def test_handles_a_new_interval_inside_an_existing_one() -> None:
    """Leaves the list unchanged when the new interval is already covered."""
    assert insert([(1, 5)], (2, 3)) == [(1, 5)]
    assert insert([(1, 5)], (1, 5)) == [(1, 5)]


def test_handles_a_new_interval_covering_everything() -> None:
    """Replaces every interval when the new one spans them all."""
    assert insert([(2, 3), (5, 6), (8, 9)], (1, 10)) == [(1, 10)]


def test_inserts_before_everything() -> None:
    """Puts a new interval at the front when nothing overlaps it."""
    assert insert([(5, 7), (9, 11)], (1, 2)) == [(1, 2), (5, 7), (9, 11)]


def test_inserts_after_everything() -> None:
    """Puts a new interval at the end when nothing overlaps it."""
    assert insert([(1, 2), (5, 7)], (9, 11)) == [(1, 2), (5, 7), (9, 11)]


def test_inserts_into_a_gap() -> None:
    """Puts a new interval between two others without merging either."""
    assert insert([(1, 2), (8, 9)], (4, 5)) == [(1, 2), (4, 5), (8, 9)]


def test_merges_intervals_that_merely_touch() -> None:
    """Treats touching intervals as overlapping, on both sides.

    (1, 3) and (3, 5) share a point and merge. The comparison that decides this
    appears twice -- once for "entirely before" and once for "still
    overlapping" -- so a solution using <= in one place and < in the other
    merges on the left and not on the right.
    """
    assert insert([(1, 3)], (3, 5)) == [(1, 5)]
    assert insert([(3, 5)], (1, 3)) == [(1, 5)]
    assert insert([(1, 3), (5, 7)], (3, 5)) == [(1, 7)]


def test_handles_a_zero_width_interval() -> None:
    """Handles an interval whose start equals its end."""
    assert insert([(1, 3)], (2, 2)) == [(1, 3)]
    assert insert([(1, 3)], (5, 5)) == [(1, 3), (5, 5)]
    assert insert([], (4, 4)) == [(4, 4)]


def test_returns_tuples_in_order() -> None:
    """Returns ascending, non-overlapping tuples."""
    result = insert([(1, 2), (5, 7)], (3, 4))

    assert result == sorted(result)
    for earlier, later in pairwise(result):
        assert earlier[1] < later[0]


def test_does_not_mutate_the_input() -> None:
    """Leaves the caller's list alone."""
    intervals = [(1, 3), (6, 9)]
    before = list(intervals)

    insert(intervals, (2, 5))

    assert intervals == before


def test_agrees_with_a_sort_and_merge_across_many_inputs() -> None:
    """Matches the oracle for every small disjoint list and every new interval.

    Around twelve hundred cases: disjoint lists of up to three unit intervals
    over seven positions, crossed with every new interval. The touching rule
    and the emit-once rule each fail only at specific alignments.
    """
    points = range(7)
    for size in range(4):
        for intervals in disjoint_lists(points, size):
            for start in points:
                for end in range(start, 8):
                    assert insert(list(intervals), (start, end)) == reference(
                        list(intervals), (start, end)
                    ), (intervals, (start, end))


def test_handles_a_long_list() -> None:
    """Inserts into a hundred thousand intervals within the time limit.

    The new interval spans the middle half, so most of the list is absorbed --
    which is also where sorting the input would show up as wasted work.

    Compared against the oracle rather than a hand-counted length: working out
    how many unit intervals fall strictly before 250,000 is exactly the kind of
    off-by-one the tests are supposed to catch rather than contain.
    """
    intervals = [(value * 10, value * 10 + 1) for value in range(100_000)]

    result = insert(intervals, (250_000, 750_000))

    assert result == reference(intervals, (250_000, 750_000))
    assert (250_000, 750_001) in result
    for earlier, later in pairwise(result):
        assert earlier[1] < later[0]
